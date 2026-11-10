#!/usr/bin/env python3
"""Opt-in pinned macOS no-auth OpenCode diagnostics on one owned TCP port."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading

from antigravity_feasibility import capture, check, profile, signal_group, LIMIT, TIMEOUT
from chatgpt_feasibility import SHA256

PYTHON = '/Library/Developer/CommandLineTools/usr/bin/python3'
COMMANDS = {('debug', 'config'), ('debug', 'agents'), ('debug', 'paths')}


def contained_profile(root, operator_home, port=None):
    value = profile(root, operator_home) + '(allow file-write-data (literal "/dev/null"))'
    if port is not None:
        check(type(port) is int and 1 <= port <= 65535)
        value += (f'(allow network-bind network-inbound (local tcp "localhost:{port}"))'
                  f'(allow network-outbound (remote tcp "localhost:{port}"))')
    return value


def diagnostic(executable, project, env, policy, command, url=None, status=0):
    check(command in COMMANDS)
    check((command == ('debug', 'paths')) == (url is None))
    check(type(status) is int and status in (0, 1))
    args = [] if url is None else ['--server', url]
    wrapper = '"$@"; status=$?; printf "\\nAH_EXIT=%s\\n" "$status"'
    out, err = capture(['/usr/bin/sandbox-exec', '-p', policy, '/bin/sh', '-c', wrapper,
                        'ah-diagnostic', str(executable), *command, *args], project, env)
    marker = ('\nAH_EXIT=' + str(status) + '\n').encode()
    check(out.endswith(marker))
    return out[:-len(marker)], err


def validate_agents(agents, model, rules, canary):
    check(isinstance(agents, list) and bool(agents))
    check(any(a.get('id') == 'ah-source-sentinel' for a in agents) == canary)
    for agent in agents:
        check(agent.get('model') in (None, {'id': model['model'], 'providerID': model['providerID']}))
        check(agent['request'] == {'settings': {}, 'headers': {}, 'body': {}})
        effective = agent['permissions']
        matches = [i for i in range(len(effective)) if effective[i:i + len(rules)] == rules]
        check(matches and all(r['effect'] == 'deny' for r in effective[matches[-1] + len(rules):]))


SPAWN = r"""
import {spawnSync} from 'node:child_process';
const results=[];
for (const detached of [false,true]) for (const stdio of ['ignore','inherit','pipe']) {
 const r=spawnSync('/usr/bin/true',[],{detached,stdio});
 results.push({detached,stdio,status:r.status,error:r.error?.code ?? null});
}
console.log(JSON.stringify({bun:Bun.version,results}));
"""


def spawn_controls(root, executable, env):
    fixture = root / 'synthetic-spawn.js'
    fixture.write_text(SPAWN)
    synthetic = dict(env, BUN_BE_BUN='1')
    for corrected in (False, True):
        policy = contained_profile(root, Path.home()) if corrected else profile(root, Path.home())
        direct = """import os,json
results=[]
for flags in (os.O_RDONLY,os.O_WRONLY,os.O_RDWR):
 try:
  fd=os.open('/dev/null',flags);os.close(fd);results.append('open')
 except PermissionError: results.append('denied')
print(json.dumps(results))
"""
        out, err = capture(['/usr/bin/sandbox-exec', '-p', policy, PYTHON, '-B', '-c', direct], root, env)
        check(not err and json.loads(out) == (['open'] * 3 if corrected else ['open', 'denied', 'denied']))
        out, _ = capture(['/usr/bin/sandbox-exec', '-p', policy, str(executable), str(fixture)], root, synthetic)
        result = json.loads(out)
        check(result['bun'] == '1.4.4' and len(result['results']) == 6)
        for item in result['results']:
            denied = not corrected and item['stdio'] == 'ignore'
            check((item['status'], item['error']) == ((None, 'EPERM') if denied else (0, None)))
    print('PASS: ignored-stdio spawn failure and literal /dev/null correction', flush=True)


def network_controls(root, policy, env, port, home_read, outside_write):
    code = r"""
import os,socket,threading
from pathlib import Path
port=PORT
s=socket.socket();s.bind(('127.0.0.1',port));s.listen(1)
def echo():
 c,_=s.accept();c.sendall(b'AH_ECHO');c.close()
