#!/usr/bin/env python3
"""P3.2 native-route boundary fixtures. No billable provider traffic."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'

class Trap(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def do_GET(self):
        self.server.requests.append(self.path)
        self.send_error(500)
    do_POST = do_GET

with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Trap) as trap:
    trap.requests = []
    thread = threading.Thread(target=trap.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{trap.server_port}/v1'
    cases = [(case, 2) for case in ['native-model-missing', 'route', 'native-provider', 'native-enabled', 'native-agent', 'widened', 'agent-widened', 'version']]
    cases += [('success', 0), ('read', 0), ('deny', 0), ('cancel-deadline', 3), ('session-model', 1), ('rpc-error', 4), ('preview', 0), ('missing-key', 2)]
    count = 0
    for case, expected in cases:
        for no_sync in [False, True]:
            with tempfile.TemporaryDirectory(prefix='ah-native-') as d:
                base = Path(d).resolve()
                (base/'opencode').symlink_to(FAKE)
                (base/'case').write_text(case)
                (base/'track-runtime-home').touch()
                # Malformed/unowned local config is deliberately irrelevant to
                # native execution. Neither planner nor ownership code may read it.
                sentinels = {'opencode.json': b'{ malformed local route SECRET_SENTINEL',
                             'opencode.jsonc': b'// conflicting custom project configuration',
                             '.ah-opencode-owner.json': b'manual receipt',
                             '.ah-opencode.lock': b'lock sentinel',
                             'user.txt': b'preserve dirty user content'}
                for name, content in sentinels.items():
                    (base/name).write_bytes(content)
                cfg = dict(version=1, mode='cloud-only',
                           native=dict(target='opencode', model='fixture', api_key_env='NATIVE_KEY'),
                           litellm=dict(api_base=endpoint, api_key_env='MISSING_LOCAL_KEY'))
                (base/'ah.json').write_text(json.dumps(cfg))
                env = {**os.environ, 'PATH': str(base)+':'+os.environ['PATH'],
                       'NATIVE_KEY': 'SECRET_SENTINEL', 'OPENCODE_API_KEY': 'poison',
                       'OPENCODE_CONFIG_CONTENT': 'poison', 'OPENCODE_AUTH_CONTENT': 'poison',
                       'OPENAI_BASE_URL': endpoint, 'LITELLM_API_KEY': 'poison',
                       'ANTHROPIC_API_KEY': 'poison'}
                env.pop('MISSING_LOCAL_KEY', None)
                if case == 'missing-key': env.pop('NATIVE_KEY')
                args = [str(BINARY), 'single', 'native task', '--project', str(base), '--timeout-secs', '1' if case == 'cancel-deadline' else '15']
                if no_sync: args += ['--no-sync']
                if case == 'preview': args += ['--preview']
                if case == 'read': args += ['--permissions', 'trusted']
                p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
                assert p.returncode == expected, (case, no_sync, p.returncode, p.stderr)
                assert 'SECRET_SENTINEL' not in p.stdout+p.stderr, case
                assert 'poison' not in p.stdout+p.stderr, case
                for name, content in sentinels.items():
                    assert (base/name).read_bytes() == content, (case, name)
                assert not list(base.glob('.ah-write-*')), case
                if case in ['success', 'read', 'deny', 'cancel-deadline', 'rpc-error']:
                    assert (base/'prompted').exists(), case
                else:
                    assert not (base/'prompted').exists(), case
                if case in ['preview', 'missing-key']:
                    assert not (base/'runtime-home').exists(), case
                else:
                    assert not Path((base/'runtime-home').read_text()).exists(), case
                if case == 'preview':
                    assert 'route: native OpenCode' in p.stdout
                    assert 'managed project config untouched' in p.stdout
                    assert 'planned changes: none' in p.stdout
                if case == 'read':
                    result=json.loads((base/'permission-result.json').read_text())
                    assert result['result']['outcome']['optionId'] == 'once', result
                if case == 'deny':
                    result=json.loads((base/'permission-result.json').read_text())
                    assert result['result']['outcome']['optionId'] == 'reject', result
                if case == 'cancel-deadline':
                    assert (base/'cancelled').exists(), case
                count += 1
    trap.shutdown()
    thread.join(timeout=2)
    assert trap.requests == [], trap.requests
print(f'PASS {count} native CLI cases; zero LiteLLM discovery/model requests; project sentinels preserved')
