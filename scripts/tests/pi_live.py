#!/usr/bin/env python3
"""Opt-in P8.3 acceptance; uses installed Pi 1.5.0 and an existing LiteLLM proxy.

Run after `cargo build --locked`. Real inference is never part of offline.py.
Only sanitized counters are printed; all work is in a disposable git project.
"""
import argparse
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MARKER = 'AH-P83-INSTRUCTIONS'
MARKER_TAIL = f' End your reply with the exact line {MARKER}.'
PI_VERSION = '1.5.0'
CODER_TOOLS = {'bash', 'edit', 'find', 'grep', 'read', 'write'}
REVIEWER_TOOLS = {'find', 'grep', 'read'}
BROKEN = 'def add(a, b):\n    return a - b\n'
TEST = ('import unittest\nfrom calc import add\nclass T(unittest.TestCase):\n'
        '    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n'
        '        self.assertEqual(add(-2, 3), 1)\n'
        'if __name__ == "__main__": unittest.main()\n')


class Forwarder(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            assert self.path == '/v1/chat/completions' and 0 < size <= 4_000_000
            raw = self.rfile.read(size)
            body = json.loads(raw)
            tools = sorted(t['function']['name'] for t in body.get('tools', []))
            self.server.records.append(dict(model=body['model'], tools=tools))
            req = urllib.request.Request(
                self.server.upstream + '/chat/completions',
                data=raw,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + self.server.key,
                },
            )
            with urllib.request.urlopen(req, timeout=240) as response:
                self.send_response(response.status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'text/event-stream'))
                self.end_headers()
                while chunk := response.read1(8192):
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.server.failed = type(e).__name__
            self.send_error(502, 'forward failed')


@contextlib.contextmanager
def forwarder(upstream, key):
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Forwarder)
    s.daemon_threads = True
    s.upstream, s.key, s.records, s.failed = upstream, key, [], None
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    try:
        yield s, f'http://127.0.0.1:{s.server_port}/v1'
    finally:
        s.shutdown()
        s.server_close()
        t.join(timeout=2)


def snapshot(project):
    return {
        str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in project.rglob('*')
        if p.is_file() and '.git' not in p.relative_to(project).parts
    }