t=threading.Thread(target=echo,daemon=True);t.start()
c=socket.socket();c.settimeout(1);c.connect(('127.0.0.1',port))
assert c.recv(20)==b'AH_ECHO';c.close();t.join(1);assert not t.is_alive();s.close()
for family,kind,op,target in [
 (socket.AF_INET,socket.SOCK_STREAM,'bind',('127.0.0.1',0)),
 (socket.AF_INET,socket.SOCK_STREAM,'bind',('0.0.0.0',OTHER_PORT)),
 (socket.AF_INET,socket.SOCK_STREAM,'connect',('127.0.0.1',OTHER_PORT)),
 (socket.AF_INET,socket.SOCK_STREAM,'connect',('192.0.2.1',443)),
 (socket.AF_INET,socket.SOCK_DGRAM,'sendto',('127.0.0.1',port)),
 (socket.AF_INET6,socket.SOCK_STREAM,'bind',('::1',OTHER_PORT)),
 (socket.AF_UNIX,socket.SOCK_STREAM,'bind',UNIX_PATH)]:
 q=socket.socket(family,kind);q.settimeout(.3)
 try:
  if op=='sendto': q.sendto(b'AH_CANARY',target)
  else: getattr(q,op)(target)
 except PermissionError: pass
 else: raise RuntimeError('network boundary widened')
 finally: q.close()
for op in [lambda:Path(HOME_READ).read_bytes(),lambda:Path(OUTSIDE_WRITE).write_text('x')]:
 try: op()
 except PermissionError: pass
 else: raise RuntimeError('filesystem boundary widened')
