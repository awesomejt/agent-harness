#!/usr/bin/env python3
"""P5.2 ordered prompt execution (D044) against fake OpenCode 2.2.5 and fake checks; no model traffic.

Covers numeric order, fresh per-step runtimes, the in-memory snapshot, per-step
agent and check metadata, stopping dependent steps after a failed step or gate,
signals during and between steps, and validation of every step before launch.
Build target/debug/ah first.
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
REVIEWER = (ROOT / 'agents/reviewer.md').read_text()

# Fake check: logs its name, then acts on MODE. `interrupt` signals the harness
# and passes at once, so the stop lands between steps (or as a cancelled gate).
CHECKER = '''#!/usr/bin/env python3
import os, signal, sys
name, mode, out = sys.argv[1], sys.argv[2], sys.argv[3]
with open(os.path.join(out, 'checks.log'), 'a') as f:
    f.write(name + '\\n')
if mode == 'interrupt':
    os.kill(os.getppid(), signal.SIGINT)
sys.exit(3 if mode == 'fail' else 0)
'''


def run(steps, expected, *, args=(), checks=None, extra_files=None, interrupt=False, preview=False):
    with tempfile.TemporaryDirectory(prefix='ah-sequence-project-') as p, \
         tempfile.TemporaryDirectory(prefix='ah-sequence-tools-') as t:
        project, tools = Path(p).resolve(), Path(t).resolve()
        (project / 'opencode').symlink_to(FAKE)
        (project / 'case').write_text('sequence')
        (project / 'agents').mkdir()
        (project / 'agents/reviewer.md').write_text(REVIEWER)
        (project / 'agents/thinker.md').write_text(
            REVIEWER.replace('name: reviewer', 'name: thinker').replace('\ntools:', '\neffort: high\ntools:'))
        folder = project / 'prompts'
        folder.mkdir()
        for name, text in steps.items():
            (folder / name).write_text(text)
        for name, text in (extra_files or {}).items():
            (folder / name).write_text(text)
        checker = tools / 'checker'
        checker.write_text(CHECKER)
        checker.chmod(0o755)
        if checks is None:
            checks = dict(test=['pass'], build=['pass'])
        config = dict(version=1, mode='local-only', model='fixture',
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'),
                      checks={name: dict(argv=[str(checker), name, *mode, str(tools)])
                              for name, mode in checks.items()})
        (project / 'ah.json').write_text(json.dumps(config))
        argv = [str(BINARY), 'sequence', 'run', str(folder), '--project', str(project),
                '--timeout-secs', '15', *args]
        if preview:
            argv.append('--preview')
        env = {**os.environ, 'PATH': f'{project}:{tools}:' + os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL'}
        proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        if interrupt:
            until = time.monotonic() + 15
            while not (project / 'sleeping').exists() and time.monotonic() < until:
                time.sleep(.02)
            assert (project / 'sleeping').exists(), 'step never started'
            proc.send_signal(signal.SIGINT)
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == expected, (steps, proc.returncode, err)
        assert 'SECRET_SENTINEL' not in out + err
        log = project / 'prompts.jsonl'
        prompts = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        checks_log = tools / 'checks.log'
        state = dict(prompts=prompts, texts=[p['text'] for p in prompts], out=out, err=err,
                     launched=(project / 'launched').exists(),
                     checks=checks_log.read_text().split() if checks_log.exists() else [],
                     files=sorted(os.listdir(project)))
        print('PASS', sorted(steps), expected, flush=True)
        return state


# Numeric order (2 before 10), dot entries ignored, one fresh runtime per step.
s = run({'10-last.md': 'Third.\n', '2-second.md': 'Second.\n', '1-first.md': 'First.\n'}, 0,
        extra_files={'.notes': 'ignored'})
assert s['texts'] == ['First.\n', 'Second.\n', 'Third.\n'], s['texts']
assert len({p['home'] for p in s['prompts']}) == 3, 'each step has a private runtime'
assert s['out'] == 'OKOKOK', s['out']
assert s['err'].count('outcome=Success') == 3 and 'completed all 3 steps' in s['err'], s['err']
assert 'sequence step 1/3 1-first.md sha256=' in s['err'] and 'sequence step 3/3 10-last.md' in s['err']

# Metadata is stripped from the prompt; agent applies to its step only.
s = run({'1-a.md': 'Plain.\n', '2-b.md': '---\nagent: reviewer\n---\nReview.\n', '3-c.md': 'Plain again.\n'}, 0)
assert s['texts'] == ['Plain.\n', 'Review.\n', 'Plain again.\n'], s['texts']
assert [p['agent'] for p in s['prompts']] == ['build', 'reviewer', 'build'], s['prompts']

# --agent applies to every step; agreeing metadata is accepted.
s = run({'1-a.md': 'One.\n', '2-b.md': '---\nagent: reviewer\n---\nTwo.\n'}, 0, args=['--agent', 'reviewer'])
assert [p['agent'] for p in s['prompts']] == ['reviewer', 'reviewer']

# The snapshot is in memory: step 2's agent rewrites step 3's file, which still
# runs as originally read.
s = run({'1-a.md': 'One.\n', '2-b.md': 'EDIT-LATER\n', '3-c.md': 'Original third.\n'}, 0)
assert s['texts'][2] == 'Original third.\n', s['texts']

# A failed step stops the sequence with its own exit; later steps never launch.
s = run({'1-a.md': 'One.\n', '2-b.md': 'FAIL\n', '3-c.md': 'Three.\n'}, 1)
assert s['texts'] == ['One.\n', 'FAIL\n'], s['texts']
assert 'stopped at step 2/3 2-b.md (outcome failed); 1 later steps pending and not launched' in s['err'], s['err']

# Gates: --verify gates every step; metadata substitutes another declared check.
s = run({'1-a.md': 'One.\n', '2-b.md': '---\nverify: build\n---\nTwo.\n', '3-c.md': 'Three.\n'}, 0,
        args=['--verify', 'test'])
assert s['checks'] == ['test', 'build', 'test'], s['checks']
assert s['err'].count('verification="test" "passed"') == 2 and 'verification="build" "passed"' in s['err']

# A gate that does not pass stops dependent steps, though the agent succeeded.
s = run({'1-a.md': 'One.\n', '2-b.md': 'Two.\n'}, 1, args=['--verify', 'test'], checks=dict(test=['fail']))
assert s['texts'] == ['One.\n'] and s['checks'] == ['test'], s
assert 'verification="test" "failed"' in s['err'] and 'stopped at step 1/2' in s['err']

# Without --verify nothing is gated, and no step is labeled verified.
s = run({'1-a.md': 'One.\n'}, 0)
assert s['checks'] == [] and 'verification=' not in s['err']

# A signal during a step cancels it (exit 3); later steps never launch.
s = run({'1-a.md': 'SLEEP\n', '2-b.md': 'Two.\n'}, 3, interrupt=True)
assert s['texts'] == ['SLEEP\n'], s['texts']
assert 'stopped at step 1/2 1-a.md (outcome cancelled)' in s['err'], s['err']

# A signal arriving as step 1's gate passes stops before step 2 launches (exit
# 3), whether it lands on the gate or between steps.
s = run({'1-a.md': 'One.\n', '2-b.md': 'Two.\n'}, 3, args=['--verify', 'test'],
        checks=dict(test=['interrupt']))
assert s['texts'] == ['One.\n'] and s['checks'] == ['test'], s
assert ('stopped by signal before step 2/2 2-b.md' in s['err']
        or 'stopped at step 1/2 1-a.md (outcome cancelled)' in s['err']), s['err']

# Every step validates before step 1 launches: nothing runs on any refusal.
for steps, args, reason in [
    ({}, [], 'prompt folder has no steps'),
    ({'1-a.md': 'One.\n', '01-b.md': 'Two.\n'}, [], 'two steps share a step number'),
    ({'1-a.md': 'One.\n', 'b.md': 'Two.\n'}, [], 'regular files named N-slug.md'),
    ({'1-a.md': 'One.\n', '1234567-b.md': 'Two.\n'}, [], 'regular files named N-slug.md'),
    ({'1-a.md': 'One.\n', '2-b.txt': 'Two.\n'}, [], 'regular files named N-slug.md'),
    ({'1-a.md': 'One.\n', '2-b.md': '   \n'}, [], 'step prompt must not be empty'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nmode: cloud-only\n---\nTwo.\n'}, [], 'invalid step metadata'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nagent: reviewer\nagent: reviewer\n---\nTwo.\n'}, [], 'invalid step metadata'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nagent: reviewer\n'}, [], 'step metadata is incomplete'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nagent: reviewer\n---\nTwo.\n'}, ['--agent', 'thinker'],
     'step 2-b.md: step metadata agent conflicts with --agent'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nverify: build\n---\nTwo.\n'}, [], 'step 2-b.md: step metadata verify requires --verify'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nverify: missing\n---\nTwo.\n'}, ['--verify', 'test'],
     'step 2-b.md: verification check is not defined'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nagent: absent\n---\nTwo.\n'}, [], 'step 2-b.md: agent is not defined'),
    ({'1-a.md': 'One.\n', '2-b.md': '---\nagent: thinker\n---\nTwo.\n'}, [], 'step 2-b.md: agent effort is unsupported'),
    ({'1-a.md': 'One.\n', '2-b.md': '/review\n'}, [], 'step 2-b.md: prompt starts with a runtime slash command'),
    ({'1-a.md': 'One.\n'}, ['--prompt-file', 'x'], 'prompt sources reject'),
    ({'1-a.md': 'One.\n'}, ['--output', 'jsonl'], '--output jsonl is unsupported for sequence commands'),
]:
    s = run(steps, 2, args=args)
    assert reason in s['err'], (reason, s['err'])
    assert not s['launched'] and s['prompts'] == [], (reason, s)

# A directory or symlink entry rejects rather than being skipped.
with tempfile.TemporaryDirectory(prefix='ah-sequence-entries-') as d:
    folder = Path(d).resolve()
    (folder / '1-a.md').write_text('One.\n')
    (folder / '2-b.md').mkdir()
    proc = subprocess.run([str(BINARY), 'sequence', 'run', str(folder), '--preview'], capture_output=True, text=True)
    assert proc.returncode == 2 and 'not symlinks or directories' in proc.stderr, proc.stderr
    (folder / '2-b.md').rmdir()
    (folder / '2-b.md').symlink_to(folder / '1-a.md')
    proc = subprocess.run([str(BINARY), 'sequence', 'run', str(folder), '--preview'], capture_output=True, text=True)
    assert proc.returncode == 2 and 'not symlinks or directories' in proc.stderr, proc.stderr
    print('PASS entries', flush=True)

# Preview: one line per step with identity, agent, check and any refusal;
# nothing launched and no project writes.
s = run({'1-a.md': 'One.\n', '2-b.md': '---\nagent: thinker\nverify: build\n---\nTwo.\n'}, 0,
        args=['--verify', 'test'], preview=True)
assert not s['launched'] and s['prompts'] == [] and s['checks'] == []
assert 'sequence preview: 2 steps; nothing launched' in s['out'], s['out']
assert 'step 1 1-a.md: sha256 ' in s['out'] and 'agent none' in s['out'] and 'check "test"' in s['out']
assert 'step 2 2-b.md: sha256 ' in s['out'] and 'agent "thinker"' in s['out'] and 'check "build"' in s['out']
assert 'execution refused: agent effort is unsupported' in s['out']
assert 'One.' not in s['out'] and 'Two.' not in s['out'], 'prompt text is omitted'
assert 'opencode.json' not in s['files'], s['files']

print('sequence: all cases passed')