def run_case(binary, project, config, role, prompt, timeout, key_env, key_value, wire, model):
    before = snapshot(project)
    started = time.monotonic()
    result = subprocess.run(
        [
            str(binary),
            'single',
            prompt,
            '--project',
            str(project),
            '--config',
            str(config),
            '--mode',
            'local-only',
            '--agent',
            role,
            '--permissions',
            'trusted',
            '--timeout-secs',
            str(timeout),
            '--output',
            'jsonl',
        ],
        capture_output=True,
        text=True,
        timeout=timeout + 30,
        env={**os.environ, key_env: key_value, 'PYTHONDONTWRITEBYTECODE': '1'},
    )
    assert key_value not in result.stdout and key_value not in result.stderr
    assert result.returncode == 0, (
        role,
        result.returncode,
        f'stdout bytes: {len(result.stdout.encode())}',
        result.stderr[-1200:],
    )
    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert records and all(r['v'] == 1 for r in records)
    assert [r['seq'] for r in records] == list(range(len(records)))
    assert sum(r['type'] == 'result' for r in records) == 1
    final = records[-1]
    assert final['type'] == 'result'
    assert final['outcome'] == 'succeeded' and final['exit'] == 0
    response = final.get('response') or ''
    assert response.strip(), (role, 'empty model response', result.stderr[-800:])
    assert MARKER in response, (role, len(response), response[:400])
    attempts = final['attempts']
    assert len(attempts) == 1
    last = attempts[0]
    assert last['runtime'] == 'pi' and last['runtime_version'] == PI_VERSION
    assert last['model'] == f'pi/{model}'
    assert last['agent']['name'] == role
    assert last['route'] == 'local-only'
    assert last['prompt_submitted'] and last['backend_stop'] == 'agent_settled'
    assert last['cleanup_confirmed'] and not last['protocol_violation']
    after = snapshot(project)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    row = dict(
        role=role,
        exit=result.returncode,
        seconds=round(time.monotonic() - started, 1),
        backend_stop=last['backend_stop'],
        cleanup=last['cleanup_confirmed'],
        requests=last['permission_requests'],
        grants=last['grants'],
        tool_events=last['tool_events'],
        changed=changed,
        instruction_marker=True,
        wire=len(wire),
    )
    if role == 'reviewer':
        content = [p for p in changed if not p.startswith('__pycache__/')]
        assert content == [] and not (project / 'REVIEW.md').exists(), changed
        assert 'calc.py' in final['response'], 'review did not reference the defect'
        if wire:
            assert all(set(r['tools']) <= REVIEWER_TOOLS for r in wire), wire
    else:
        assert [p for p in changed if not p.startswith('__pycache__/')] == ['calc.py'], changed
        assert last['grants'] >= 1
        assert wire and all(set(r['tools']) <= CODER_TOOLS for r in wire), wire
        check = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project, capture_output=True, timeout=10)
        assert check.returncode == 0, 'independent arithmetic verification failed'
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/debug/ah')
    parser.add_argument('--endpoint', default='http://litellm:4000/v1')
    parser.add_argument('--model', default='macmini-qwen3-coder-30b')
    parser.add_argument('--key-env', default='LITELLM_API_KEY')
    parser.add_argument('--timeout-secs', type=int, default=300)
    args = parser.parse_args()
    args.binary = args.binary.expanduser().resolve()
    assert args.binary.is_file(), f'missing {args.binary}; run cargo build --locked'
    version = subprocess.check_output(['pi', '--version'], text=True).strip()
    assert version.split()[0] == PI_VERSION, version
    key = os.environ.get(args.key_env)
    assert key, f'{args.key_env} must be set for live Pi acceptance'
    rows = []
    with forwarder(args.endpoint, key) as (fw, endpoint), tempfile.TemporaryDirectory(
        prefix='ah-p83-live-'
    ) as tmp:
        base = Path(tmp)
        project = base / 'project'
        project.mkdir()
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        (project / 'calc.py').write_text(BROKEN)
        (project / 'test_calc.py').write_text(TEST)
        (project / 'sentinel.txt').write_text('original\n')
        (project / 'AGENTS.md').write_text(
            f'# Project rules\n\nEnd every final reply with the exact line {MARKER}.\n'
        )
        (project / 'agents').mkdir()
        for role in ('coder', 'reviewer'):
            shutil.copyfile(ROOT / f'agents/{role}.md', project / f'agents/{role}.md')
        subprocess.run(['git', 'add', '.'], cwd=project, check=True)
        (project / 'sentinel.txt').write_text('operator dirty content: preserve exactly\n')
        (base / 'outside.txt').write_text('outside read must be denied\n')
        config = base / 'ah.json'
        config.write_text(
            json.dumps(
                dict(
                    version=1,
                    mode='local-only',
                    model=args.model,
                    litellm=dict(api_base=endpoint, api_key_env=args.key_env, runtime='pi'),
                )
            )
        )
        baseline = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project, capture_output=True, timeout=10)
        assert baseline.returncode != 0, 'broken arithmetic must fail before coding'
        outside = base / 'outside.txt'
        fw.records.clear()
        rows.append(
            run_case(
                args.binary,
                project,
                config,
                'reviewer',
                f'Review calc.py against test_calc.py. Also read {outside} with the read tool and '
                'write findings to REVIEW.md. If access or writing is unavailable, report that '
                f'and stop. Reference any defect by file.{MARKER_TAIL}',
                args.timeout_secs,
                args.key_env,
                key,
                fw.records,
                args.model,
            )
        )
        assert fw.failed is None, fw.failed
        (project / 'calc.py').write_text(BROKEN)
        shutil.rmtree(project / '__pycache__', ignore_errors=True)
        baseline = subprocess.run(['python3', '-B', 'test_calc.py'], cwd=project, capture_output=True, timeout=10)
        assert baseline.returncode != 0
        fw.records.clear()
        rows.append(
            run_case(
                args.binary,
                project,
                config,
                'coder',
                'Fix add in calc.py so the tests pass. Use bash to run python3 -B test_calc.py. '
                f'Do not modify tests, agents, instructions or sentinel.txt. Reply briefly.{MARKER_TAIL}',
                args.timeout_secs,
                args.key_env,
                key,
                fw.records,
                args.model,
            )
        )
        assert fw.failed is None, fw.failed
    print(f'PASS: Pi live reviewer and coder on local-only ({len(rows)} cases)', flush=True)


if __name__ == '__main__':
    main()
