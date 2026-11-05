#!/usr/bin/env python3
"""P6.2 Ralph iterations, records, lock and show (D045) against fake OpenCode 2.2.5.

Covers fresh runtime context and private state per iteration, the fixed
header and prompt snapshot, durable records and their privacy, both bounds,
stop on a non-success iteration, interrupted and cancelled iterations, the
lock shared with sequences, read-only show/preview and argument rules.
Completion verification is P6.3: the check never runs here. No model
traffic. Build target/debug/ah first.
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
CHECKER = '#!/bin/sh\necho "$1" >> "$2/checks.log"\nexit 0\n'


class Fixture:
    def __init__(self, task='Work on the task.\n'):
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
        config = dict(version=1, mode='local-only', model='fixture',
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'),
                      checks=dict(test=dict(argv=[str(checker), 'ARGV_SENTINEL', str(self.tools)])))
        (self.project / 'ah.json').write_text(json.dumps(config))

    def env(self, **extra):
        env = {**os.environ, 'PATH': f'{self.project}:{self.tools}:' + os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'XDG_STATE_HOME': str(self.state)}
        env.update(extra)
        return {k: v for k, v in env.items() if v is not None}

    def start(self, command, *args, verify=True):
        argv = [str(BINARY), command, *args]
        if args[0] == 'run':
            argv += ['--project', str(self.project), '--timeout-secs', '15']
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
assert 'completion verification is not enforced by this build' in err
assert f.checks() == [], 'the check runs only after a claim, and not before P6.3'
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
assert 'usage: cost unknown' in out and 'next: not resumable by this build' in out, out
assert 'EDIT-TASK' not in out

# A claim is recorded and reported to the next iteration, never acted on
# here: no check runs, and the run still ends at its bound.
f = Fixture('CLAIM the task.\n')
out, err, prompts = f.ah('run', str(f.task), '--max-iterations', '2', expect=1)
run = f.run_id(err)
assert out == 'Done.\nAH-RALPH-COMPLETE\n' * 2, out
assert 'completion claimed: yes (not verified by this build)' in err, err
head, _ = header_of(prompts[1])
assert 'Previous iteration: agent outcome succeeded; completion claimed: yes; check status: not run.\n' in head, head
r = f.record(run)
assert [i['claim'] for i in r['iterations']] == [True, True] and r['status'] == 'exhausted'
assert f.checks() == []

# An iteration that does not succeed stops the run before the next launch;
# its response is never inspected for a claim.
f = Fixture('FAIL the task.\n')
_, err, prompts = f.ah('run', str(f.task), expect=1)
run = f.run_id(err)
assert len(prompts) == 1 and 'stopped at iteration 1 (outcome failed)' in err, err
r = f.record(run)
assert r['status'] == 'stopped' and len(r['iterations']) == 1, r
assert (r['iterations'][0]['status'], r['iterations'][0]['claim']) == ('failed', None), r['iterations'][0]
out, _, _ = f.ah('show', run, expect=0)
assert 'claim none' in out and f'run {run}: stopped' in out, out

# Wall-time bound: each iteration's agent deadline is capped by the time left;
# the run ends exhausted at an iteration boundary (exit 1).
f = Fixture()
_, err, prompts = f.ah('run', str(f.task), '--max-iterations', '100', '--max-runtime-secs', '2', expect=1)
run = f.run_id(err)
r = f.record(run)
assert 'wall-time bound' in err and r['status'] == 'exhausted', err
assert 1 <= len(prompts) < 100 and r['invocations'][0]['max_runtime_secs'] == 2
assert all(i['timeout_secs'] <= 2 for i in r['iterations']), r['iterations']

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
assert f'unfinished run {run} for this project (interrupted; 1 iterations); this run starts at iteration 1' in err, err

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
    (('resume', 'r20261105T140000Z-1a2b3c4d'), 'ralph resume is not supported by this build'),
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
