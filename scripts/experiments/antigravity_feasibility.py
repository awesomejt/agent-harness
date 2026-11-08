#!/usr/bin/env python3
"""Opt-in, macOS-only Antigravity 1.5.3 startup/initialize observations.

No authenticate/session/prompt RPC or operator login. Exit 0 reproduces these
observations, not production isolation or permission enforcement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

LIMIT = 2 * 1024 * 1024
TIMEOUT = 10
FAILURE = 'Antigravity feasibility probe failed; raw diagnostics withheld'


def check(value):
    if not value:
        raise RuntimeError('observation changed; reassess control gate')


def request(method):
    check(method == 'initialize')
    return (json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {
        'protocolVersion': 1, 'clientCapabilities': {},
        'clientInfo': {'name': 'agent-harness-feasibility', 'version': '0.1.0'}}})
            + '\n').encode()


def signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        # macOS can report EPERM for a just-disappeared orphan group. Ignore it
        # only after ps confirms there are no members; live groups still fail.
        result = subprocess.run(['/bin/ps', '-g', str(pid), '-o', 'stat='],
                                capture_output=True, timeout=2)
        check(result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip())


def capture(command, cwd, env, data=None):
    """Bound both pipes while reading; always reap the entire child group."""
    if data is not None:
        check(data == request('initialize'))
    child = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True,
                             stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    output = {'out': bytearray(), 'err': bytearray()}
    deadline = time.monotonic() + TIMEOUT
    count = 0
    try:
        selector.register(child.stdout, selectors.EVENT_READ, 'out')
        selector.register(child.stderr, selectors.EVENT_READ, 'err')
        if data is not None:
            child.stdin.write(data)
            child.stdin.close()
        while selector.get_map():
            remaining = deadline - time.monotonic()
            check(remaining > 0)
            for key, _ in selector.select(min(.1, remaining)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                count += len(chunk)
                check(count <= LIMIT)
                output[key.data].extend(chunk)
        check(child.wait(timeout=max(.01, deadline - time.monotonic())) == 0)
        return bytes(output['out']), bytes(output['err'])
    finally:
        try:
            try:
                if child.stdin is not None and not child.stdin.closed:
                    child.stdin.close()
                signal_group(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    pass
            finally:
                signal_group(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
        finally:
            selector.close()
            child.stdout.close()
            child.stderr.close()


def validate(stdout):
    messages = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    check(len(messages) == 1)
    message = messages[0]
    check(isinstance(message, dict) and message.get('jsonrpc') == '2.0'
          and type(message.get('id')) is int and message['id'] == 1
          and 'method' not in message and 'error' not in message)
    result = message.get('result')
    check(isinstance(result, dict) and type(result.get('protocolVersion')) is int
          and result['protocolVersion'] == 1)
    check(result.get('agentInfo') == {'name': 'Antigravity ACP Server', 'version': '1.5.3'})
    check(isinstance(result.get('agentCapabilities'), dict))
    auth = result.get('authMethods')
    check(isinstance(auth, list) and all(isinstance(m, dict)
          and isinstance(m.get('id'), str) for m in auth))
    check({m['id'] for m in auth} == {
        'oauth-personal', 'oauth-business', 'gemini-api-key', 'agent-platform'})
    # The response is not an effective tool/config/model inventory.
    check('tools' not in result and 'models' not in result)
    return result


def profile(root, operator_home):
    return ('(version 1)(allow default)(deny network*)'
            '(deny file-write* (require-not (subpath ' + json.dumps(str(root)) + ')))'
            '(deny file-read-data (subpath ' + json.dumps(str(operator_home)) + '))')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agy', default='agy', help='installed official CLI; never downloaded')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    installed = shutil.which(args.agy)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-antigravity-feasibility-') as directory:
        root = Path(directory).resolve()
        # Copy only the executable so the sandbox can deny ALL operator-home data
        # reads, including the original executable location. No auth/config copy.
        executable = root / 'agy'
        shutil.copy2(installed, executable)
        print('binary sha256=' + hashlib.sha256(executable.read_bytes()).hexdigest(), flush=True)
        home, project, gemini = root / 'home', root / 'repo' / 'project', root / 'gemini'
        for path in (home, project, gemini, root / 'repo' / '.git'):
            path.mkdir(parents=True, exist_ok=True)
        env = {'HOME': str(home), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
               'NO_COLOR': '1', 'TERM': 'dumb', 'LANG': 'C'}
        sandbox = ['/usr/bin/sandbox-exec', '-p', profile(root, Path.home())]
        # Check the containment with harmless operations before starting ACP.
        # Reading the installed executable tests the protected home path without
        # selecting any operator configuration or credential file.
        with tempfile.TemporaryDirectory(prefix='ah-agy-fence-') as fence:
            checks = ('import pathlib,socket; '
                      + 'ops=[lambda: socket.socket().bind(("127.0.0.1",0)), '
                      + 'lambda: pathlib.Path(' + repr(str(Path(installed).resolve())) + ').read_bytes(), '
                      + 'lambda: pathlib.Path(' + repr(str(Path(fence) / 'write')) + ').write_text("x")]; '
                      + '\nfor op in ops:\n try: op()\n except PermissionError: pass'
                      + '\n else: raise RuntimeError("containment failed")\n')
            capture([*sandbox, sys.executable, '-c', checks], project, env)
        print('PASS: network bind, operator-home binary read and outside write denied', flush=True)
        def run(args, data=None):
            return capture([*sandbox, str(executable), *args], project, env, data)
        out, err = run(['--version'])
        check((out + err).decode().strip() == '1.5.3')
        _, help_text = run(['acp', '--help'])
        check(b'--include-default-customizations' in help_text and b'--gemini-dir' in help_text)
        check(b'--settings' not in help_text)
        # Inert instruction/settings/role sentinels only. Never seed executable
        # hooks, plugins or MCP into startup before their discovery is controlled.
        sentinels = {
            home / '.gemini' / 'AGENTS.md': 'AH_USER_INSTRUCTIONS\n',
            root / 'repo' / 'AGENTS.md': 'AH_PARENT_INSTRUCTIONS\n',
            project / 'AGENTS.md': 'AH_PROJECT_INSTRUCTIONS\n',
            gemini / 'antigravity-cli' / 'settings.json': '{"toolPermission":"strict"}\n',
            project / '.agents' / 'agents' / 'ah-sentinel.md':
                '---\nname: ah-sentinel\ndescription: inert discovery sentinel\n---\nAH_ROLE\n',
        }
        for path, content in sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        flags = ['acp', '--app-data-dir', 'ah-app', '--gemini-dir', str(gemini),
                 '--disable-telemetry', '--include-default-customizations=false']
        for label, prefix in [('baseline', []), ('top-level-settings', ['--settings', '{}'])]:
            out, err = run([*prefix, *flags])
            check(not out and not err)
            print('PASS: ' + label + ' startup EOF; no RPC sent', flush=True)
        out, err = run(flags, request('initialize'))
        validate(out)
        check(not err)
        check(all(path.read_text() == content for path, content in sentinels.items()))
        created = [path for path in root.rglob('*') if path.is_file()
                   and path != executable and path not in sentinels]
        logdir = gemini / 'ah-app' / 'log'
        check(created and all(path.parent == logdir and path.name.startswith('acp-server-')
                              and path.suffix == '.log' for path in created))
        print('PASS: initialize protocol=1 version=1.5.3 auth-method IDs only; '
              'no effective tool/model inventory', flush=True)
        print('PASS: inert sentinels unchanged; only synthetic ACP logs created', flush=True)
        print('GATE UNPASSED: source isolation, login preservation, complete deny and '
              'exact grants require separate proof; no session/model RPC', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(FAILURE, file=sys.stderr)
        sys.exit(1)
