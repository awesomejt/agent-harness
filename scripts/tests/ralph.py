#!/usr/bin/env python3
"""P6.2/P6.3 Ralph loops (D045) against fake OpenCode 2.2.5.

Covers fresh runtime context and private state per iteration, the fixed
header and prompt snapshot, durable records and their privacy, both bounds,
completion only from a claim plus a passing check, rejected claims and the
repair iteration, false, stale and DONE-file signals, check outcomes that
stop the run, interrupted and cancelled iterations, explicit resume choices,
the lock shared with sequences, read-only show/preview and argument rules.
No model traffic. Build target/debug/ah first.
"""
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'
# Runs in the project. It passes once the agent wrote `fixed`; otherwise it
# exits with tools/check-exit (default 0). tools/check-hang outlasts timeouts.
CHECKER = ('#!/bin/sh\necho "$1" >> "$2/checks.log"\n[ -f "$2/check-hang" ] && sleep 30\n'
           '[ -f fixed ] && exit 0\nexit "$(cat "$2/check-exit" 2>/dev/null || echo 0)"\n')


class Fixture:
    def __init__(self, task='Work on the task.\n', check_exit=None, check_timeout=None):
        self.dirs = [tempfile.TemporaryDirectory(prefix=f'ah-ralph-{n}-') for n in ('project', 'tools', 'home')]
        self.project, self.tools, self.home = (Path(d.name).resolve() for d in self.dirs)
        self.state = self.home / 'state'
        (self.project / 'opencode').symlink_to(FAKE)
        (self.project / 'case').write_text('sequence')
        (self.project / 'track-runtime-home').touch()
        self.task = self.project / 'TASK.md'
        self.task.write_text(task)
        checker = self.tools / 'checker'
        checker.write_text(CHECKER)
        checker.chmod(0o755)
        if check_exit is not None:
            (self.tools / 'check-exit').write_text(str(check_exit))
        test = dict(argv=[str(checker), 'ARGV_SENTINEL', str(self.tools)])
        if check_timeout:
            test['timeout_secs'] = check_timeout
        config = dict(version=1, mode='local-only', model='fixture',
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'),
                      checks=dict(test=test, other=dict(argv=[str(checker), 'ARGV_SENTINEL', str(self.tools)])))
        (self.project / 'ah.json').write_text(json.dumps(config))

    def env(self, **extra):
        env = {**os.environ, 'PATH': f'{self.project}:{self.tools}:' + os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'XDG_STATE_HOME': str(self.state)}
        env.update(extra)
        return {k: v for k, v in env.items() if v is not None}

    def start(self, command, *args, verify=True):
        argv = [str(BINARY), command, *args]
        if args[0] in ('run', 'resume'):
            if args[0] == 'run':
                argv += ['--project', str(self.project)]
            argv += ['--timeout-secs', '15']
            if verify:
                argv += ['--verify', 'test']
        return subprocess.Popen(argv, env=self.env(), cwd=self.project, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                start_new_session=True)

    def ah(self, *args, expect, command='ralph', verify=True):
        before = len(self.prompts())
        proc = self.start(command, *args, verify=verify)
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == expect, (args, proc.returncode, out, err)
        assert 'SECRET_SENTINEL' not in out + err and 'ARGV_SENTINEL' not in out + err
        print('PASS', command, ' '.join(args[:2]), expect, flush=True)
        return out, err, self.prompts()[before:]

    def prompts(self):
        log = self.project / 'prompts.jsonl'
        return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

    def checks(self):
        log = self.tools / 'checks.log'
        return log.read_text().split() if log.exists() else []

    def wait_checking(self):
        until = time.monotonic() + 15
        while not (self.tools / 'checks.log').exists():
            assert time.monotonic() < until, 'check never started'
            time.sleep(.02)

    def wait_sleeping(self):
        until = time.monotonic() + 15
        while not (self.project / 'sleeping').exists():
            assert time.monotonic() < until, 'iteration never started'
            time.sleep(.02)
        (self.project / 'sleeping').unlink()

    def runs(self):
        return sorted(p.stem for p in (self.state / 'agent-harness/ralph').glob('r*.json'))

    def record(self, run):
        path = self.state / f'agent-harness/ralph/{run}.json'
        text = path.read_text()
        for secret in ['SECRET_SENTINEL', 'ARGV_SENTINEL', 'TEST_KEY', 'Work on', 'Ralph loop', 'Iteration:', 'OK']:
            assert secret not in text, (secret, text)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        return json.loads(text)

    def run_id(self, err):
        return err.split('ah: ralph run ', 1)[1].split()[0]


