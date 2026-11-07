#!/usr/bin/env python3
"""Opt-in Grok 1.0.70 discovery with synthetic config and initialize-only ACP.

No operator login, authenticate/session/prompt RPC, model turn or grant is used.
Exit 0 reproduces observations; it does NOT pass the production feasibility gate.
"""
import argparse
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

PIN = 'grok 1.0.70 (f50904eaee6c)'
LIMIT = 2 * 1024 * 1024
TIMEOUT = 10
FILTERS = ['--tools=', '--deny', '*', '--no-subagents', '--disable-web-search']
FAILURE = 'Grok feasibility probe failed; raw protocol/diagnostics withheld'


def check(condition):
    if not condition:
        raise RuntimeError('observation changed; reassess the gate')


class Child:
    """Bound both output pipes and elapsed time; clean the whole process group."""
    def __init__(self, command, project, env, protocol=False):
        self.child = subprocess.Popen(
            command, cwd=project, env=env,
            stdin=subprocess.PIPE if protocol else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.child.stdout, selectors.EVENT_READ, 'out')
        self.selector.register(self.child.stderr, selectors.EVENT_READ, 'err')
        self.deadline = time.monotonic() + TIMEOUT
        self.output = {'out': bytearray(), 'err': bytearray()}
        self.count = 0

    def read(self):
        remaining = self.deadline - time.monotonic()
        check(remaining > 0)
        for key, _ in self.selector.select(min(.1, remaining)):
            data = os.read(key.fileobj.fileno(), 65536)
            if not data:
                self.selector.unregister(key.fileobj)
                continue
            self.count += len(data)
            check(self.count <= LIMIT)
            self.output[key.data].extend(data)

    def send(self, method):
        # The only allowed RPC cannot authenticate, create a session or infer.
        check(method == 'initialize')
        request = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': {
            'protocolVersion': 1, 'clientCapabilities': {},
            'clientInfo': {'name': 'agent-harness-feasibility', 'version': '0.1.0'}}}
        self.child.stdin.write((json.dumps(request) + '\n').encode())
        self.child.stdin.flush()

    def initialize(self):
        self.send('initialize')
        while self.selector.get_map():
            self.read()
            result = None
            while b'\n' in self.output['out']:
                line, _, rest = self.output['out'].partition(b'\n')
                self.output['out'] = bytearray(rest)
                message = json.loads(line)
                check(isinstance(message, dict) and message.get('jsonrpc') == '2.0')
                # Refuse server requests/unknown messages; never send approval replies.
                check('method' not in message and type(message.get('id')) is int
                      and message['id'] == 1 and 'error' not in message)
                check(result is None and isinstance(message.get('result'), dict))
                result = message['result']
            if result is not None:
                validate_init(result)
                return result
        raise RuntimeError('unexpected ACP EOF')

    def capture(self):
        while self.selector.get_map():
            self.read()
        code = self.child.wait(timeout=max(.01, self.deadline - time.monotonic()))
        check(code == 0)
        return bytes(self.output['out'])

    def close(self):
        if self.child.stdin is not None:
            self.child.stdin.close()
        try:
            os.killpg(self.child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.child.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            pass
        finally:
            # The leader may exit while a descendant still holds pipes open.
            try:
                os.killpg(self.child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.child.wait(timeout=2)
            self.selector.close()
            self.child.stdout.close()
            self.child.stderr.close()


def validate_init(result):
    check(type(result.get('protocolVersion')) is int and result['protocolVersion'] == 1)
    meta = result.get('_meta')
    check(isinstance(meta, dict) and meta.get('agentVersion') == '1.0.70')
    state = meta.get('modelState')
    check(isinstance(state, dict) and isinstance(state.get('currentModelId'), str))
    check(isinstance(result.get('agentCapabilities'), dict))
    check(isinstance(result.get('authMethods'), list))
    for method in result['authMethods']:
        check(isinstance(method, dict) and isinstance(method.get('id'), str))
    # No login was supplied. Do not interpret available auth methods as login.
    check(meta.get('defaultAuthMethodId') is None)


def capture(executable, args, project, env):
    child = Child([executable, *args], project, env)
    try:
        return child.capture()
    finally:
        child.close()


def inspect(executable, project, env, flags):
    result = json.loads(capture(executable, [*flags, 'inspect', '--json'], project, env))
    check(isinstance(result, dict) and result.get('grokVersion') == '1.0.70')
    check(isinstance(result.get('mcpServers'), list))
    for server in result['mcpServers']:
        check(isinstance(server, dict) and isinstance(server.get('name'), str))
    permissions = result.get('permissions')
    check(isinstance(permissions, dict) and type(permissions.get('loaded')) is int)
    check(permissions['loaded'] == 1)
    check({s['name'] for s in result['mcpServers']} == {'ah_user', 'ah_project'})
    return result


def initialize(executable, project, env, top_flags, agent_flags):
    child = Child([executable, '--no-auto-update', *top_flags,
                   'agent', '--no-leader', *agent_flags, 'stdio'], project, env, protocol=True)
    try:
        return child.initialize()
    finally:
        child.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grok', default='grok', help='installed official Grok executable')
    args = parser.parse_args()
    executable = shutil.which(args.grok)
    if not executable:
        parser.error('Grok executable not found')
    executable = str(Path(executable).resolve())
    with tempfile.TemporaryDirectory(prefix='ah-grok-feasibility-') as directory:
        root = Path(directory)
        home, project = root / 'home', root / 'project'
        grok_home = home / '.grok'
        grok_home.mkdir(parents=True)
        (project / '.grok').mkdir(parents=True)
        env = {'HOME': str(home), 'GROK_HOME': str(grok_home), 'TMPDIR': str(root),
               'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'NO_COLOR': '1', 'TERM': 'dumb',
               'RUST_LOG': 'off'}
        check(capture(executable, ['--version'], project, env).decode().strip() == PIN)
        print(PIN, flush=True)
        user = grok_home / 'config.toml'
        user.write_text('[models]\ndefault="grok-4.5"\n[cli]\nauto_update=false\n'
                        '[permission]\nrules=[{action="allow",tool="read"}]\n'
                        '[mcp_servers.ah_user]\ncommand="/usr/bin/false"\nenabled=true\n')
        local = project / '.grok' / 'config.toml'
        local.write_text('[mcp_servers.ah_project]\ncommand="/usr/bin/false"\nenabled=true\n')
        instructions = project / 'AGENTS.md'
        instructions.write_text('AH_PROJECT_INSTRUCTIONS_SENTINEL\n')
        originals = {path: path.read_bytes() for path in (user, local, instructions)}
        inspect(executable, project, env, [])
        inspect(executable, project, env, FILTERS)
        print('PASS: inspect retains synthetic user permission and user/project MCP '
              'entries with tool-filter flags; not ACP enforcement proof', flush=True)
        check(all(path.read_bytes() == data for path, data in originals.items()))
        # Remove MCP from the synthetic configs BEFORE initializing. An initializer
        # can start configured extensions; this probe does not test that lifecycle.
        user.write_text('[models]\ndefault="grok-4.5"\n[cli]\nauto_update=false\n')
        local.unlink()
        before_init = user.read_bytes()
        for label, top, agent, expected in [
                ('baseline', [], [], 'grok-4.5'),
                ('top-level model and filters', [*FILTERS, '-m', 'grok-4.6'], [], 'grok-4.5'),
                ('agent-level model', FILTERS, ['-m', 'grok-4.6'], 'grok-4.6')]:
            result = initialize(executable, project, env, top, agent)
            check(result['_meta']['modelState']['currentModelId'] == expected)
            check('tools' not in result and 'tools' not in result['_meta'])
            print('PASS: initialize-only ' + label + ' model=' + expected
                  + '; no top-level/meta tools inventory', flush=True)
        migration = b'\n[marketplace]\ndefault_skills_installs_purged = true\n'
        check(user.read_bytes() == before_init + migration and not local.exists())
        print('PASS: startup appended the synthetic marketplace migration flag', flush=True)
        check(instructions.read_bytes() == originals[instructions])
        check(not (grok_home / 'auth.json').exists())
        # Initialization writes support/log/index files under synthetic GROK_HOME.
        # Project contents must remain the original directory and instruction file.
        check({str(p.relative_to(project)) for p in project.rglob('*')}
              == {'.grok', 'AGENTS.md'})
        print('PASS: synthetic project preserved; no synthetic login store', flush=True)
        print('GATE NOT PASSED: complete pre-turn tool denial and login-preserving '
              'isolation remain unproven; no authenticate/session/prompt RPC sent.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, AttributeError,
            subprocess.TimeoutExpired):
        raise SystemExit(FAILURE)
