#!/usr/bin/env python3
"""P4.7 version-1 machine output fixtures (D039) against fake OpenCode 2.2.5; no model traffic.

The validator below is written as an independent consumer would: it relies only
on the documented contract, never on harness internals. Build target/debug/ah first.
"""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'
PROMPT = 'PROMPT_SENTINEL task'
OUTCOMES = {0: 'succeeded', 1: 'failed', 2: 'rejected', 3: 'cancelled', 4: 'uncertain'}
ATTEMPT_KEYS = {'attempt', 'route', 'runtime', 'runtime_version', 'model', 'group', 'permissions', 'agent',
                'launched', 'session', 'prompt_submitted', 'backend_stop', 'cleanup_confirmed',
                'permission_requests', 'grants', 'tool_events', 'protocol_violation',
                'runtime_state_removed', 'usage'}
USAGE_KEYS = {'source', 'context_used_tokens', 'context_capacity_tokens', 'turn_tokens', 'session_cost'}


def consume(out, err, code):
    """Validate a complete stdout stream and return (records, result)."""
    assert 'SECRET_SENTINEL' not in out + err and 'PROMPT_SENTINEL' not in out + err
    lines = out.split('\n')
    assert lines[-1] == '', 'stdout must end with a complete record'
    records = [json.loads(line) for line in lines[:-1]]
    assert records, 'machine mode always writes records'
    for line in err.splitlines():
        assert line.startswith('ah: '), ('stderr carries only human diagnostics', line)
    run = records[0]['run']
    previous = None
    for r in records:
        assert isinstance(r, dict) and r['v'] == 1 and r['run'] == run, r
        assert isinstance(r['type'], str) and isinstance(r['ts_ms'], int) and isinstance(r['elapsed_ms'], int), r
        if previous is not None:
            assert r['seq'] > previous['seq'] and r['elapsed_ms'] >= previous['elapsed_ms'], (previous, r)
        previous = r
    assert records[0]['type'] == 'run.started' and records[0]['seq'] == 0, records[0]
    result = records[-1]
    assert result['type'] == 'result' and [r['type'] for r in records].count('result') == 1, records
    if result['records_dropped'] == 0:
        assert [r['seq'] for r in records] == list(range(len(records))), 'gaps only after dropped records'
    assert result['exit'] == code and result['outcome'] == OUTCOMES[code], (code, result)
    assert result['reason'] is None or isinstance(result['reason'], str)
    assert isinstance(result['fallback'], bool) and isinstance(result['recovery'], str)
    for attempt in result['attempts']:
        assert set(attempt) == ATTEMPT_KEYS, set(attempt) ^ ATTEMPT_KEYS
        assert set(attempt['usage']) == USAGE_KEYS and attempt['usage']['turn_tokens'] is None
        if attempt['prompt_submitted']:
            assert attempt['launched'] and attempt['session'] is not None, attempt
    if code != 0:
        # A non-success result never claims a delivered success.
        assert result['outcome'] != 'succeeded'
    return records, result