def header_of(prompt):
    head, task = prompt['text'].split('--- Task ---\n\n', 1)
    return head, task


# Bounded run: every iteration is a fresh single run (own runtime HOME and
# session) with the fixed header before the unchanged snapshot; the agent's
# edit to TASK.md does not reach later iterations; exhausted exits 1.
f = Fixture('EDIT-TASK Work on the task; keep progress in progress.md.\n')
out, err, prompts = f.ah('run', str(f.task), '--max-iterations', '3', expect=1)
run = f.run_id(err)
assert len(prompts) == 3 and out == 'OK\nOK\nOK\n', (prompts, out)
assert f.task.read_text() == 'Edited by the agent.\n'
homes = [p['home'] for p in prompts]
assert len(set(homes)) == 3 and all(not Path(h).exists() for h in homes), homes
for number, prompt in enumerate(prompts, 1):
    head, task = header_of(prompt)
    assert task == 'EDIT-TASK Work on the task; keep progress in progress.md.\n', task
    assert head.startswith('[agent-harness Ralph loop]\n') and f'Iteration: {number} of at most 3.\n' in head, head
    assert 'Completion check: test.\n' in head and 'AH-RALPH-COMPLETE' in head
    previous = ('none (first iteration of this run)' if number == 1 else
                'agent outcome succeeded; completion claimed: no; check status: not run')
    assert f'Previous iteration: {previous}.\n' in head, head
    assert 'OK' not in head and str(f.project) not in head
assert 'exhausted: reached 3 iterations without completion' in err, err
assert "completes only when a claim's check passes" in err, err
assert f.checks() == [], 'the check runs only after a claim'
r = f.record(run)
assert r['v'] == 1 and r['run'] == run and r['status'] == 'exhausted' and r['max_iterations'] == 3, r
assert (r['project'], r['prompt'], r['config']) == (str(f.project), str(f.task), str(f.project / 'ah.json'))
assert [(i['number'], i['reason'], i['status']) for i in r['iterations']] == [
    (1, 'initial', 'succeeded'), (2, 'continue', 'succeeded'), (3, 'continue', 'succeeded')], r['iterations']
assert len(r['invocations']) == 1 and r['invocations'][0]['reason'] == 'run'
assert r['invocations'][0]['max_runtime_secs'] == 3600
assert len({i['prompt_sha256'] for i in r['iterations']}) == 1
assert len({i['input_sha256'] for i in r['iterations']}) == 3
i = r['iterations'][0]
assert (i['route'], i['model'], i['permissions'], i['timeout_secs']) == ('local-only', 'ah-litellm/fixture', 'deny', 15), i
assert i['check']['name'] == 'test' and i['check']['program'] == str(f.tools / 'checker') and len(i['check']['argv_sha256']) == 64
assert (i['agent_outcome'], i['exit'], i['claim'], i['verification']) == ('succeeded', 0, False, None), i
assert i['backends'] == [dict(attempt=1, launched=True, prompt_submitted=True, backend_stop='end_turn',
                              cleanup_confirmed=True, grants=0, tool_events=0,
                              usage=dict(source=None, context_used_tokens=None, context_capacity_tokens=None,
                                         turn_tokens=None, session_cost=None))], i['backends']
for d in ['agent-harness', 'agent-harness/ralph', 'agent-harness/locks']:
    assert stat.S_IMODE((f.state / d).stat().st_mode) == 0o700, d
