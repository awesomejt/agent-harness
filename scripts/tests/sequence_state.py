#!/usr/bin/env python3
"""P5.3 durable sequence records, lock, show and resume (D044) against fake OpenCode 2.2.5.

Covers the record's content and privacy, crash and write-failure windows,
competing writers, cancellation, changed inputs and schema, explicit
--retry/--accept choices and gate handling, and read-only inspection. No model
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

# Fake check: logs its name, then acts on MODE. `lockdown` makes the record
# directory read-only before passing, so the step result write fails.
CHECKER = '''#!/usr/bin/env python3
import os, sys
name, mode, out = sys.argv[1], sys.argv[2], sys.argv[3]
with open(os.path.join(out, 'checks.log'), 'a') as f:
    f.write(name + '\\n')
if mode == 'lockdown':
    os.chmod(os.path.join(os.environ['XDG_STATE_HOME'], 'agent-harness', 'sequences'), 0o500)
sys.exit(3 if mode == 'fail' else 0)
'''


class Fixture:
    def __init__(self, steps, checks=None):
        self.dirs = [tempfile.TemporaryDirectory(prefix=f'ah-state-{n}-') for n in ('project', 'tools', 'home')]
        self.project, self.tools, self.home = (Path(d.name).resolve() for d in self.dirs)
        self.state = self.home / 'state'
        (self.project / 'opencode').symlink_to(FAKE)
        self.case('sequence')
        self.folder = self.project / 'prompts'
        self.folder.mkdir()
        for name, text in steps.items():
            (self.folder / name).write_text(text)
        checker = self.tools / 'checker'
        checker.write_text(CHECKER)
        checker.chmod(0o755)
        self.configure(checks or dict(test=['pass']))

    def case(self, name):
        (self.project / 'case').write_text(name)

    def configure(self, checks):
        config = dict(version=1, mode='local-only', model='fixture',
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'),
                      checks={name: dict(argv=[str(self.tools / 'checker'), name, *mode, str(self.tools),
                                               'ARGV_SENTINEL'])
                              for name, mode in checks.items()})
        (self.project / 'ah.json').write_text(json.dumps(config))

    def env(self, **extra):
        env = {**os.environ, 'PATH': f'{self.project}:{self.tools}:' + os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'XDG_STATE_HOME': str(self.state)}
        env.update(extra)
        return {k: v for k, v in env.items() if v is not None}

    def start(self, *args, env=None):
        argv = [str(BINARY), 'sequence', *args]
        if args[0] == 'run':
            argv += ['--project', str(self.project)]
        if args[0] in ('run', 'resume'):
            argv += ['--timeout-secs', '15']
        return subprocess.Popen(argv, env=env or self.env(), cwd=self.project, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                start_new_session=True)

    def ah(self, *args, expect, env=None):
        before = len(self.prompts())
        proc = self.start(*args, env=env)
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == expect, (args, proc.returncode, out, err)
        assert 'SECRET_SENTINEL' not in out + err
        print('PASS', ' '.join(args[:2]), expect, flush=True)
        return out, err, self.prompts()[before:]

    def prompts(self):
        log = self.project / 'prompts.jsonl'
        return [json.loads(l)['text'] for l in log.read_text().splitlines()] if log.exists() else []

    def checks(self):
        log = self.tools / 'checks.log'
        return log.read_text().split() if log.exists() else []

    def wait_sleeping(self):
        until = time.monotonic() + 15
        while not (self.project / 'sleeping').exists():
            assert time.monotonic() < until, 'step never started'
            time.sleep(.02)
        (self.project / 'sleeping').unlink()

    def runs(self):
        return sorted(p.stem for p in (self.state / 'agent-harness/sequences').glob('s*.json'))

    def record(self, run):
        path = self.state / f'agent-harness/sequences/{run}.json'
        text = path.read_text()
        for secret in ['SECRET_SENTINEL', 'ARGV_SENTINEL', 'TEST_KEY', 'One.', 'Two.', 'FAIL', 'SLEEP']:
            assert secret not in text, (secret, text)
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        return json.loads(text)

    def run_id(self, err):
        return err.split('ah: sequence run ', 1)[1].split()[0]


def attempt_reasons(record, index):
    return [(a['reason'], a['status']) for a in record['steps'][index]['attempts']]


# A completed run: v1 record outside the project, private modes, identities,
# per-backend summary and no prompt text, keys or argv text.
f = Fixture({'1-a.md': 'One.\n', '2-b.md': '---\nverify: test\n---\nTwo.\n'})
out, err, prompts = f.ah('run', str(f.folder), '--verify', 'test', expect=0)
run = f.run_id(err)
assert prompts == ['One.\n', 'Two.\n'] and out == 'OKOK'
r = f.record(run)
assert r['v'] == 1 and r['run'] == run and r['status'] == 'completed', r
assert r['project'] == str(f.project) and r['folder'] == str(f.folder) and r['config'] == str(f.project / 'ah.json')
assert [s['status'] for s in r['steps']] == ['succeeded', 'succeeded']
a = r['steps'][0]['attempts'][0]
assert a['reason'] == 'initial' and a['exit'] == 0 and a['agent_outcome'] == 'succeeded'
assert (a['input_sha256'], a['route'], a['model']) == (r['steps'][0]['sha256'], 'local-only', 'ah-litellm/fixture'), a
assert a['check']['name'] == 'test' and a['check']['program'] == str(f.tools / 'checker') and len(a['check']['argv_sha256']) == 64
assert a['verification']['status'] == 'passed' and a['verification']['agent_outcome'] == 'succeeded'
assert a['backends'] == [dict(attempt=1, launched=True, prompt_submitted=True, backend_stop='end_turn',
                              cleanup_confirmed=True, grants=0, tool_events=0)], a['backends']
for d in ['agent-harness', 'agent-harness/sequences', 'agent-harness/locks']:
    assert stat.S_IMODE((f.state / d).stat().st_mode) == 0o700, d
assert not any('agent-harness' in p for p in os.listdir(f.project))
out, _, _ = f.ah('show', expect=0)
assert out.startswith(f'{run} completed; 2/2 steps complete'), out
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: completed' in out and 'attempt 1 initial: succeeded; exit 0' in out and 'next: complete' in out, out
assert 'One.' not in out and 'ARGV_SENTINEL' not in out
_, err, prompts = f.ah('resume', run, expect=0)
assert prompts == [] and 'no remaining steps' in err

# A failed step whose prompt was submitted needs an explicit choice; --retry
# re-reads the folder, reports the changed input and records a new attempt.
f = Fixture({'1-a.md': 'One.\n', '2-b.md': 'FAIL\n', '3-c.md': 'Three.\n'})
_, err, prompts = f.ah('run', str(f.folder), expect=1)
run = f.run_id(err)
assert prompts == ['One.\n', 'FAIL\n']
r = f.record(run)
assert r['status'] == 'stopped' and [s['status'] for s in r['steps']] == ['succeeded', 'failed', 'pending']
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: stopped' in out and 'step 2-b.md may have had effects' in out, out
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'step 2-b.md: its last attempt may have had effects' in err, err
_, err, _ = f.ah('resume', run, '--retry', '--accept', expect=2)
assert 'at most one of --retry or --accept' in err
(f.folder / '2-b.md').write_text('Fixed two.\n')
_, err, prompts = f.ah('resume', run, '--retry', expect=0)
assert prompts == ['Fixed two.\n', 'Three.\n'], prompts
assert 'attempt 2 (retry) changed since attempt 1: input sha256' in err, err
r = f.record(run)
assert r['status'] == 'completed' and attempt_reasons(r, 1) == [('initial', 'failed'), ('retry', 'succeeded')]
assert attempt_reasons(r, 2) == [('resume', 'succeeded')]
assert r['steps'][1]['attempts'][0]['input_sha256'] != r['steps'][1]['attempts'][1]['input_sha256']

# Changed inputs: a completed step may not change; the attempted step must
# remain next; later steps may be edited, added or removed.
f = Fixture({'1-a.md': 'One.\n', '2-b.md': 'FAIL\n', '3-c.md': 'Three.\n'})
_, err, _ = f.ah('run', str(f.folder), expect=1)
run = f.run_id(err)
before = f.record(run)
(f.folder / '1-a.md').write_text('Changed one.\n')
_, err, prompts = f.ah('resume', run, '--retry', expect=2)
assert prompts == [] and 'step 1-a.md: a completed step changed' in err, err
(f.folder / '1-a.md').write_text('One.\n')
(f.folder / '2-b.md').rename(f.folder / '4-b.md')
_, err, prompts = f.ah('resume', run, '--retry', expect=2)
assert prompts == [] and 'step 2-b.md: the step with recorded attempts must remain the next step' in err, err
assert f.record(run) == before, 'refusals do not rewrite the record'
# Truncating the folder to the completed prefix does not settle it either.
(f.folder / '4-b.md').rename(f.project / 'held-b.md')
(f.folder / '3-c.md').rename(f.project / 'held-c.md')
for choice in ([], ['--retry'], ['--accept']):
    _, err, prompts = f.ah('resume', run, *choice, expect=2)
    assert prompts == [] and 'step 2-b.md: the step with recorded attempts must remain the next step' in err, err
assert f.record(run) == before
(f.project / 'held-b.md').rename(f.folder / '2-b.md')
(f.project / 'held-c.md').rename(f.folder / '3-c.md')
(f.folder / '2-b.md').write_text('Two.\n')
(f.folder / '3-c.md').unlink()
(f.folder / '5-e.md').write_text('Five.\n')
_, _, prompts = f.ah('resume', run, '--retry', expect=0)
assert prompts == ['Two.\n', 'Five.\n'], prompts
assert [s['name'] for s in f.record(run)['steps']] == ['1-a.md', '2-b.md', '5-e.md']

# Rejected before submission: resume retries it without a choice.
f = Fixture({'1-a.md': 'One.\n', '2-b.md': 'Two.\n'})
f.case('version')
_, err, prompts = f.ah('run', str(f.folder), expect=2)
run = f.run_id(err)
r = f.record(run)
assert prompts == [] and r['steps'][0]['status'] == 'rejected', r
assert r['steps'][0]['attempts'][0]['backends'][0]['prompt_submitted'] is False
f.case('sequence')
_, _, prompts = f.ah('resume', run, expect=0)
assert prompts == ['One.\n', 'Two.\n']
assert attempt_reasons(f.record(run), 0) == [('initial', 'rejected'), ('resume', 'succeeded')]

# Crash window: SIGKILL during a step leaves an `active` attempt; show
# reports it interrupted; resume needs a choice; --accept records an operator
# acceptance (no agent turn, never verified) and continues.
f = Fixture({'1-a.md': 'SLEEP\n', '2-b.md': 'Two.\n'})
proc = f.start('run', str(f.folder))
f.wait_sleeping()
os.kill(proc.pid, signal.SIGKILL)
_, err = proc.communicate(timeout=30)
run = f.run_id(err)
r = f.record(run)
assert r['status'] == 'active' and r['steps'][0]['attempts'][0]['status'] == 'active', r
out, _, _ = f.ah('show', expect=0)
assert f'{run} interrupted; 0/2 steps complete' in out, out
out, _, _ = f.ah('show', run, expect=0)
assert 'step 1 1-a.md: interrupted' in out and 'prompt submitted unknown' in out and 'may have had effects' in out, out
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'may have had effects' in err
_, err, prompts = f.ah('resume', run, '--accept', expect=0)
assert prompts == ['Two.\n'] and 'accepted by the operator' in err, err
r = f.record(run)
assert attempt_reasons(r, 0) == [('initial', 'interrupted'), ('accept', 'accepted')], r
accept = r['steps'][0]['attempts'][1]
assert accept['agent_outcome'] is None and accept['verification'] is None and accept['backends'] == []

# Competing writers and cancellation: the lock refuses a second run or a
# resume before launch; show reports the holder active; SIGINT stops it.
f = Fixture({'1-a.md': 'SLEEP\n', '2-b.md': 'Two.\n'})
proc = f.start('run', str(f.folder))
f.wait_sleeping()
_, err, prompts = f.ah('run', str(f.folder), expect=2)
assert prompts == [] and "another sequence holds this project's lock" in err, err
runs = f.runs()
assert len(runs) == 1, runs
run = runs[0]
_, err, prompts = f.ah('resume', run, '--retry', expect=2)
assert prompts == [] and "another sequence holds this project's lock" in err, err
out, _, _ = f.ah('show', run, expect=0)
assert f'run {run}: active' in out and 'next: running' in out, out
proc.send_signal(signal.SIGINT)
proc.communicate(timeout=60)
assert proc.returncode == 3
r = f.record(run)
assert r['status'] == 'stopped' and attempt_reasons(r, 0) == [('initial', 'cancelled')], r
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'may have had effects' in err
# A new run starts at step 1 and lists the unfinished one.
(f.folder / '1-a.md').write_text('One.\n')
_, err, prompts = f.ah('run', str(f.folder), expect=0)
assert prompts == ['One.\n', 'Two.\n'] and f'unfinished run {run} for this project (stopped; 0/2' in err, err

# Gates on --accept: the recorded check stays required; a failed accept check
# keeps the run stopped (exit 1); a passing one completes the step `accepted`.
f = Fixture({'1-a.md': 'One.\n', '2-b.md': 'Two.\n'}, checks=dict(test=['fail'], build=['pass']))
_, err, _ = f.ah('run', str(f.folder), '--verify', 'test', expect=1)
run = f.run_id(err)
assert f.record(run)['steps'][0]['attempts'][0]['verification']['status'] == 'failed'
_, err, _ = f.ah('resume', run, '--accept', expect=2)
assert 'gated by check "test"; --accept requires --verify and the same check' in err, err
_, err, _ = f.ah('resume', run, '--accept', '--verify', 'build', expect=2)
assert 'gated by check "test"' in err
_, err, prompts = f.ah('resume', run, '--accept', '--verify', 'test', expect=1)
assert prompts == [] and f.checks() == ['test', 'test'], f.checks()
r = f.record(run)
assert r['status'] == 'stopped' and attempt_reasons(r, 0) == [('initial', 'failed'), ('accept', 'failed')]
_, err, _ = f.ah('resume', run, expect=2)
assert 'may have had effects' in err
f.configure(dict(test=['pass'], build=['pass']))
_, err, prompts = f.ah('resume', run, '--accept', '--verify', 'test', expect=0)
assert prompts == ['Two.\n'] and 'changed since attempt 2: check argv sha256' in err, err
r = f.record(run)
accept = r['steps'][0]['attempts'][2]
assert accept['status'] == 'accepted' and accept['agent_outcome'] is None
assert accept['verification']['status'] == 'passed' and accept['verification']['agent_outcome'] is None
assert r['steps'][1]['attempts'][0]['verification']['status'] == 'passed'

# A failed gate on an agent success is not settled by removing its step.
f = Fixture({'1-a.md': 'One.\n', '2-b.md': '---\nverify: build\n---\nTwo.\n'}, checks=dict(test=['pass'], build=['fail']))
_, err, _ = f.ah('run', str(f.folder), '--verify', 'test', expect=1)
run = f.run_id(err)
before = f.record(run)
assert before['steps'][1]['attempts'][0]['verification']['status'] == 'failed', before
(f.folder / '2-b.md').unlink()
_, err, prompts = f.ah('resume', run, expect=2)
assert prompts == [] and 'step 2-b.md: the step with recorded attempts must remain the next step' in err, err
assert f.record(run) == before and f.checks() == ['test', 'build']

# Reused harness-owned directories and lock files must be private; a
# permissive one is refused (exit 2) before any launch and left as found.
f = Fixture({'1-a.md': 'One.\n'})
_, err, _ = f.ah('run', str(f.folder), expect=0)
run = f.run_id(err)
owned = f.state / 'agent-harness'
for path, loose in [(owned, 0o777), (owned / 'sequences', 0o755), (owned / 'locks', 0o770)]:
    path.chmod(loose)
    # A completed run's resume and show never reach locks/.
    for args in (('run', str(f.folder)), ('resume', run), ('show', run)):
        if args[0] != 'run' and path.name == 'locks':
            continue
        _, err, prompts = f.ah(*args, expect=2)
        assert prompts == [] and 'must be owned by the current user and private' in err, (args, err)
    assert stat.S_IMODE(path.stat().st_mode) == loose
    path.chmod(0o700)
lock = next((owned / 'locks').iterdir())
lock.chmod(0o666)
_, err, prompts = f.ah('run', str(f.folder), expect=2)
assert prompts == [] and 'must be owned by the current user and private' in err, err
assert stat.S_IMODE(lock.stat().st_mode) == 0o666 and len(f.runs()) == 1
lock.chmod(0o600)
f.ah('run', str(f.folder), expect=0)

# Write failures: before launch exits 1 with nothing launched; after an
# attempt exits 4 and stops later steps; the record then shows the uncertainty.
f = Fixture({'1-a.md': 'One.\n'})
(f.state / 'agent-harness').mkdir(parents=True, mode=0o700)
(f.state / 'agent-harness/sequences').mkdir(mode=0o700)
(f.state / 'agent-harness/sequences').chmod(0o500)
_, err, prompts = f.ah('run', str(f.folder), expect=1)
assert prompts == [] and 'cannot stage sequence record; nothing launched' in err, err
(f.state / 'agent-harness/sequences').chmod(0o700)
f = Fixture({'1-a.md': 'One.\n', '2-b.md': 'Two.\n'}, checks=dict(test=['lockdown']))
_, err, prompts = f.ah('run', str(f.folder), '--verify', 'test', expect=4)
(f.state / 'agent-harness/sequences').chmod(0o700)
run = f.run_id(err)
assert prompts == ['One.\n'] and 'durable record may not reflect this attempt' in err, err
out, _, _ = f.ah('show', run, expect=0)
assert 'step 1 1-a.md: interrupted' in out, out
_, err, _ = f.ah('resume', run, expect=2)
assert 'may have had effects' in err

# Schema and record validation refuse without rewriting.
f = Fixture({'1-a.md': 'One.\n'})
_, err, _ = f.ah('run', str(f.folder), expect=0)
run = f.run_id(err)
path = f.state / f'agent-harness/sequences/{run}.json'
original = json.loads(path.read_text())
for mutate, reason in [
    (lambda r: r.update(v=2), 'schema version is unsupported'),
    (lambda r: r.update(extra=1), 'invalid for schema v1'),
    (lambda r: r['steps'][0].update(status='bogus'), 'invalid for schema v1'),
    (lambda r: r.update(run='s20000101T000000Z-00000000'), 'invalid for schema v1'),
]:
    changed = json.loads(json.dumps(original))
    mutate(changed)
    text = json.dumps(changed)
    path.write_text(text)
    for args in [('show', run), ('resume', run)]:
        _, err, _ = f.ah(*args, expect=2)
        assert reason in err and 'not rewritten' in err, (reason, err)
    assert path.read_text() == text
    out, _, _ = f.ah('show', expect=0)
    assert f'{run} unreadable (project unknown)' in out, out
path.write_text('{not json')
_, err, _ = f.ah('show', run, expect=2)
assert 'unparsable' in err

# State location rules and argument validation; nothing launches.
f = Fixture({'1-a.md': 'One.\n'})
for env, reason in [
    (f.env(XDG_STATE_HOME=str(f.project / 'state')), 'must lie outside the project'),
    (f.env(XDG_STATE_HOME='relative', HOME='relative'), 'needs an absolute XDG_STATE_HOME or HOME'),
    (f.env(XDG_STATE_HOME=None, HOME=None), 'needs an absolute XDG_STATE_HOME or HOME'),
]:
    _, err, prompts = f.ah('run', str(f.folder), env=env, expect=2)
    assert prompts == [] and reason in err, (reason, err)
assert not (f.project / 'state').exists()
_, err, _ = f.ah('run', str(f.folder), env=f.env(XDG_STATE_HOME=None, HOME=str(f.home)), expect=0)
assert (f.home / '.local/state/agent-harness/sequences' / f'{f.run_id(err)}.json').exists()
f.state.mkdir()
(f.state / 'agent-harness').symlink_to(f.home)
_, err, prompts = f.ah('run', str(f.folder), expect=2)
assert prompts == [] and 'not symlinks' in err, err
_, err, _ = f.ah('show', expect=2)
assert 'not symlinks' in err, err
(f.state / 'agent-harness').unlink()
for args, reason in [
    (('show', '../../etc/passwd'), 'run ID must be'),
    (('resume', 's2026'), 'run ID must be'),
    (('resume', 's20261103T140000Z-1a2b3c4d', '--project', '.'), '--project, --config and --preview reject'),
    (('resume', 's20261103T140000Z-1a2b3c4d', '--output', 'jsonl'), '--output jsonl is unsupported'),
    (('show', '--output', 'jsonl'), '--output jsonl is unsupported'),
    (('show', 's20261103T140000Z-1a2b3c4d', '--project', '.'), 'takes no --project'),
    (('resume', 's20261103T140000Z-1a2b3c4d', '--retry', '--retry'), 'at most one of --retry or --accept'),
]:
    _, err, _ = f.ah(*args, expect=2)
    assert reason in err, (args, err)
out, _, _ = f.ah('show', '--project', str(f.home), expect=0)
assert out == 'no sequence runs recorded for this project\n', out

print('sequence_state: all cases passed')
