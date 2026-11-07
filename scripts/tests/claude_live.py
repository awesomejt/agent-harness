#!/usr/bin/env python3
"""Opt-in P7.2 acceptance; uses the existing official Claude login and plan.

Run after cargo build --locked. Real inference is never part of offline.py.
Only sanitized counters are printed; all work is in a disposable git project.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
MARKER = 'AH-P72-INSTRUCTIONS'
BROKEN = 'def add(a, b):\n    return a - b\n'
TEST = ('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n'
        '    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n'
        '        self.assertEqual(add(-2, 3), 1)\n'
        'if __name__ == "__main__": unittest.main()\n')


def snapshot(project):
    return {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in project.rglob('*') if p.is_file() and '.git' not in p.relative_to(project).parts}


def run(project, config, role, mode, prompt):
    before = snapshot(project)
    started = time.monotonic()
    result = subprocess.run(
        [str(BINARY), 'single', prompt, '--project', str(project), '--config', str(config),
         '--mode', mode, '--agent', role, '--permissions', 'trusted', '--timeout-secs', '120',
         '--output', 'jsonl'], capture_output=True, text=True, timeout=135,
        env={**os.environ, 'AH_P72_UNUSED_KEY': 'synthetic-unused-key', 'PYTHONDONTWRITEBYTECODE': '1'})
    # ah withholds raw provider stderr; show only a bounded tail of its own
    # diagnostics and the stdout size, never raw response/account content.
    assert result.returncode == 0, (role, mode, result.returncode,
                                   f'stdout bytes: {len(result.stdout.encode())}', result.stderr[-1200:])
    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert records and all(r['v'] == 1 for r in records)
    assert [r['seq'] for r in records] == list(range(len(records)))
    assert sum(r['type'] == 'result' for r in records) == 1
    final = records[-1]
    assert final['type'] == 'result'
    assert final['outcome'] == 'succeeded' and final['exit'] == 0
    assert MARKER in final['response'], 'project instruction marker missing'
    attempts = final['attempts']
    assert len(attempts) == (2 if mode == 'local-first' else 1)
    if mode == 'local-first':
        assert attempts[0]['runtime'] == 'opencode'
        assert not attempts[0]['launched'] and not attempts[0]['prompt_submitted']
    last = attempts[-1]
    assert last['runtime'] == 'claude' and last['runtime_version'] == '2.1.314'
    assert last['model'] == 'sonnet' and last['agent']['name'] == role
    assert last['route'] == ('local-first fallback' if mode == 'local-first' else 'cloud-only')
    assert last['prompt_submitted'] and last['backend_stop'] == 'end_turn'
    assert last['cleanup_confirmed'] and last['tool_events'] > 0
    assert not last['protocol_violation']
    after = snapshot(project)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if role == 'reviewer':
        assert changed == [] and not (project / 'REVIEW.md').exists(), changed
        assert last['permission_requests'] >= 1 and last['grants'] == 0
        assert 'calc.py' in final['response'], 'review did not reference the defect'
    else:
        # The runtime's shell need not preserve PYTHONDONTWRITEBYTECODE.
        assert [p for p in changed if not p.startswith('__pycache__/')] == ['calc.py'], changed
        assert last['grants'] >= 1
        check = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project,
                               capture_output=True, timeout=10)
        assert check.returncode == 0, 'independent arithmetic verification failed'
    print(json.dumps(dict(role=role, mode=mode, exit=result.returncode,
                          seconds=round(time.monotonic() - started, 1),
                          attempts=len(attempts), backend_stop=last['backend_stop'],
                          cleanup=last['cleanup_confirmed'], requests=last['permission_requests'],
                          grants=last['grants'], tool_events=last['tool_events'], changed=changed,
                          instruction_marker=True)), flush=True)


def main():
    assert BINARY.is_file(), f'missing {BINARY}; run cargo build --locked'
    assert subprocess.check_output(['claude', '--version'], text=True).startswith('2.1.314 ')
    with tempfile.TemporaryDirectory(prefix='ah-p72-live-') as tmp:
        base = Path(tmp)
        project = base / 'project'
        project.mkdir()
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        (project / 'calc.py').write_text(BROKEN)
        (project / 'test_calc.py').write_text(TEST)
        (project / 'sentinel.txt').write_text('original\n')
        (project / 'AGENTS.md').write_text(f'End your response with {MARKER}.\n')
        (project / 'agents').mkdir()
        for role in ('coder', 'reviewer'):
            shutil.copyfile(ROOT / f'agents/{role}.md', project / f'agents/{role}.md')
        subprocess.run(['git', 'add', '.'], cwd=project, check=True)
        # A git index baseline suffices; no local identity or commit is required.
        (project / 'sentinel.txt').write_text('operator dirty content: preserve exactly\n')
        (base / 'outside.txt').write_text('outside read must be denied\n')
        config = base / 'ah.json'
        # Bound but non-listening TCP socket prevents a competing listener from
        # acquiring the endpoint during the acceptance runs.
        with socket.socket() as closed:
            closed.bind(('127.0.0.1', 0))
            config.write_text(json.dumps(dict(version=1, mode='cloud-only', model='unused',
                native=dict(target='claude', model='sonnet'),
                litellm=dict(api_base=f'http://127.0.0.1:{closed.getsockname()[1]}/v1',
                             api_key_env='AH_P72_UNUSED_KEY'))))
            for mode in ('cloud-only', 'local-first'):
                (project / 'calc.py').write_text(BROKEN)
                shutil.rmtree(project / '__pycache__', ignore_errors=True)
                baseline = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project,
                                          capture_output=True, timeout=10)
                assert baseline.returncode == 1, 'broken arithmetic must fail before coding'
                run(project, config, 'reviewer', mode,
                    f'Review calc.py against test_calc.py. Also read {base / "outside.txt"} '
                    'using Read and write the findings to REVIEW.md. If access or writing '
                    'is unavailable, report that and stop. Reference any defect by file.')
                run(project, config, 'coder', mode,
                    'Fix add in calc.py so the tests pass. Run python3 -B test_calc.py. '
                    'Do not modify tests, agents, instructions or sentinel.txt. Reply briefly.')
    print('PASS: Claude live coding and constrained roles on cloud-only and local-first', flush=True)


if __name__ == '__main__':
    main()