assert not (f.state / 'agent-harness/sequences').exists()
out, _, _ = f.ah('show', expect=0)
assert out.startswith(f'{run} exhausted; 3/3 iterations'), out
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: exhausted; 3/3 iterations' in out and 'invocation 1 run: started' in out, out
assert 'iteration 2 continue: succeeded; exit 0; agent outcome succeeded; claim no; verification none; prompt submitted yes' in out, out
assert 'usage: cost unknown' in out, out
assert f'next: ah ralph resume {run} --verify test --max-iterations N, with N greater than 3 (at most 100)' in out, out
assert 'EDIT-TASK' not in out
# Resume: the reached bound needs a larger --max-iterations; the prompt file
# is re-read and a changed prompt is reported, not refused.
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'pass --max-iterations greater than its counted iterations' in err, err
_, err, prompts = f.ah('resume', run, '--max-iterations', '3', expect=2)
assert prompts == [] and '--max-iterations must be greater' in err, err
_, err, prompts = f.ah('resume', run, '--verify', 'other', '--max-iterations', '4', expect=2, verify=False)
assert prompts == [] and 'was gated by check "test"; resume requires --verify test' in err, err
f.task.write_text('Work on the task, steered.\n')
out, err, prompts = f.ah('resume', run, '--max-iterations', '4', expect=1)
assert len(prompts) == 1 and out == 'OK\n', (prompts, out)
head, task = header_of(prompts[0])
assert task == 'Work on the task, steered.\n' and 'Iteration: 4 of at most 4.\n' in head, head
assert 'Previous iteration: agent outcome succeeded; completion claimed: no; check status: not run.\n' in head
assert 'ralph iteration 4 (resume) changed since iteration 3: prompt sha256' in err, err
assert 'exhausted: reached 4 iterations without completion' in err, err
r = f.record(run)
assert r['max_iterations'] == 4 and r['status'] == 'exhausted' and r['iterations'][3]['reason'] == 'resume', r
assert [v['reason'] for v in r['invocations']] == ['run', 'resume'], r['invocations']
assert r['iterations'][3]['prompt_sha256'] != r['iterations'][2]['prompt_sha256']

# Completion: a claim whose check passes completes the run (exit 0) at that
# iteration; the check runs once, after the claim.
f = Fixture('CLAIM the task.\n')
out, err, prompts = f.ah('run', str(f.task), '--max-iterations', '3', expect=0)
run = f.run_id(err)
assert len(prompts) == 1 and out == 'Done.\nAH-RALPH-COMPLETE\n', out
assert 'completed at iteration 1: claim verified by a passing check' in err, err
assert f.checks() == ['ARGV_SENTINEL'], f.checks()
r = f.record(run)
i = r['iterations'][0]
assert r['status'] == 'completed' and (i['status'], i['exit'], i['claim'], i['agent_outcome']) == ('succeeded', 0, True, 'succeeded'), r
assert (i['verification']['check'], i['verification']['status'], i['verification']['exit_code']) == ('test', 'passed', 0), i
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: completed' in out and 'claim yes; verification test passed (exit 0)' in out, out
assert 'next: complete; nothing to resume' in out, out
_, err, prompts = f.ah('resume', run, expect=0)
assert prompts == [] and f'run {run} is already completed; nothing launched' in err, err
assert f.checks() == ['ARGV_SENTINEL']

# A rejected claim (check failed) continues: the next iteration is the bounded
# repair, told the claim and check status; the repaired claim completes.
f = Fixture('REPAIR the task.\n', check_exit=1)
out, err, prompts = f.ah('run', str(f.task), expect=0)
run = f.run_id(err)
assert len(prompts) == 2 and f.checks() == ['ARGV_SENTINEL'] * 2, (prompts, f.checks())
assert 'claim rejected at iteration 1: check failed; the next iteration is the bounded repair' in err, err
head, _ = header_of(prompts[1])
assert 'Previous iteration: agent outcome succeeded; completion claimed: yes; check status: failed.\n' in head, head
r = f.record(run)
assert r['status'] == 'completed' and [(i['status'], i['exit'], i['claim'], i['verification']['status'])
                                       for i in r['iterations']] == [
    ('failed', 1, True, 'failed'), ('succeeded', 0, True, 'passed')], r['iterations']
assert r['iterations'][0]['agent_outcome'] == 'succeeded'

# Rejected claims that never pass end at the bound (exhausted, exit 1);
# a timed-out check is also a rejected claim.
f = Fixture('CLAIM the task.\n', check_exit=1)
_, err, prompts = f.ah('run', str(f.task), '--max-iterations', '2', expect=1)
assert len(prompts) == 2 and f.checks() == ['ARGV_SENTINEL'] * 2 and 'exhausted: reached 2' in err, err
f = Fixture('CLAIM the task.\n', check_timeout=1)
(f.tools / 'check-hang').touch()
_, err, prompts = f.ah('run', str(f.task), '--max-iterations', '2', expect=1)
run = f.run_id(err)
r = f.record(run)
assert len(prompts) == 2 and r['status'] == 'exhausted', err
assert [i['verification']['status'] for i in r['iterations']] == ['timed_out'] * 2, r['iterations']