def run(case, expected, *, trusted=False, extra=(), stdin_open=False, interrupt=False, cfg=None, read_stdout=True):
    with tempfile.TemporaryDirectory(prefix='ah-machine-test-') as d:
        base = Path(d).resolve()
        (base/'opencode').symlink_to(FAKE)
        (base/'case').write_text(case)
        (base/'track-runtime-home').touch()
        (base/'ah.json').write_text(json.dumps(cfg or dict(version=1, mode='local-only', model='fixture',
            litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'))))
        args = [str(BINARY), 'single', PROMPT, '--project', str(base), '--timeout-secs', '15',
                '--output', 'jsonl', *extra]
        if trusted:
            args += ['--permissions', 'trusted']
        env = {**os.environ, 'PATH': str(base)+':'+os.environ['PATH'], 'TEST_KEY': 'SECRET_SENTINEL',
               'NATIVE_KEY': 'SECRET_SENTINEL', 'OPENCODE_CONFIG_CONTENT': 'poison'}
        p = subprocess.Popen(args, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
        if interrupt:
            until = time.monotonic() + 10
            while not (base/'prompted').exists() and p.poll() is None and time.monotonic() < until:
                time.sleep(.02)
            assert (base/'prompted').exists(), case
            p.send_signal(signal.SIGINT)
        if not read_stdout:
            # Never read stdout: the large result record cannot be delivered.
            started = time.monotonic()
            p.wait(timeout=20)
            assert time.monotonic() - started < 15, case
            assert p.returncode == expected, (case, p.returncode, p.stderr.read())
            print('PASS', case, 'blocked stdout', flush=True)
            return None
        if stdin_open:
            # No hidden interactive wait: stdin stays open and unread.
            p.wait(timeout=30)
            out, err = p.stdout.read(), p.stderr.read()
            p.stdin.close()
        else:
            out, err = p.communicate('', timeout=30)
        assert p.returncode == expected, (case, p.returncode, err)
        assert str(base) not in out, 'paths are never machine fields'
        records, result = consume(out, err, expected)
        print('PASS', case, expected, flush=True)
        return records, result


# Success: response moves from raw stdout into the result record.
records, result = run('text', 0, stdin_open=True)
types = [r['type'] for r in records]
assert types[:2] == ['run.started', 'attempt.started'] and 'attempt.session' in types, types
assert types.index('attempt.prompt_submitted') < types.index('attempt.backend_stop') < types.index('attempt.cleanup'), types
assert result['response'] == 'OK' and result['reason'] is None and result['fallback'] is False, result
(attempt,) = result['attempts']
assert attempt['route'] == 'local-only' and attempt['model'] == 'ah-litellm/fixture' and attempt['runtime'] == 'opencode', attempt
assert attempt['backend_stop'] == 'end_turn' and attempt['cleanup_confirmed'] is True and attempt['runtime_state_removed'] is True
assert attempt['permissions'] == 'deny' and attempt['agent'] is None and attempt['grants'] == 0, attempt
assert all(v is None for v in attempt['usage'].values()), 'unreported usage is null, never zero'

# Reported usage with units and provenance; an invalid cost stays unknown.
_, result = run('usage', 0)
usage = result['attempts'][0]['usage']
assert usage == dict(source='opencode-acp-usage-update', context_used_tokens=123, context_capacity_tokens=32000,
                     turn_tokens=None, session_cost=dict(amount=0.25, currency='USD')), usage
_, result = run('usage-invalid-cost', 0)
assert result['attempts'][0]['usage']['session_cost'] is None and result['attempts'][0]['usage']['context_used_tokens'] == 123

# Trusted grant counters.
_, result = run('read', 0, trusted=True)
assert result['attempts'][0]['grants'] == 1 and result['attempts'][0]['permission_requests'] == 1, result

# Known terminal failure, known cancellation and uncertainty keep D024 exits.
_, result = run('known-failure', 1)
assert result['attempts'][0]['backend_stop'] == 'other' and result['response'] is None, result
_, result = run('backend-cancelled', 3)
assert result['attempts'][0]['backend_stop'] == 'cancelled', result
_, result = run('deny-completed', 4)
assert result['attempts'][0]['protocol_violation'] is True and result['response'] is None, result
# R03-REC1 declined (D039): a post-submission failure without terminal evidence
# stays uncertain even with zero grants; the counters are reported instead.
_, result = run('rpc-error', 4)
a = result['attempts'][0]
assert a['prompt_submitted'] and a['backend_stop'] is None and a['grants'] == 0 and a['tool_events'] == 0, a
_, result = run('interrupt', 4, trusted=True, interrupt=True)
assert result['attempts'][0]['prompt_submitted'] is True, result

# Rejections still end in exactly one result record.
records, result = run('text', 2, extra=['--preview'])
assert [r['type'] for r in records] == ['run.started', 'result'] and '--preview' in result['reason'], result
records, result = run('text', 2, extra=['--output', 'jsonl'])
assert result['reason'] == 'duplicate option' and result['attempts'] == [], result
_, result = run('version', 2)
assert result['attempts'][0]['launched'] is False and result['attempts'][0]['prompt_submitted'] is False, result
assert result['reason'].startswith('preflight failed'), result

# A blocked consumer cannot stall cleanup; undelivered success becomes exit 1.
run('blocked-stdout', 1, read_stdout=False)

# Local-first fallback: two linked attempts in one run.
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    closed = f'http://127.0.0.1:{s.getsockname()[1]}/v1'
records, result = run('success', 0, cfg=dict(version=1, mode='local-first', model='fixture',
    litellm=dict(api_base=closed, api_key_env='TEST_KEY'),
    native=dict(target='opencode', model='fixture', api_key_env='NATIVE_KEY')))
assert result['fallback'] is True and [a['attempt'] for a in result['attempts']] == [1, 2], result
assert result['attempts'][0]['launched'] is False and result['attempts'][0]['route'] == 'local-first', result
assert result['attempts'][1]['route'] == 'local-first fallback' and result['attempts'][1]['model'] == 'opencode/fixture', result
fallback = next(r for r in records if r['type'] == 'fallback')
assert fallback['from_attempt'] == 1 and fallback['to_attempt'] == 2, fallback
assert all(r.get('attempt') == 2 for r in records if r['type'].startswith('attempt.') and r['seq'] > fallback['seq'])

# Human mode stays byte-for-byte unchanged on stdout.
with tempfile.TemporaryDirectory(prefix='ah-machine-test-') as d:
    base = Path(d).resolve()
    (base/'opencode').symlink_to(FAKE)
    (base/'case').write_text('text')
    (base/'ah.json').write_text(json.dumps(dict(version=1, mode='local-only', model='fixture',
        litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'))))
    env = {**os.environ, 'PATH': str(base)+':'+os.environ['PATH'], 'TEST_KEY': 'k'}
    for extra in [[], ['--output', 'human']]:
        p = subprocess.run([str(BINARY), 'single', 'Task', '--project', str(base), *extra],
                           env=env, capture_output=True, text=True, timeout=30)
        assert p.returncode == 0 and p.stdout == 'OK', (extra, p.stdout, p.stderr)
    p = subprocess.run([str(BINARY), 'single', 'Task', '--project', str(base), '--output', 'xml'],
                       env=env, capture_output=True, text=True, timeout=30)
    assert p.returncode == 2 and p.stdout == '' and 'unsupported output format' in p.stderr, p
# A runtime-phase rejection (missing key) also names its reason.
records, result = run('text', 2, extra=[], cfg=dict(version=1, mode='local-only', model='fixture',
    litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='ABSENT_KEY')))
assert result['reason'] == 'API key environment reference is missing or empty', result
print('PASS machine output fixtures')
