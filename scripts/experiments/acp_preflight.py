#!/usr/bin/env python3
"""ACP experiment tooling, not the Rust runtime.

Default: no-prompt connectivity probe with a synthetic unreachable provider.
--live: one fixed text prompt via an existing LiteLLM alias, with tools disabled.
Credentials come from the environment; no client tool calls or grants are accepted.
"""
import argparse
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
import urllib.request
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode', help='executable path')
    parser.add_argument('--live', action='store_true', help='send the fixed text-only probe prompt')
    parser.add_argument('--endpoint', help='LiteLLM API base URL (required with --live)')
    parser.add_argument('--model', help='existing LiteLLM alias (required with --live)')
    parser.add_argument('--key-env', default='LITELLM_API_KEY', help='API key environment variable name')
    args = parser.parse_args()
    if args.live and (not args.endpoint or not args.model):
        parser.error('--live requires explicit --endpoint and --model')
    alias = args.model if args.live else 'unavailable'
    target = 'harness-preflight/' + alias
    if args.live:
        parsed = urlsplit(args.endpoint)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            parser.error('endpoint must be an HTTP(S) base URL without credentials/query/fragment')
        key = os.environ.get(args.key_env)
        if not key:
            parser.error('API key environment variable is missing or empty')
        try:
            req = urllib.request.Request(args.endpoint.rstrip('/') + '/models',
                                         headers={'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(req, timeout=15) as response:
                aliases = json.load(response).get('data', [])
            if alias not in [x.get('id') for x in aliases]:
                parser.error('selected alias is absent from authenticated discovery')
        except Exception:
            parser.error('authenticated model discovery failed (raw error withheld)')
        print('Authenticated discovery: selected alias exists:', alias, flush=True)
    executable = shutil.which(args.opencode)
    if not executable:
        parser.error('OpenCode executable not found; supply --opencode /absolute/path')
    executable = str(Path(executable).resolve())
    with tempfile.TemporaryDirectory(prefix='ah-acp-preflight-') as root:
        base = Path(root)
        project = base / 'project'
        project.mkdir()
        # v1.18.30 appends a tool-output directory allow unless this exact glob is denied.
        permission = {'*': 'deny', 'external_directory': {
            '*': 'deny', str(base / 'data' / 'opencode' / 'tool-output' / '*'): 'deny'}}
        config = {
            'autoupdate': False, 'share': 'disabled', 'plugin': [], 'mcp': {},
            'permission': permission, 'tools': {'*': False},
            'enabled_providers': ['harness-preflight'],
            'model': target,
            'small_model': target,
            'provider': {'harness-preflight': {
                'npm': '@ai-sdk/openai-compatible',
                'options': {'baseURL': args.endpoint.rstrip('/') if args.live else 'http://127.0.0.1:9/v1',
                            'apiKey': '{env:AH_PROBE_API_KEY}' if args.live else 'unused'},
                'models': {alias: {'name': alias}},
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
        if args.live:
            env['AH_PROBE_API_KEY'] = key
        version = subprocess.check_output([executable, '--version'], env=env, timeout=15).decode().strip()
        print('OpenCode:', version, flush=True)
        resolved = json.loads(subprocess.check_output(
            [executable, 'debug', 'config', '--pure'], cwd=project, env=env,
            stderr=subprocess.PIPE, timeout=30))
        if (resolved.get('permission') != permission
                or resolved.get('enabled_providers') != ['harness-preflight']
                or resolved.get('model') != target
                or resolved.get('small_model') != target
                or resolved.get('tools') != {'*': False}
                or resolved.get('share') != 'disabled'
                or resolved.get('autoupdate') is not False
                or resolved.get('mcp') or resolved.get('plugin')):
            raise RuntimeError('Resolved configuration differs from probe restrictions')
        print('Resolved config: deny all; tools disabled; sole selected provider; no MCP/plugins.', flush=True)
        agent = json.loads(subprocess.check_output(
            [executable, 'debug', 'agent', 'build', '--pure'], cwd=project, env=env,
            stderr=subprocess.PIPE, timeout=30))
        rules = agent.get('permission', [])
        expected = [{'permission': '*', 'pattern': '*', 'action': 'deny'},
                    {'permission': 'external_directory', 'pattern': '*', 'action': 'deny'},
                    {'permission': 'external_directory', 'pattern':
                     str(base / 'data' / 'opencode' / 'tool-output' / '*'), 'action': 'deny'}]
        if rules[-3:] != expected:
            raise RuntimeError('Build agent does not end with expected deny-all rules')
        print('Build agent effective permission: final rules deny all, including tool-output directory.', flush=True)
        with tempfile.TemporaryFile() as errors:
            child = subprocess.Popen([executable, 'acp', '--pure', '--cwd', str(project)],
                                     cwd=project, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=errors, start_new_session=True)
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            pending = b''
            text_chunks = []
            event_counts = {'agent_message_chunk': 0, 'agent_thought_chunk': 0, 'other': 0}

            def request(identifier, method, params, timeout=30):
                nonlocal pending
                child.stdin.write((json.dumps({'jsonrpc': '2.0', 'id': identifier,
                                               'method': method, 'params': params}) + '\n').encode())
                child.stdin.flush()
                deadline = time.monotonic() + timeout
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
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            message = json.loads(line)
                        except json.JSONDecodeError:
                            raise RuntimeError('Non-JSON line on ACP stdout') from None
                        if not isinstance(message, dict):
                            raise RuntimeError('ACP message must be a JSON object')
                        if 'method' in message:
                            # This probe never implements client filesystem/terminal/approval operations.
                            if 'id' in message:
                                raise RuntimeError('Unexpected ACP client request; refusing probe')
                            if message['method'] == 'session/update':
                                update = message.get('params', {}).get('update', {})
                                kind = update.get('sessionUpdate')
                                if kind in ('tool_call', 'tool_call_update'):
                                    raise RuntimeError('Unexpected tool activity in text-only probe')
                                event_counts[kind if kind in event_counts else 'other'] += 1
                                if kind == 'agent_message_chunk':
                                    content = update.get('content', {})
                                    if content.get('type') == 'text':
                                        text_chunks.append(content.get('text', ''))
                                        if sum(map(len, text_chunks)) > 100_000:
                                            raise RuntimeError('Probe text exceeded output bound')
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
                        or model_options[0].get('currentValue') != target):
                    raise RuntimeError('ACP session did not select the requested model')
                print('session/new: session identity and selected model confirmed', flush=True)
                print('session config:', json.dumps({k: v for k, v in session.items() if k != 'sessionId'}, sort_keys=True), flush=True)
                if args.live:
                    print('Sending fixed text-only prompt; deadline 180 seconds.', flush=True)
                    result = request(3, 'session/prompt', {
                        'sessionId': session['sessionId'],
                        'prompt': [{'type': 'text', 'text':
                                    'Reply with exactly AH_ACP_P1_2_OK and nothing else. Do not use tools.'}],
                    }, timeout=180)
                    print('session/update counts:', json.dumps(event_counts, sort_keys=True), flush=True)
                    if result.get('stopReason') != 'end_turn':
                        raise RuntimeError('Prompt did not terminate with end_turn')
                    if ''.join(text_chunks).strip() != 'AH_ACP_P1_2_OK':
                        print('Marker mismatch: text characters:', sum(map(len, text_chunks)),
                              'marker present:', 'AH_ACP_P1_2_OK' in ''.join(text_chunks), flush=True)
                        raise RuntimeError('Assistant text did not match explicit marker (text withheld)')
                    print('session/prompt: stopReason=end_turn; exact explicit marker received.', flush=True)
                else:
                    print('No session/prompt sent; synthetic route only.', flush=True)
            except Exception:
                # Report size only: arbitrary child stderr must not leak raw secrets.
                errors.seek(0, os.SEEK_END)
                print(f'ACP stderr: {errors.tell()} bytes (content withheld).', file=sys.stderr)
                raise
            finally:
                original_failure = sys.exc_info()[0] is not None
                selector.close()
                # Bound shutdown and reap this process even if protocol startup fails.
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print('ACP direct child could not be reaped within deadline.', file=sys.stderr)
                child.stdin.close()
                child.stdout.close()
                if child.returncode is not None:
                    print('ACP process reaped; descendant cleanup is not proven.', flush=True)
                elif not original_failure:
                    raise RuntimeError('ACP direct-child cleanup deadline exceeded')


if __name__ == '__main__':
    main()