# False and stale signals: the marker mentioned mid-response is no claim; a
# claim never carries over; a DONE file and a check that would now pass do
# not complete without a claim. The check runs only after the one claim.
f = Fixture('MENTION the marker.\n')
out, err, prompts = f.ah('run', str(f.task), '--max-iterations', '2', expect=1)
run = f.run_id(err)
assert len(prompts) == 2 and f.checks() == [] and 'completion claimed: no; check: not run' in err, err
assert [i['claim'] for i in f.record(run)['iterations']] == [False, False]
f = Fixture('CLAIM-ONCE then write DONE.\n', check_exit=1)
_, err, prompts = f.ah('run', str(f.task), '--max-iterations', '3', expect=1)
run = f.run_id(err)
assert (f.project / 'DONE').exists() and (f.project / 'fixed').exists()
assert len(prompts) == 3 and f.checks() == ['ARGV_SENTINEL'], f.checks()
head, _ = header_of(prompts[2])
assert 'completion claimed: no; check status: not run' in head, head
r = f.record(run)
assert r['status'] == 'exhausted' and [i['claim'] for i in r['iterations']] == [True, False, False], r

# A check that cannot run (error) stops the run (exit 1); bare resume needs a
# choice, and --retry/--accept together reject.
f = Fixture('RMCHECK then claim.\n')
_, err, prompts = f.ah('run', str(f.task), expect=1)
run = f.run_id(err)
r = f.record(run)
assert len(prompts) == 1 and r['status'] == 'stopped' and r['iterations'][0]['verification']['status'] == 'error', r
assert 'stopped at iteration 1 (outcome failed; check error)' in err, err
out, _, _ = f.ah('show', run, expect=0)
assert f'next: its last iteration may have had effects; inspect the project, then ah ralph resume {run} --verify test --retry or --accept' in out, out
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'pass --retry or --accept' in err, err
_, err, prompts = f.ah('resume', run, '--retry', '--accept', expect=2)
assert prompts == [] and 'at most one of --retry or --accept' in err, err

# Cancellation while the check runs stops the run (exit 3, check cancelled).
f = Fixture('CLAIM the task.\n')
(f.tools / 'check-hang').touch()
proc = f.start('ralph', 'run', str(f.task))
f.wait_checking()
proc.send_signal(signal.SIGINT)
_, err = proc.communicate(timeout=60)
assert proc.returncode == 3, (proc.returncode, err)
r = f.record(f.runs()[0])
assert r['status'] == 'stopped' and r['iterations'][0]['verification']['status'] == 'cancelled', r

# An iteration that does not succeed stops the run before the next launch;
# its response is never inspected for a claim.
f = Fixture('FAIL the task.\n')
_, err, prompts = f.ah('run', str(f.task), expect=1)
run = f.run_id(err)
assert len(prompts) == 1 and 'stopped at iteration 1 (outcome failed; check not run)' in err, err
r = f.record(run)
assert r['status'] == 'stopped' and len(r['iterations']) == 1, r
assert (r['iterations'][0]['status'], r['iterations'][0]['claim']) == ('failed', None), r['iterations'][0]
out, _, _ = f.ah('show', run, expect=0)
assert 'claim none' in out and f'run {run}: stopped' in out, out
assert '--retry or --accept' in out, out
# A submitted failure needs a choice. --accept runs no agent turn: a failing
# check keeps the run stopped (exit 1); a passing one completes it with that
# iteration accepted, not counted against the bound.
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'pass --retry or --accept' in err, err
(f.tools / 'check-exit').write_text('1')
_, err, prompts = f.ah('resume', run, '--accept', expect=1)
assert prompts == [] and f.checks() == ['ARGV_SENTINEL'], err
r = f.record(run)
assert r['status'] == 'stopped' and (r['iterations'][1]['reason'], r['iterations'][1]['status']) == ('accept', 'failed'), r
(f.tools / 'check-exit').write_text('0')
_, err, prompts = f.ah('resume', run, '--accept', expect=0)
assert prompts == [] and 'completed at iteration 3: accepted by the operator after a passing check' in err, err
r = f.record(run)
a = r['iterations'][2]
assert r['status'] == 'completed' and (a['reason'], a['status'], a['agent_outcome'], a['claim'], a['backends']) == (
    'accept', 'accepted', None, None, []), a
