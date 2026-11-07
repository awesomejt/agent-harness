#!/usr/bin/env python3
"""Malformed protocol must fail sanitized through the experiment's public CLI.

No installed Codex, credentials, thread, model request or network is required.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

PROBE = Path(__file__).resolve().parents[1] / 'experiments/codex_feasibility.py'
PRIVATE = 'AH_RAW_DIAGNOSTIC_SENTINEL'


def main():
    cases = [None, [], 7, PRIVATE,
             {'id': 1, 'result': None}, {'id': 1, 'result': []},
             {'id': 1, 'result': PRIVATE},
             {'id': 2, 'result': {'config': None}},
             {'id': 2, 'result': {'config': []}}]
    for section in ('features', 'mcp_servers'):
        config = {'model': 'ah-user-sentinel',
                  'developer_instructions': 'AH_USER_SENTINEL',
                  'features': {'shell_tool': True},
                  'mcp_servers': {'ah_sentinel': {'enabled': True}}}
        config[section] = [PRIVATE]
        cases.append({'id': 2, 'result': {'config': config}})
    with tempfile.TemporaryDirectory(prefix='ah-codex-malformed-') as directory:
        fake = Path(directory) / 'codex'
        for index, payload in enumerate(cases):
            # Malformed init replies are immediate; malformed config replies follow
            # a valid handshake so both parsing stages are exercised.
            during_config = isinstance(payload, dict) and payload.get('id') == 2
            source = f'''#!{sys.executable}
import json, sys
if sys.argv[1:] == ['--version']:
    print('codex-cli 0.166.0')
else:
    for line in sys.stdin:
        request = json.loads(line)
        if request['method'] == 'initialize':
            print(json.dumps({{'id': 1, 'result': {{}}}}) if {during_config!r}
                  else {json.dumps(payload)!r}, flush=True)
        elif request['method'] == 'config/read':
            print({json.dumps(payload)!r}, flush=True)
'''
            fake.write_text(source)
            fake.chmod(0o700)
            result = subprocess.run([sys.executable, str(PROBE), '--codex', str(fake)],
                                    capture_output=True, text=True, timeout=15)
            assert result.returncode == 1, f'case {index}: expected refusal'
            assert result.stderr == ('Codex feasibility probe failed; '
                                     'raw protocol/diagnostics withheld\n'), index
            assert PRIVATE not in result.stdout + result.stderr, index
            assert 'Traceback' not in result.stdout + result.stderr, index
    print(f'Codex feasibility malformed-protocol cases: {len(cases)}/{len(cases)} pass')


if __name__ == '__main__':
    main()
