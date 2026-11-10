#!/usr/bin/env python3
"""Offline command/refusal and owned-server lifecycle checks; no provider runtime."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_contained as probe


def refuses(action):
    try:
        action()
    except (RuntimeError, ValueError):
        return
    raise AssertionError('unsafe input was accepted')


def main():
    calls = []
    original = probe.capture
    probe.capture = lambda *args, **kwargs: calls.append(args) or (b'', b'')
    try:
        for command, url in [(('auth', 'login'), 'http://127.0.0.1:1'),
                             (('acp',), None), (('debug', 'config'), None),
                             (('debug', 'paths'), 'http://127.0.0.1:1')]:
            refuses(lambda: probe.diagnostic(Path('/unused'), Path('/unused'), {}, '', command, url))
        assert not calls
    finally:
        probe.capture = original
    for port in (True, 0, 65536, '443'):
        refuses(lambda: probe.contained_profile(Path('/scratch'), Path('/operator'), port))
    model = {'providerID': 'openai', 'model': 'synthetic'}
    rules = [{'action': '*', 'resource': '*', 'effect': 'deny'}]
    agent = {'id': 'build', 'model': None, 'permissions': rules,
             'request': {'settings': {}, 'headers': {}, 'body': {}}}
    probe.validate_agents([agent], model, rules, False)
    for mutation in ({'model': {'id': 'foreign', 'providerID': 'other'}},
                     {'permissions': rules + [{'action': 'shell', 'resource': '*', 'effect': 'allow'}]},
                     {'request': {'settings': {}, 'headers': {'endpoint': 'foreign'}, 'body': {}}}):
        refuses(lambda: probe.validate_agents([dict(agent, **mutation)], model, rules, False))
    refuses(lambda: probe.validate_agents([agent], model, rules, True))

    # These synthetic scripts never import or run OpenCode. The owned server
    # helper applies the actual sandbox and verifies pipe/deadline cleanup.
    probe.TIMEOUT = .5
    probe.LIMIT = 8192
    with tempfile.TemporaryDirectory(prefix='ah-contained-cases-') as directory:
        root = Path(directory).resolve()
        fixture = root / 'fake-server'
        env = {'HOME': str(root), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin'}
        policy = probe.contained_profile(root, Path.home())
        for scenario in ('normal', 'descendant', 'early-exit', 'bad-ready', 'never-ready', 'overflow'):
            fixture.write_text('#!' + probe.PYTHON + '\n' + '''
import os,sys,time,json,subprocess
from pathlib import Path
Path('pid').write_text(str(os.getpid()))
scenario = SCENARIO
if scenario == 'early-exit': sys.exit(0)
if scenario == 'never-ready': time.sleep(20)
if scenario == 'bad-ready': print('{}',flush=True)
else: print(json.dumps({'url':'http://127.0.0.1:'+sys.argv[-1]}),flush=True)
if scenario == 'overflow':
 sys.stderr.write('x'*20000);sys.stderr.flush()
if scenario == 'descendant':
 child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
 Path('descendant-pid').write_text(str(child.pid))
sys.stdin.read()
'''.replace('SCENARIO', repr(scenario)))
            fixture.chmod(0o700)
            entered = False
            failed = False
            start = time.monotonic()
            try:
                with probe.owned_server(fixture, root, env, policy, 49152):
                    entered = True
                    if scenario == 'overflow':
                        time.sleep(.2)
            except Exception:
                failed = True
            assert failed == (scenario not in ('normal', 'descendant')), scenario
            if scenario != 'overflow':
                assert entered == (scenario in ('normal', 'descendant')), scenario
            assert time.monotonic() - start < 6, scenario
            pid = int((root / 'pid').read_text())
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise AssertionError('server survived cleanup: ' + scenario)
            if scenario == 'descendant':
                pid = int((root / 'descendant-pid').read_text())
                result = subprocess.run(['/bin/ps', '-o', 'stat=', '-p', str(pid)],
                                        capture_output=True, text=True, timeout=2)
                assert result.returncode == 1 or result.stdout.strip().startswith('Z'), 'descendant survived cleanup'
    print('PASS: command guards, narrowing mutations and 6 synthetic server lifecycle cases')


if __name__ == '__main__':
    main()
