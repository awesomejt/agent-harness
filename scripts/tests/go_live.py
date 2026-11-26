#!/usr/bin/env python3
"""Opt-in P7.12 acceptance; uses the operator-attested Go API key.

Run after cargo build --locked from the reviewed continuation revision.
Real inference is never part of offline.py. Only sanitized counters and
closed D107 labels are printed; all work is in a disposable git project.
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
MARKER = 'AH-P712-INSTRUCTIONS'
BROKEN = 'def add(a, b):\n    return a - b\n'
TEST = ('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n'
        '    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n'
        '        self.assertEqual(add(-2, 3), 1)\n'
        'if __name__ == "__main__": unittest.main()\n')


def snapshot(project):
    return {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in project.rglob('*') if p.is_file() and '.git' not in p.relative_to(project).parts}


def closed_labels(attempt):
    """Return only D107 closed labels; never provider text.

    Index required keys so a stale binary missing the schema fails loudly.
    """
    return attempt['acp_error'], attempt['acp_data']


def parse_records(stdout, *, strict=False):
    """Parse JSONL. Strict mode re-raises without echoing line content."""
    records = []
    for line in stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if strict:
                raise AssertionError('malformed JSONL line in harness stdout') from None
            break
    return records


def failure_summary(role, mode, result):
    # Sanitized stop diagnostics only: exit, closed labels, sizes. No response.
    labels = []
    for record in parse_records(result.stdout, strict=False):
        if record.get('type') != 'result':
            continue
        for attempt in record.get('attempts') or []:
            labels.append(dict(
                attempt=attempt.get('attempt'),
                prompt_submitted=attempt.get('prompt_submitted'),
                backend_stop=attempt.get('backend_stop'),
                cleanup_confirmed=attempt.get('cleanup_confirmed'),
                acp_error=attempt.get('acp_error'),
                acp_data=attempt.get('acp_data'),
                grants=attempt.get('grants'),
                tool_events=attempt.get('tool_events'),
            ))
    return (role, mode, result.returncode,
            f'stdout bytes: {len(result.stdout.encode())}',
            f'stderr bytes: {len(result.stderr.encode())}',
            labels, result.stderr[-1200:])


def run(project, config, role, mode, prompt, key):
    before = snapshot(project)
    started = time.monotonic()
    result = subprocess.run(
        [str(BINARY), 'single', prompt, '--project', str(project), '--config', str(config),
         '--mode', mode, '--agent', role, '--permissions', 'trusted', '--timeout-secs', '120',
         '--output', 'jsonl'], capture_output=True, text=True, timeout=135,
        env={**os.environ, 'P712_KEY': key, 'AH_P712_UNUSED_KEY': 'synthetic-unused-key', 'PYTHONDONTWRITEBYTECODE': '1'})
    # ah withholds raw provider stderr; show only closed D107 labels, a bounded
    # harness diagnostic tail, and sizes — never raw response/account content.
    assert result.returncode == 0, failure_summary(role, mode, result)
    records = parse_records(result.stdout, strict=True)
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
        assert closed_labels(attempts[0]) == (None, None)
    last = attempts[-1]
    # D106: machine records expose the supported-line constant, not a single patch.
    assert last['runtime'] == 'opencode', last.get('runtime')
    assert last['runtime_version'] == '2.3.x or 2.4.x', last.get('runtime_version')
    assert last['model'] == 'opencode-go/beam-free', last.get('model')
    assert last['agent']['name'] == role, last.get('agent')
    assert last['route'] == ('local-first fallback' if mode == 'local-first' else 'cloud-only'), last.get('route')
    assert last['prompt_submitted'] and last['backend_stop'] == 'end_turn', (
        last.get('prompt_submitted'), last.get('backend_stop'))
    assert last['cleanup_confirmed'] and last['tool_events'] > 0, (
        last.get('cleanup_confirmed'), last.get('tool_events'))
    assert not last['protocol_violation']
    assert closed_labels(last) == (None, None), 'success must leave acp labels null'
    after = snapshot(project)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if role == 'reviewer':
        # No project mutation; fixture suites own deny/grant matrix proof. Under
        # trusted Read/Search the model may receive grants for in-project reads.
        assert changed == [] and not (project / 'REVIEW.md').exists(), changed
        resp = final['response']
        lower = resp.lower()
        assert 'calc.py' in lower, ('review missing calc.py', f'response_bytes={len(resp.encode())}')
        assert any(t in lower for t in ('subtract', 'subtraction', 'a - b')), (
            'review missing subtraction defect', f'response_bytes={len(resp.encode())}')
        assert 'outside read must be denied' not in resp, 'outside sentinel appeared in response'
    else:
        # The runtime's shell need not preserve PYTHONDONTWRITEBYTECODE.
        assert [p for p in changed if not p.startswith('__pycache__/')] == ['calc.py'], changed
        assert last['grants'] >= 1
        check = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project,
                               capture_output=True, timeout=10)
        assert check.returncode == 0, 'independent arithmetic verification failed'
    err, data = closed_labels(last)
    print(json.dumps(dict(role=role, mode=mode, exit=result.returncode,
                          seconds=round(time.monotonic() - started, 1),
                          attempts=len(attempts), backend_stop=last['backend_stop'],
                          cleanup=last['cleanup_confirmed'], requests=last['permission_requests'],
                          grants=last['grants'], tool_events=last['tool_events'], changed=changed,
                          acp_error=err, acp_data=data,
                          instruction_marker=True)), flush=True)


def main():
    if not __debug__:
        raise SystemExit('assertions required for live acceptance')
    assert BINARY.is_file(), f'missing {BINARY}; run cargo build --locked'
    assert os.environ.get('AH_P712_LIVE') == 'operator-attested', 'setup review and fresh account attestation required'
    key = os.environ.pop('P712_KEY', '')
    os.environ.pop('AH_P712_LIVE', None)
    assert key and key != 'synthetic-unused-key', 'operator key required'
    runtime = shutil.which('opencode')
    assert runtime and Path(runtime).resolve() == Path('/opt/homebrew/Cellar/opencode/2.4.1/bin/opencode').resolve(), 'reviewed Homebrew runtime required'
    assert subprocess.check_output([runtime, '--version'], text=True).strip() == 'opencode v2.4.1'
    with tempfile.TemporaryDirectory(prefix='ah-p712-live-') as tmp:
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
                native=dict(target='opencode-go', model='beam-free', api_key_env='P712_KEY'),
                litellm=dict(api_base=f'http://127.0.0.1:{closed.getsockname()[1]}/v1',
                             api_key_env='AH_P712_UNUSED_KEY'))))
            for mode in ('cloud-only', 'local-first'):
                (project / 'calc.py').write_text(BROKEN)
                shutil.rmtree(project / '__pycache__', ignore_errors=True)
                baseline = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project,
                                          capture_output=True, timeout=10)
                assert baseline.returncode == 1, 'broken arithmetic must fail before coding'
                run(project, config, 'reviewer', mode,
                    f'Review calc.py against test_calc.py. In your FINAL reply, name the '
                    f'file you reviewed and describe the defect you found (do not only say '
                    f'that tests failed). Also try to read {base / "outside.txt"} using Read '
                    f'and write findings to REVIEW.md. If access or writing is unavailable, '
                    f'say so and stop.', key)
                run(project, config, 'coder', mode,
                    'Fix add in calc.py so the tests pass. Run python3 -B test_calc.py. '
                    'Do not modify tests, agents, instructions or sentinel.txt. Reply briefly.', key)
    print('PASS: Go live coding and constrained roles on cloud-only and local-first', flush=True)


if __name__ == '__main__':
    main()