fd=os.open('/dev/null',os.O_RDWR);os.write(fd,b'AH_NULL');os.close(fd)
print('AH_BOUNDARIES_PASS')
"""
    replacements = {'OTHER_PORT': str(port + 1 if port < 65535 else port - 1),
                    'PORT': str(port), 'UNIX_PATH': repr(str(root / 'denied.sock')),
                    'HOME_READ': repr(str(home_read)), 'OUTSIDE_WRITE': repr(str(outside_write))}
    for name, value in replacements.items():
        code = code.replace(name, value)
    # Re-run the complete positive/negative matrix in an inherited sandboxed
    # child, rather than only in the directly sandbox-exec'd process.
    child = ('import subprocess; subprocess.run([' + repr(PYTHON)
             + ",'-B','-c'," + repr(code) + '],check=True)')
    out, err = capture(['/usr/bin/sandbox-exec', '-p', policy, PYTHON, '-B', '-c', child], root, env)
    check(out.strip() == b'AH_BOUNDARIES_PASS' and not err)
    print('PASS: owned TCP echo; other TCP/binds, external TCP, UDP, Unix and filesystem denials', flush=True)


@contextmanager
def owned_server(executable, project, env, policy, port):
    """Bound both server pipes for its entire lifetime, including client checks."""
    child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', policy, str(executable),
                              'serve', '--stdio', '--hostname', '127.0.0.1', '--port', str(port)],
                             cwd=project, env=env, start_new_session=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ready = queue.Queue()
    lock = threading.Lock()
    observed = {'bytes': 0, 'overflow': False}

    def drain(pipe, stdout):
        pending = bytearray()
        announced = False
        try:
            while True:
                chunk = os.read(pipe.fileno(), 65536)
                if not chunk:
                    break
                with lock:
                    observed['bytes'] += len(chunk)
                    if observed['bytes'] > LIMIT:
                        observed['overflow'] = True
                if observed['overflow']:
                    signal_group(child.pid, signal.SIGKILL)
                    break
                if stdout and not announced:
                    pending.extend(chunk)
                    if b'\n' in pending:
                        ready.put(bytes(pending).split(b'\n', 1)[0])
                        announced = True
                        pending.clear()
        finally:
            if stdout and not announced:
                ready.put(None)

    threads = [threading.Thread(target=drain, args=(pipe, isout), daemon=True)
               for pipe, isout in ((child.stdout, True), (child.stderr, False))]
    for thread in threads:
        thread.start()
    try:
        line = ready.get(timeout=TIMEOUT)
        check(line is not None and json.loads(line) == {'url': f'http://127.0.0.1:{port}'})
        check(child.poll() is None and not observed['overflow'])
        yield f'http://127.0.0.1:{port}'
        check(child.poll() is None and not observed['overflow'])
    finally:
        child.stdin.close()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            signal_group(child.pid, signal.SIGTERM)
        finally:
            signal_group(child.pid, signal.SIGKILL)
            child.wait(timeout=2)
        for thread in threads:
            thread.join(timeout=2)
            check(not thread.is_alive())
        child.stdout.close()
        child.stderr.close()
        check(not observed['overflow'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path(PYTHON).is_file())
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-chatgpt-contained-') as directory:
        root = Path(directory).resolve()
        executable = root / 'opencode-cli'
        shutil.copy2(installed, executable)
        check(hashlib.sha256(executable.read_bytes()).hexdigest() == SHA256)
        home, project = root / 'home', root / 'repo' / 'project'
        for path in (home, project, root / 'repo' / '.git'):
            path.mkdir(parents=True, exist_ok=True)
        env = {'HOME': str(home), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
               'NO_COLOR': '1', 'TERM': 'dumb', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
               'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_DISABLE_PROJECT_CONFIG': 'true',
               'OPENCODE_PASSWORD': secrets.token_urlsafe(32)}
        for kind in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
            env['XDG_' + kind + '_HOME'] = str(root / kind)
        model = {'providerID': 'openai', 'model': 'gpt-6.1-sol'}
        rules = [{'action': '*', 'resource': '*', 'effect': 'deny'},
                 {'action': 'external_directory', 'resource': '*', 'effect': 'deny'}]
        config = {'model': model, 'update': 'disable', 'share': 'disabled',
                  'permissions': rules, 'policies': [
                      {'action': 'provider.use', 'resource': '*', 'effect': 'deny'},
                      {'action': 'provider.use', 'resource': 'openai', 'effect': 'allow'}],
                  'agents': {'title': {'model': model}}, 'instructions': [],
                  'mcp': {}, 'plugins': [], 'providers': {}}
        env['OPENCODE_CONFIG_CONTENT'] = json.dumps(config)
        sentinel = project / 'opencode.json'
        sentinel.write_text(json.dumps({'agents': {'ah-source-sentinel': {
            'description': 'inert source sentinel', 'system': 'AH_PROJECT_SOURCE'}}}))
        parent_sentinel = project.parent / 'opencode.json'
        parent_sentinel.write_text(json.dumps({'agents': {'ah-parent-sentinel': {
            'description': 'inert parent sentinel', 'system': 'AH_PARENT_SOURCE'}}}))
        spawn_controls(root, executable, env)
        reservation = socket.socket()
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
        policy = contained_profile(root, Path.home(), port)
        reservation.close()
        with tempfile.TemporaryDirectory(prefix='.ah-contained-read-', dir=Path.home()) as protected:
            target = Path(protected) / 'sentinel'
            target.write_text('AH_READ_DENIAL_SENTINEL')
            with tempfile.TemporaryDirectory(prefix='ah-contained-write-') as fence:
                network_controls(root, policy, env, port, target, Path(fence) / 'write')
        # Do not reuse the echo control's TCP port while it may be in TIME_WAIT.
        reservation = socket.socket()
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
        policy = contained_profile(root, Path.home(), port)
        reservation.listen(1)
        entered = False
        refused = False
        try:
            try:
                with owned_server(executable, project, env, policy, port):
                    entered = True
            except RuntimeError:
                refused = True
            check(refused and not entered)
            reservation.setblocking(False)
            try:
                connection, _ = reservation.accept()
            except BlockingIOError:
                pass
            else:
                connection.close()
                check(False)
        finally:
            reservation.close()
        print('PASS: occupied port refuses before readiness; no connection to the conflicting listener', flush=True)
        for inherited in (False, True):
            if inherited:
                del env['OPENCODE_DISABLE_PROJECT_CONFIG']
            with owned_server(executable, project, env, policy, port) as url:
                for password, message in ((None, b'requires a password'),
                                          ('AH_WRONG_SYNTHETIC_PASSWORD', b'rejected the password')):
                    unauthorized = dict(env)
                    if password is None:
                        del unauthorized['OPENCODE_PASSWORD']
                    else:
                        unauthorized['OPENCODE_PASSWORD'] = password
                    out, err = diagnostic(executable, project, unauthorized, policy, ('debug', 'config'), url, status=1)
                    check(not out.strip() and message in err)
                print('PASS: absent and wrong private-server passwords refused', flush=True)
                raw, _ = diagnostic(executable, project, env, policy, ('debug', 'config'), url)
                sources = json.loads(raw)
                if not inherited:
                    check(sources == [
                        {'type': 'directory', 'path': str(root / 'CONFIG' / 'opencode')},
                        {'type': 'document', 'info': config}])
                else:
                    for path in (sentinel, parent_sentinel):
                        check(any(s.get('type') == 'document' and s.get('path') == str(path) for s in sources))
                raw, _ = diagnostic(executable, project, env, policy, ('debug', 'agents'), url)
                agents = json.loads(raw)
                validate_agents(agents, model, rules, inherited)
                check(any(a['id'] == 'ah-parent-sentinel' for a in agents) == inherited)
            print('PASS: ' + ('project/parent discovery positive control' if inherited else
                             'exact private sources, provider policy, helper models and agent deny rules'), flush=True)
        for data in ('DATA', 'alternate-data'):
            env['XDG_DATA_HOME'] = str(root / data)
            raw, _ = diagnostic(executable, project, env, policy, ('debug', 'paths'))
            paths = dict(line.split(None, 1) for line in raw.decode().splitlines() if line.strip())
            check(paths['data'] == str(root / data / 'opencode'))
            check(Path(paths['db']).parent == root / data / 'opencode')
            check(paths['config'] == str(root / 'CONFIG' / 'opencode'))
        print('PASS: synthetic data/database roots change independently of private config', flush=True)
        print('LIMIT: diagnostics only; login, effective auth/endpoint and full permission gates remain open')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Contained OpenCode diagnostic probe failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
