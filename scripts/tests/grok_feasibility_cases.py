#!/usr/bin/env python3
"""Offline public-CLI protocol, output/deadline and process-group probe checks."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PROBE = Path(__file__).resolve().parents[1] / 'experiments/grok_feasibility.py'
PRIVATE = 'AH_RAW_DIAGNOSTIC_SENTINEL'
FAILURE = 'Grok feasibility probe failed; raw protocol/diagnostics withheld\n'
VALID = {'jsonrpc': '2.0', 'id': 1, 'result': {
    'protocolVersion': 1, 'agentCapabilities': {}, 'authMethods': [],
    '_meta': {'agentVersion': '1.0.70', 'defaultAuthMethodId': None,
              'modelState': {'currentModelId': 'grok-4.5'}}}}


def source(payload, behavior, log, descendant):
    return f'''#!{sys.executable}
import json, os, subprocess, sys, time
args = sys.argv[1:]
if args == ['--version']:
    print('grok 1.0.70 (f50904eaee6c)')
elif args[-2:] == ['inspect', '--json']:
    if {behavior!r} == 'bad-inspect':
        print({json.dumps(payload)!r})
    else:
        print(json.dumps({{'grokVersion': '1.0.70', 'permissions': {{'loaded': 1}},
            'mcpServers': [{{'name': 'ah_user'}}, {{'name': 'ah_project'}}]}}))
else:
    request = json.loads(sys.stdin.readline())
    with open({str(log)!r}, 'a') as out:
        out.write(request['method'] + '\\n')
    if request['method'] != 'initialize':
        sys.exit(9)
    behavior = {behavior!r}
    if behavior in ('descendant', 'timeout', 'flood'):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        with open({str(descendant)!r}, 'a') as out:
            out.write(str(child.pid) + '\\n')
    if behavior == 'timeout':
        time.sleep(30)
    if behavior == 'flood':
        sys.stderr.write({PRIVATE!r} * 100000); sys.stderr.flush()
    if behavior == 'invalid-json':
        print({PRIVATE!r}, flush=True)
    elif behavior == 'eof':
        sys.exit(0)
    else:
        payload = json.loads({json.dumps(payload)!r})
        if behavior in ('valid', 'descendant'):
            # Only an agent-level model override changes this fake's result.
            agent_args = args[args.index('agent') + 1:]
            if '-m' in agent_args:
                payload['result']['_meta']['modelState']['currentModelId'] = 'grok-4.6'
        if behavior == 'descendant':
            from pathlib import Path
            config = Path(os.environ['GROK_HOME']) / 'config.toml'
            migration = '\\n[marketplace]\\ndefault_skills_installs_purged = true\\n'
            if migration not in config.read_text():
                with config.open('a') as out: out.write(migration)
        print(json.dumps(payload), flush=True)
    if behavior == 'descendant':
        time.sleep(30)
'''


def run(fake):
    return subprocess.run([sys.executable, str(PROBE), '--grok', str(fake)],
                          capture_output=True, text=True, timeout=20)


def alive(pid):
    result = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)],
                            capture_output=True, text=True, timeout=2)
    return result.returncode == 0 and not result.stdout.strip().startswith('Z')


def main():
    malformed = [None, [], 7, PRIVATE,
                 {'jsonrpc': '2.0', 'id': True, 'result': {}},
                 {'jsonrpc': '2.0', 'id': 2, 'result': {}},
                 {'jsonrpc': '2.0', 'id': 1, 'error': {'message': PRIVATE}},
                 {'jsonrpc': '2.0', 'id': 1, 'method': 'session/request_permission',
                  'params': {'private': PRIVATE}},
                 {'jsonrpc': '2.0', 'id': 1, 'result': None}]
    for key, value in [('protocolVersion', True), ('agentCapabilities', []),
                       ('authMethods', [PRIVATE]), ('_meta', []),
                       ('_meta', {'agentVersion': '1.0.70', 'modelState': []})]:
        payload = json.loads(json.dumps(VALID))
        payload['result'][key] = value
        malformed.append(payload)
    cases = [(payload, 'malformed') for payload in malformed]
    cases += [(VALID, behavior) for behavior in ('invalid-json', 'eof', 'timeout', 'flood')]
    cases += [(payload, 'bad-inspect') for payload in [None, [],
        {'grokVersion': '1.0.70', 'permissions': [], 'mcpServers': []},
        {'grokVersion': '1.0.70', 'permissions': {'loaded': 1}, 'mcpServers': [PRIVATE]}]]
    with tempfile.TemporaryDirectory(prefix='ah-grok-probe-cases-') as directory:
        root = Path(directory)
        fake, log, descendant = (root / name for name in ('grok', 'methods', 'descendant'))
        for index, (payload, behavior) in enumerate(cases):
            fake.write_text(source(payload, behavior, log, descendant))
            fake.chmod(0o700)
            result = run(fake)
            assert result.returncode == 1, (index, result.stdout, result.stderr)
            assert result.stderr == FAILURE, (index, result.stderr)
            assert PRIVATE not in result.stdout + result.stderr, index
        # Successful replies still clean up the child and its descendants.
        fake.write_text(source(VALID, 'descendant', log, descendant))
        result = run(fake)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert 'GATE NOT PASSED' in result.stdout
        pids = [int(line) for line in descendant.read_text().splitlines()]
        assert len(pids) == 5  # timeout, flood, and the three successful initializers
        deadline = time.monotonic() + 2
        while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(.05)
        assert not any(alive(pid) for pid in pids), 'probe left a running descendant'
        assert set(log.read_text().splitlines()) == {'initialize'}
        # Refused methods fail before writing anything to a protocol pipe.
        spec = importlib.util.spec_from_file_location('grok_probe', PROBE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        child = module.Child.__new__(module.Child)
        for method in ('authenticate', 'session/new', 'session/prompt', 'session/request_permission'):
            try:
                child.send(method)
            except RuntimeError:
                continue
            raise AssertionError('RPC allowlist widened')
    print(f'Grok feasibility: {len(cases)} sanitized refusals, success/descendant cleanup '
          'and RPC allowlist pass')


if __name__ == '__main__':
    main()