assert a['verification']['status'] == 'passed' and a['verification']['agent_outcome'] is None, a
assert [v['reason'] for v in r['invocations']] == ['run', 'accept', 'accept'] and r['max_iterations'] == 10
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: completed; 1/10 iterations' in out and 'iteration 3 accept: accepted' in out, out
# --retry launches a new agent iteration after a submitted failure.
f = Fixture('FAIL the task.\n')
_, err, _ = f.ah('run', str(f.task), expect=1)
run = f.run_id(err)
f.task.write_text('Work.\n')
_, err, prompts = f.ah('resume', run, '--retry', '--max-iterations', '2', expect=1)
r = f.record(run)
assert len(prompts) == 1 and [(i['reason'], i['status']) for i in r['iterations']] == [
    ('initial', 'failed'), ('retry', 'succeeded')], r['iterations']
assert r['status'] == 'exhausted' and r['invocations'][1]['reason'] == 'retry', r

# A submitted failure at the iteration bound: show names both paths, since
# --retry needs a larger bound and --accept does not.
f = Fixture('FAIL the task.\n')
_, err, _ = f.ah('run', str(f.task), '--max-iterations', '1', expect=1)
run = f.run_id(err)
out, _, _ = f.ah('show', run, expect=0)
assert (f'then ah ralph resume {run} --verify test --retry --max-iterations N (N greater than 1, at most 100) '
        f'or ah ralph resume {run} --verify test --accept (needs no larger bound)') in out, out
_, err, prompts = f.ah('resume', run, '--retry', expect=2)
assert prompts == [] and 'pass --max-iterations greater' in err, err

# Wall-time bound: each iteration's agent deadline is capped by the time left;
# the run ends exhausted at an iteration boundary (exit 1).
f = Fixture()
_, err, prompts = f.ah('run', str(f.task), '--max-iterations', '100', '--max-runtime-secs', '2', expect=1)
run = f.run_id(err)
r = f.record(run)
assert 'wall-time bound' in err and r['status'] == 'exhausted', err
assert 1 <= len(prompts) < 100 and r['invocations'][0]['max_runtime_secs'] == 2
assert all(i['timeout_secs'] <= 2 for i in r['iterations']), r['iterations']
# Exhausted only by wall time: bare resume continues under the recorded
# iteration bound, with this invocation's own wall bound.
counted = len(r['iterations'])
_, err, prompts = f.ah('resume', run, '--max-runtime-secs', '2', expect=1)
r = f.record(run)
assert len(prompts) >= 1 and r['iterations'][counted]['reason'] == 'resume', r['iterations']
assert r['max_iterations'] == 100 and r['invocations'][1] == dict(started=r['invocations'][1]['started'],
                                                                  reason='resume', max_runtime_secs=2), r

# Crash window: SIGKILL during an iteration leaves it `active`; show reports
# the run and iteration interrupted with submission unknown.
f = Fixture('SLEEP\n')
proc = f.start('ralph', 'run', str(f.task))
f.wait_sleeping()
os.kill(proc.pid, signal.SIGKILL)
_, err = proc.communicate(timeout=30)
run = f.run_id(err)
r = f.record(run)
assert r['status'] == 'active' and r['iterations'][0]['status'] == 'active', r
out, _, _ = f.ah('show', expect=0)
assert f'{run} interrupted; 1/10 iterations' in out, out
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: interrupted' in out and 'iteration 1 initial: interrupted' in out, out
assert 'prompt submitted unknown' in out, out
# A new run lists it and starts afresh at iteration 1.
f.task.write_text('Work.\n')
_, err, _ = f.ah('run', str(f.task), '--max-iterations', '1', expect=1)
assert f'unfinished run {run} for this project (interrupted; 1 iterations); this run starts at iteration 1; continue that one with ah ralph resume {run}' in err, err
# The interrupted iteration is uncertain: bare resume refuses; --retry records
# it interrupted and launches the next iteration.
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'pass --retry or --accept' in err, err
_, err, prompts = f.ah('resume', run, '--retry', '--max-iterations', '2', expect=1)
head, task = header_of(prompts[0])
assert task == 'Work.\n' and 'Previous iteration: agent outcome interrupted; completion claimed: not inspected; check status: not run.\n' in head, head
r = f.record(run)
assert [(i['reason'], i['status']) for i in r['iterations']] == [('initial', 'interrupted'), ('retry', 'succeeded')], r

