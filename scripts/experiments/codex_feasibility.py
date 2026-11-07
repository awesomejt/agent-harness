#!/usr/bin/env python3
"""Opt-in Codex 0.166.0 pre-turn discovery; never starts a thread or model turn.

Uses only synthetic HOME/CODEX_HOME/config, no operator credentials. Exit 0
means the recorded observations reproduced, NOT that adapter feasibility passed.
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

PIN = 'codex-cli 0.166.0'
LIMIT = 2 * 1024 * 1024


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


class Server:
    def __init__(self, executable, project, env, overrides):
        self.child = subprocess.Popen(
            [executable, 'app-server', '--listen', 'stdio://', *overrides],
            cwd=project, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.child.stdout, selectors.EVENT_READ, 'out')
        self.selector.register(self.child.stderr, selectors.EVENT_READ, 'err')
        self.buffer = b''
        self.count = 0
        self.next_id = 1

    def send(self, method, params, identifier=None):
        # A hard allowlist keeps future edits from accidentally submitting work.
        check(method in {'initialize', 'initialized', 'config/read'},
              'probe method is outside the non-inference allowlist')
        message = {'method': method, 'params': params}
        if identifier is not None:
            message['id'] = identifier
        self.child.stdin.write((json.dumps(message) + '\n').encode())
        self.child.stdin.flush()

    def request(self, method, params):
        identifier = self.next_id
        self.next_id += 1
        self.send(method, params, identifier)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                message = json.loads(line)
                check(isinstance(message, dict), 'malformed protocol message')
                check(not ('id' in message and 'method' in message),
                      'unexpected server request; no approval response sent')
                if message.get('id') == identifier:
                    check('error' not in message, 'discovery RPC rejected (details withheld)')
                    result = message['result']
                    check(isinstance(result, dict), 'malformed discovery result')
                    return result
            for key, _ in self.selector.select(min(.2, max(0, deadline - time.monotonic()))):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    self.selector.unregister(key.fileobj)
                    check(key.data != 'out', 'unexpected protocol EOF')
                    continue
                self.count += len(data)
                check(self.count <= LIMIT, 'probe output budget exceeded')
                if key.data == 'out':
                    self.buffer += data
        raise RuntimeError('discovery RPC timed out')

    def close(self):
        try:
            if not self.child.stdin.closed:
                self.child.stdin.close()
            try:
                self.child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        finally:
            try:
                os.killpg(self.child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.child.wait(timeout=2)
            self.selector.close()
            self.child.stdout.close()
            self.child.stderr.close()


def read_config(executable, project, env, overrides):
    server = Server(executable, project, env, overrides)
    try:
        server.request('initialize', {'clientInfo': {
            'name': 'agent_harness_feasibility', 'version': '0.1.0'}})
        server.send('initialized', {})
        result = server.request('config/read', {
            'includeLayers': True, 'cwd': str(project)})
        check(isinstance(result.get('config'), dict), 'missing effective config')
        return result['config']
    finally:
        server.close()


def capture(command, project, env):
    # Used only for bounded installed help/parser/schema commands, never inference.
    # The file-size check is post-exit, not a live disk cap or an arbitrary-binary sandbox.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        child = subprocess.Popen(command, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, start_new_session=True)
        try:
            child.wait(timeout=10)
            check(out.tell() + err.tell() <= LIMIT, 'command output budget exceeded')
            out.seek(0)
            err.seek(0)
            return child.returncode, out.read(), err.read()
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', default='codex', help='installed official Codex executable')
    args = parser.parse_args()
    executable = shutil.which(args.codex)
    if not executable:
        parser.error('Codex executable not found')
    executable = str(Path(executable).resolve())
    with tempfile.TemporaryDirectory(prefix='ah-codex-feasibility-') as directory:
        root = Path(directory)
        home, codex_home, project = (root / name for name in ('home', 'codex', 'project'))
        for path in (home, codex_home, project):
            path.mkdir()
        env = {'HOME': str(home), 'CODEX_HOME': str(codex_home),
               'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'TMPDIR': str(root), 'RUST_LOG': 'off'}
        code, out, _ = capture([executable, '--version'], project, env)
        check(code == 0 and out.decode().strip() == PIN, 'installed Codex pin differs')
        print(PIN, flush=True)
        config = codex_home / 'config.toml'
        config.write_text('model = "ah-user-sentinel"\n'
                          'developer_instructions = "AH_USER_SENTINEL"\n'
                          '[features]\nshell_tool = true\n'
                          '[mcp_servers.ah_sentinel]\ncommand = "/usr/bin/false"\n')
        original = config.read_bytes()
        baseline = read_config(executable, project, env, [])
        check(baseline.get('model') == 'ah-user-sentinel'
              and baseline.get('developer_instructions') == 'AH_USER_SENTINEL'
              and baseline.get('features', {}).get('shell_tool') is True
              and baseline.get('mcp_servers', {}).get('ah_sentinel', {}).get('enabled') is True,
              'synthetic user config inheritance changed')
        print('PASS: synthetic user model/instructions/shell/MCP settings inherited', flush=True)
        overrides = ['-c', 'features.shell_tool=false', '-c', 'mcp_servers={}']
        narrowed = read_config(executable, project, env, overrides)
        check(narrowed.get('features', {}).get('shell_tool') is False,
              'shell override did not reach effective config')
        check(narrowed.get('developer_instructions') == 'AH_USER_SENTINEL'
              and narrowed.get('mcp_servers', {}).get('ah_sentinel', {}).get('enabled') is True,
              'empty-table override inheritance changed')
        print('PASS: shell=false reflected; empty MCP table retained enabled sentinel', flush=True)
        disabled = read_config(executable, project, env,
                               ['-c', 'mcp_servers.ah_sentinel.enabled=false'])
        check(disabled.get('mcp_servers', {}).get('ah_sentinel', {}).get('enabled') is False,
              'per-server disable did not reach effective config')
        print('PASS: explicit known-server disable reflected (not blanket isolation)', flush=True)
        for option in ('--ignore-user-config', '--ignore-rules'):
            code, _, err = capture([executable, 'app-server', option], project, env)
            check(code == 2 and b'unexpected argument' in err and option.encode() in err,
                  'app-server parser behavior changed')
            print('PASS: app-server rejects ' + option, flush=True)
        schemas = root / 'schema'
        code, _, _ = capture([executable, 'app-server', 'generate-json-schema',
                              '--out', str(schemas)], project, env)
        check(code == 0, 'schema generation failed')
        response = json.loads((schemas / 'v2/ConfigReadResponse.json').read_text())
        tools = response['definitions']['ToolsV2']['properties']
        check(set(tools) == {'web_search'}, 'stable ToolsV2 schema changed; reassess gate')
        thread = json.loads((schemas / 'v2/ThreadStartResponse.json').read_text())
        check('tools' not in thread['properties'], 'thread tool inventory changed; reassess gate')
        print('PASS: stable ToolsV2 has only web_search; thread response lacks tools field', flush=True)
        check(config.read_bytes() == original, 'synthetic config was modified')
        check(not list(project.iterdir()), 'probe wrote into disposable project')
        check(not (codex_home / 'auth.json').exists(), 'unexpected synthetic login store')
        print('PASS: synthetic config/project preserved; no copied login store', flush=True)
        print('GATE NOT PASSED: no complete pre-turn tool enforcement/isolation proof; '
              'no thread, turn, model request or permission grant was sent.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, AttributeError,
            subprocess.TimeoutExpired):
        raise SystemExit('Codex feasibility probe failed; raw protocol/diagnostics withheld')
