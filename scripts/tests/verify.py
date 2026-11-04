#!/usr/bin/env python3
"""P5.5 trusted verification gates (D043) against fake OpenCode 2.2.5 and fake checks; no model traffic.

Distinguishes agent success, no verification, passed/failed/timed-out/cancelled
verification and untrusted-check rejection. Build target/debug/ah first.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'

# Fake check: records its context, writes to both streams, then acts on MODE.
CHECKER = '''#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time
mode, out = sys.argv[1], sys.argv[2]
with open(os.path.join(out, 'check-ran.json'), 'w') as f:
    json.dump(dict(cwd=os.getcwd(), env=sorted(os.environ), stdin=sys.stdin.read(),
                   pgid=os.getpgid(0), pid=os.getpid()), f)
print('CHECK_STDOUT', flush=True)
print('CHECK_STDERR', file=sys.stderr, flush=True)
if mode in ('linger', 'sleep'):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    open(os.path.join(out, 'descendant'), 'w').write(str(child.pid))
if mode == 'sleep':
    open(os.path.join(out, 'check-started'), 'w').close()
    time.sleep(60)
if mode == 'selfkill':
    os.kill(os.getpid(), signal.SIGKILL)
sys.exit({'pass': 0, 'linger': 0, 'fail': 3}.get(mode, 0))
'''


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A zombie awaiting its reaper is terminated.
    stat = subprocess.run(['/bin/ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout
    return bool(stat.strip()) and not stat.strip().startswith('Z')


def run(case, expected, *, mode='pass', verify='test', timeout=30, checks=None, machine=True,
        extra=(), interrupt=False, kill=False):
    with tempfile.TemporaryDirectory(prefix='ah-verify-project-') as p, \
         tempfile.TemporaryDirectory(prefix='ah-verify-tools-') as t:
        project, tools = Path(p).resolve(), Path(t).resolve()
        (project/'opencode').symlink_to(FAKE)
        (project/'case').write_text(case)
        checker = tools/'checker'
        checker.write_text(CHECKER)
        checker.chmod(0o755)
        if checks is None:
            checks = dict(test=dict(argv=[str(checker), mode, str(tools)], timeout_secs=timeout))
        (project/'ah.json').write_text(json.dumps(dict(version=1, mode='local-only', model='fixture',
            litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'), checks=checks)))
        args = [str(BINARY), 'single', 'Task', '--project', str(project), '--timeout-secs', '15', *extra]
        if verify:
            args += ['--verify', verify]
        if machine:
            args += ['--output', 'jsonl']
        env = {**os.environ, 'PATH': f'{project}:{tools}:' + os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'AH_RUNTIME_API_KEY': 'SECRET_SENTINEL',
               'OPENCODE_API_KEY': 'SECRET_SENTINEL'}
        proc = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        if interrupt:
            until = time.monotonic() + 15
            while not (tools/'check-started').exists() and time.monotonic() < until:
                time.sleep(.02)
            assert (tools/'check-started').exists(), 'check never started'
            proc.send_signal(signal.SIGKILL if kill else signal.SIGINT)
            if kill:
                # Nothing is left to clean up the orphaned check, which holds stderr.
                proc.wait(timeout=15)
                os.killpg(json.loads((tools/'check-ran.json').read_text())['pgid'], signal.SIGKILL)
        out, err = proc.communicate(timeout=60)
        assert proc.returncode == expected, (case, mode, proc.returncode, err)
        assert 'SECRET_SENTINEL' not in out + err
        ran = json.loads((tools/'check-ran.json').read_text()) if (tools/'check-ran.json').exists() else None
        descendant = int((tools/'descendant').read_text()) if (tools/'descendant').exists() else None
        result = None
        if machine:
            # stdout stays machine-only: check output went to stderr.
            records = [json.loads(line) for line in out.splitlines()]
            result = records[-1]
            assert result['type'] == 'result' and result['exit'] == expected, result
            result['types'] = [r['type'] for r in records]
        state = dict(project=project, tools=tools, prompted=(project/'prompted').exists(), ran=ran,
                     config=json.loads((project/'ah.json').read_text()),
                     descendant=descendant, out=out, err=err, result=result)
        print('PASS', case, mode, verify, expected, flush=True)
        return state


# Passed: exit 0 with a separate verification record; check context is pinned.
s = run('text', 0)
v = s['result']['verification']
assert v['check'] == 'test' and v['status'] == 'passed' and v['agent_outcome'] == 'succeeded', v
assert v['exit_code'] == 0 and v['signal'] is None and v['cleanup_confirmed'] is True and v['timeout_secs'] == 30, v
assert isinstance(v['duration_ms'], int), v
types = s['result']['types']
assert types.index('attempt.cleanup') < types.index('verification.started') < types.index('verification.finished') < types.index('result'), types
assert s['result']['response'] == 'OK'
ran = s['ran']
assert ran['cwd'] == str(s['project']) and ran['stdin'] == '', ran
assert not {'TEST_KEY', 'AH_RUNTIME_API_KEY', 'OPENCODE_API_KEY'} & set(ran['env']), ran['env']
assert 'CHECK_STDOUT' not in s['out'] and 'CHECK_STDOUT' in s['err'] and 'CHECK_STDERR' in s['err']
assert ran['pgid'] == ran['pid'], 'check runs in its own process group'

# No verification requested: agent success is reported, never labeled verified.
s = run('text', 0, verify=None)
assert s['result']['verification'] is None and s['ran'] is None, s['result']
assert 'verification.started' not in s['result']['types']

# Failed: the agent succeeded but the gate decides the exit.
s = run('text', 1, mode='fail')
v = s['result']['verification']
assert v['status'] == 'failed' and v['exit_code'] == 3 and v['agent_outcome'] == 'succeeded', v
assert s['result']['outcome'] == 'failed' and s['result']['response'] == 'OK', s['result']
assert 'repair' in s['result']['recovery'], s['result']['recovery']
s = run('text', 1, mode='selfkill')
v = s['result']['verification']
assert v['status'] == 'failed' and v['exit_code'] is None and v['signal'] == signal.SIGKILL, v

# Timed out: the group is terminated, including a lingering descendant.
s = run('text', 1, mode='sleep', timeout=1)
v = s['result']['verification']
assert v['status'] == 'timed_out' and v['cleanup_confirmed'] is True and v['exit_code'] is None, v
assert s['descendant'] and not alive(s['descendant']), 'descendant survived timeout'

# A passing check's lingering descendant is still cleaned up.
s = run('text', 0, mode='linger')
assert s['result']['verification']['cleanup_confirmed'] is True
assert s['descendant'] and not alive(s['descendant']), 'descendant survived passing check'

# Cancelled while the check runs: exit 3, group terminated.
s = run('text', 3, mode='sleep', interrupt=True)
v = s['result']['verification']
assert v['status'] == 'cancelled' and v['agent_outcome'] == 'succeeded' and v['cleanup_confirmed'] is True, v
assert not alive(s['descendant'])

# Agent did not succeed: the check never runs and the backend exit stands.
s = run('known-failure', 1)
v = s['result']['verification']
assert v['status'] == 'not_run' and v['agent_outcome'] == 'failed' and s['ran'] is None, v
assert 'verification.started' not in s['result']['types']
s = run('version', 2)
assert s['result']['verification']['agent_outcome'] == 'rejected' and s['ran'] is None

# Error: the pinned program vanished before the gate (spawn failure) → exit 1.
s = run('remove-check', 1)
v = s['result']['verification']
assert v['status'] == 'error' and v['agent_outcome'] == 'succeeded' and s['ran'] is None, v
assert v['exit_code'] is None and v['cleanup_confirmed'] is None, v

# Untrusted: undeclared names and in-project programs reject before launch.
s = run('text', 2, verify='lint')
assert s['result']['reason'] == 'verification check is not defined in config checks', s['result']
assert not s['prompted'] and s['ran'] is None and s['result']['attempts'] == []
s = run('text', 2, checks=dict(test=dict(argv=['opencode'])))
assert 'outside the project' in s['result']['reason'] and not s['prompted'], s['result']
s = run('text', 2, checks=dict(test=dict(argv=['scripts/check.sh'])))
assert 'absolute path or a bare name' in s['result']['reason'] and not s['prompted']

# An agent rewrite of ah.json during the turn cannot change the pinned check.
s = run('rewrite-config', 0)
assert s['result']['verification']['status'] == 'passed' and s['ran'] is not None
assert s['config']['checks']['test']['argv'] == ['/usr/bin/false'], 'fake did not rewrite ah.json'

# Human mode: stdout is only the response; the final line names the gate.
s = run('text', 1, mode='fail', machine=False)
assert s['out'] == 'OK', s['out']
final = s['err'].strip().splitlines()[-1]
assert 'outcome=Failed; verification="test" "failed"' in final, final
assert 'verification check test started' in s['err'] and 'verification check test failed (exit 3)' in s['err']

# The response is flushed before the check runs: a harness crash during the
# check cannot lose its unterminated last line (P5.4).
s = run('text', -signal.SIGKILL, mode='sleep', machine=False, interrupt=True, kill=True)
assert s['out'] == 'OK', s['out']

# Preview reports the pinned check without running it.
s = run('text', 0, machine=False, extra=['--preview'])
assert s['ran'] is None and not s['prompted']
line = next(l for l in s['out'].splitlines() if l.startswith('verification: '))
assert 'check "test"' in line and '2 arguments omitted' in line and 'never by preview' in line, line
assert 'pass' not in line.replace(str(s['tools']), ''), 'arguments are omitted'
s = run('text', 0, machine=False, verify=None, extra=['--preview'])
assert 'verification: none (no --verify)' in s['out']
print('PASS verification gate fixtures')