# Shared lock and cancellation: a running loop refuses another Ralph run and
# a sequence before launch; show reports it active; SIGINT stops it (exit 3).
f = Fixture('SLEEP\n')
(f.project / 'prompts').mkdir()
(f.project / 'prompts/1-a.md').write_text('One.\n')
proc = f.start('ralph', 'run', str(f.task))
f.wait_sleeping()
_, err, prompts = f.ah('run', str(f.task), expect=2)
assert prompts == [] and "another sequence or Ralph run holds this project's lock" in err, err
_, err, prompts = f.ah('run', str(f.project / 'prompts'), expect=2, command='sequence', verify=False)
assert prompts == [] and "another sequence or Ralph run holds this project's lock" in err, err
run = f.runs()[0]
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: active' in out and 'next: running' in out, out
proc.send_signal(signal.SIGINT)
_, err = proc.communicate(timeout=60)
assert proc.returncode == 3, (proc.returncode, err)
r = f.record(run)
assert r['status'] == 'stopped' and r['iterations'][0]['status'] == 'cancelled', r
# A running sequence holds the same lock against Ralph.
(f.project / 'prompts/1-a.md').write_text('SLEEP\n')
proc = f.start('sequence', 'run', str(f.project / 'prompts'), verify=False)
f.wait_sleeping()
_, err, prompts = f.ah('run', str(f.task), expect=2)
assert prompts == [] and "another sequence or Ralph run holds this project's lock" in err, err
proc.send_signal(signal.SIGINT)
proc.communicate(timeout=60)

# Preview reads FILE, resolves agent, route and check, and prints the bounds
# and the iteration-1 header without state, lock, launch or write.
f = Fixture()
out, _, prompts = f.ah('run', str(f.task), '--preview', '--max-iterations', '4', expect=0)
assert prompts == [] and not f.state.exists(), out
assert 'ralph preview: nothing launched' in out and 'bounds: at most 4 iterations per run; 3600 seconds' in out, out
assert 'check: "test"' in out and 'iteration 1 header:\n[agent-harness Ralph loop]\nIteration: 1 of at most 4.' in out, out
assert 'Work on the task' not in out

# Argument rules; nothing launches and no state is written.
f = Fixture()
for args, reason in [
    (('run', str(f.task)), 'requires --verify'),
    (('run', str(f.task), '--prompt-file', str(f.task)), 'only from FILE'),
    (('run', str(f.task), '--output', 'jsonl'), '--output jsonl is unsupported for ralph'),
    (('run', str(f.task), '--max-iterations', '0'), '--max-iterations must be 1–100'),
    (('run', str(f.task), '--max-runtime-secs', '86401'), '--max-runtime-secs must be 1–86400'),
    (('run', str(f.project / 'absent.md')), 'cannot open input file'),
    (('resume', 'r20261105T140000Z-1a2b3c4d'), 'no Ralph record with that run ID'),
    (('resume', 's20261105T140000Z-1a2b3c4d'), 'run ID must be rYYYYMMDD'),
    (('resume', 'r20261105T140000Z-1a2b3c4d', '--project', '.'), 'from the record'),
    (('show', 's20261105T140000Z-1a2b3c4d'), 'run ID must be rYYYYMMDD'),
    (('show', '--output', 'jsonl'), '--output jsonl is unsupported for ralph'),
    (('show', 'r20261105T140000Z-1a2b3c4d', '--project', '.'), 'takes no --project'),
]:
    _, err, prompts = f.ah(*args, expect=2, verify=(reason != 'requires --verify'))
    assert prompts == [] and reason in err, (args, err)
f.task.write_text('/init\n')
_, err, prompts = f.ah('run', str(f.task), expect=2)
assert prompts == [] and not f.state.exists(), err
f.task.write_text('   \n')
_, err, _ = f.ah('run', str(f.task), expect=2)
assert 'prompt file must not be empty' in err
_, err, _ = f.ah('run', str(f.task), expect=2, verify=False)
assert 'requires --verify' in err
out, _, _ = f.ah('show', expect=0)
assert out == 'no Ralph runs recorded for this project\n', out
assert not f.state.exists()

print('ralph: all cases passed')
