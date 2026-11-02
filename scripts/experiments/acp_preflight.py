#!/usr/bin/env python3
"""No-prompt ACP connectivity probe; diagnostic tooling, not the Rust runtime.

Uses a disposable HOME/project and a deliberately unreachable synthetic provider.
Never accepts prompts, credentials, client tool calls, or permission grants.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode', help='executable path')
    args = parser.parse_args()
    executable = shutil.which(args.opencode)
    if not executable:
        parser.error('OpenCode executable not found; supply --opencode /absolute/path')
    executable = str(Path(executable).resolve())
    with tempfile.TemporaryDirectory(prefix='ah-acp-preflight-') as root:
        base = Path(root)
        project = base / 'project'
        project.mkdir()
        config = {
            'autoupdate': False, 'share': 'disabled', 'plugin': [], 'mcp': {},
            'permission': {'*': 'deny'},
            'enabled_providers': ['harness-preflight'],
            'model': 'harness-preflight/unavailable',
            'small_model': 'harness-preflight/unavailable',
            'provider': {'harness-preflight': {
                'npm': '@ai-sdk/openai-compatible',
                'options': {'baseURL': 'http://127.0.0.1:9/v1', 'apiKey': 'unused'},
                'models': {'unavailable': {'name': 'No-prompt preflight only'}},
            }},
        }
        (project / 'opencode.json').write_text(json.dumps(config))
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': root,
               'XDG_CONFIG_HOME': str(base / 'config'),
               'XDG_DATA_HOME': str(base / 'data'),
               'XDG_CACHE_HOME': str(base / 'cache'),
               'XDG_STATE_HOME': str(base / 'state'),
               'OPENCODE_DISABLE_MODELS_FETCH': 'true',
               'OPENCODE_DISABLE_DEFAULT_PLUGINS': 'true',
               'OPENCODE_DISABLE_AUTOUPDATE': 'true'}
        version = subprocess.check_output([executable, '--version'], env=env, timeout=15).decode().strip()
        print('OpenCode:', version, flush=True)
        resolved = json.loads(subprocess.check_output(
            [executable, 'debug', 'config', '--pure'], cwd=project, env=env,
            stderr=subprocess.PIPE, timeout=30))
        if (resolved.get('permission') != {'*': 'deny'}
                or resolved.get('enabled_providers') != ['harness-preflight']
                or resolved.get('model') != 'harness-preflight/unavailable'
                or resolved.get('mcp') or resolved.get('plugin')):
            raise RuntimeError('Resolved configuration differs from probe restrictions')
        print('Resolved config: deny all; synthetic provider only; no MCP/plugins.', flush=True)
        with tempfile.TemporaryFile() as errors:
            child = subprocess.Popen([executable, 'acp', '--pure', '--cwd', str(project)],
                                     cwd=project, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=errors, start_new_session=True)
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            pending = b''

            def request(identifier, method, params):
                nonlocal pending
                child.stdin.write((json.dumps({'jsonrpc': '2.0', 'id': identifier,
                                               'method': method, 'params': params}) + '\n').encode())
                child.stdin.flush()
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if b'\n' not in pending:
                        if not selector.select(max(0, deadline - time.monotonic())):
                            break
                        chunk = os.read(child.stdout.fileno(), 65536)
                        if not chunk:
                            raise RuntimeError('ACP stdout closed before response')
                        pending += chunk
                        if len(pending) > 2_000_000:
                            raise RuntimeError('ACP response exceeded probe limit')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        message = json.loads(line)
                        if 'method' in message:
                            # This probe never implements client filesystem/terminal/approval operations.
                            if 'id' in message:
                                raise RuntimeError('Unexpected ACP client request; refusing probe')
                            continue
                        if message.get('id') == identifier:
                            if 'error' in message:
                                raise RuntimeError('ACP returned an error for ' + method)
                            return message['result']
                raise RuntimeError('ACP response deadline exceeded for ' + method)

            try:
                initialized = request(1, 'initialize', {
                    'protocolVersion': 1,
                    'clientInfo': {'name': 'ah-preflight', 'version': '0.1.0'},
                    'clientCapabilities': {'fs': {'readTextFile': False, 'writeTextFile': False},
                                           'terminal': False},
                })
                if initialized.get('protocolVersion') != 1:
                    raise RuntimeError('Unsupported ACP protocol version')
                print('initialize:', json.dumps(initialized, sort_keys=True), flush=True)
                session = request(2, 'session/new', {'cwd': str(project), 'mcpServers': []})
                if not session.get('sessionId'):
                    raise RuntimeError('Missing session identity')
                model_options = [x for x in session.get('configOptions', []) if x.get('id') == 'model']
                if (len(model_options) != 1
                        or model_options[0].get('currentValue') != 'harness-preflight/unavailable'):
                    raise RuntimeError('ACP session did not select the synthetic model')
                print('session/new: session identity and synthetic model confirmed', flush=True)
                print('session config:', json.dumps({k: v for k, v in session.items() if k != 'sessionId'}, sort_keys=True), flush=True)
                print('No session/prompt sent; synthetic route only.', flush=True)
            finally:
                selector.close()
                # Bound shutdown and reap this process even if protocol startup fails.
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                child.stdin.close()
                child.stdout.close()
                print('ACP process reaped; descendant cleanup is not proven.', flush=True)


if __name__ == '__main__':
    main()
