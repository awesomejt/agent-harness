#!/usr/bin/env python3
"""P4.4 live named-role acceptance on installed OpenCode 2.2.5.

Runs the example coder and reviewer roles through a recording forwarder to the
existing LiteLLM proxy and through the native OpenCode API-key route, plus a
local-first fallback, prohibited operations and unsupported-effort refusals.
Every coding run uses --output jsonl. Credentials and raw requests/responses
stay in memory; only tool names, marker presence and counters are printed.
"""
import argparse
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
MARKER = 'AH-P44-INSTRUCTIONS'
MANAGED = {'opencode.json', '.ah-opencode-owner.json', '.ah-opencode-agents.json', '.ah-opencode.lock'}
CODER_TOOLS = {'read', 'glob', 'grep', 'edit', 'write', 'shell', 'skill', 'opencode_worktree_remove'}
REVIEWER_TOOLS = {'read', 'glob', 'grep', 'skill'}
FIX = ('Fix add in calc.py so it adds correctly. Read calc.py, edit it, then run python3 test_calc.py '
       'and touch verified only if it passes. Do not change test_calc.py. Reply briefly.')
REVIEW = 'Review calc.py against test_calc.py and report any defect with its line. Reply briefly.'
PROHIBITED = ('Edit calc.py so add returns a + b, then run python3 test_calc.py and touch verified. '
              'If you cannot edit or run commands, say so and stop.')


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
            system = '\n'.join(m['content'] if isinstance(m['content'], str) else json.dumps(m['content'])
                               for m in body.get('messages', []) if m.get('role') == 'system')
            self.server.records.append(dict(model=body['model'], tools=tools, marker=MARKER in system,
                                            role=self.server.role_text in system if self.server.role_text else None))
            req = urllib.request.Request(self.server.upstream + '/chat/completions', data=raw,
                                         headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.server.key})
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
    s.upstream, s.key, s.records, s.failed, s.role_text = upstream, key, [], None, None
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    try:
        yield s, f'http://127.0.0.1:{s.server_port}/v1'
    finally:
        s.shutdown(); s.server_close(); t.join(timeout=2)


def closed_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def snapshot(cwd):
    return {str(p.relative_to(cwd)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(cwd.rglob('*')) if p.is_file() and '.git' not in p.relative_to(cwd).parts}


def reset(cwd):
    subprocess.run(['git', 'checkout', '-q', '--', 'calc.py'], cwd=cwd, check=True)
    (cwd / 'verified').unlink(missing_ok=True)


def changed(before, after):
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k)
                  and k not in MANAGED and not k.startswith(('.opencode/agents/', '__pycache__/')))


def run(args, cwd, name, prompt, mode, agent, permissions, secrets, config=None):
    cmd = [str(args.binary), 'single', prompt, '--project', str(cwd), '--mode', mode, '--agent', agent,
           '--permissions', permissions, '--timeout-secs', str(args.timeout_secs), '--output', 'jsonl']
    if config:
        cmd += ['--config', str(config)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout_secs + 30)
    for value in secrets:
        assert value not in p.stdout and value not in p.stderr, f'{name}: credential value echoed'
    records = [json.loads(line) for line in p.stdout.splitlines()]
    assert records and all(r['v'] == 1 for r in records), name
    assert [r['seq'] for r in records] == list(range(len(records))), name
    result = records[-1]
    assert result['type'] == 'result' and result['exit'] == p.returncode, (name, result)
    assert [r['type'] for r in records].count('result') == 1, name
    return p, records, result


def summary(name, p, result, wire, cwd, extra=''):
    a = result['attempts'][-1] if result['attempts'] else {}
    usage = a.get('usage') or {}
    cost = usage.get('session_cost')
    row = dict(case=name, exit=p.returncode, outcome=result['outcome'], route=a.get('route'), model=a.get('model'),
               agent=a.get('agent'), requests=len(wire), perm_requests=a.get('permission_requests'),
               grants=a.get('grants'), tool_events=a.get('tool_events'), backend_stop=a.get('backend_stop'),
               context_tokens=usage.get('context_used_tokens'), cost=cost and f"{cost['amount']} {cost['currency']}",
               edited='return a + b' in (cwd / 'calc.py').read_text(), verified=(cwd / 'verified').exists(),
               response_marker=bool(result['response'] and MARKER in result['response']))
    print('ROW', json.dumps(row), extra, flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/release/ah')
    parser.add_argument('--endpoint', default='http://litellm:4000/v1')
    parser.add_argument('--local-model', default='flash')
    parser.add_argument('--native-model', default='deepseek-v4.1-flash-free')
    parser.add_argument('--timeout-secs', type=int, default=300)
    args = parser.parse_args()
    args.binary = args.binary.expanduser().resolve()
    assert args.binary.is_file() and os.access(args.binary, os.X_OK), args.binary
    secrets = [os.environ['LITELLM_API_KEY'], os.environ['OPENCODE_API_KEY']]
    assert all(secrets), 'LITELLM_API_KEY and OPENCODE_API_KEY must be set'
    rows = []
    with forwarder(args.endpoint, secrets[0]) as (fw, endpoint), tempfile.TemporaryDirectory(prefix='ah-p44-') as d:
        cwd = Path(d).resolve()
        subprocess.run(['git', 'init', '-q', str(cwd)], check=True)
        (cwd / 'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (cwd / 'test_calc.py').write_text('from calc import add\nassert add(2, 3) == 5\nprint("PASS arithmetic")\n')
        (cwd / 'AGENTS.md').write_text(f'# Project rules\n\nEnd every final reply with the exact line {MARKER}.\n')
        (cwd / 'agents').mkdir()
        for role in ('coder', 'reviewer'):
            shutil.copy(ROOT / 'agents' / f'{role}.md', cwd / 'agents' / f'{role}.md')
        effortful = (ROOT / 'agents/reviewer.md').read_text().replace('name: reviewer', 'name: deep-reviewer') \
            .replace('tools: [read, search]', 'tools: [read, search]\neffort: high')
        (cwd / 'agents/deep-reviewer.md').write_text(effortful)
        native = dict(target='opencode', model=args.native_model, api_key_env='OPENCODE_API_KEY')
        (cwd / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only', model=args.local_model,
            litellm=dict(api_base=endpoint, api_key_env='LITELLM_API_KEY'), native=native)))
        fallback_cfg = cwd.parent / (cwd.name + '-fallback.json')
        fallback_cfg.write_text(json.dumps(dict(version=1, mode='local-first', model=args.local_model,
            litellm=dict(api_base=f'http://127.0.0.1:{closed_port()}/v1', api_key_env='LITELLM_API_KEY'), native=native)))
        subprocess.run(['git', 'add', '-A'], cwd=cwd, check=True)
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base'], cwd=cwd, check=True)
        # AC05: uncommitted tracked and untracked work must survive every named run.
        (cwd / 'AGENTS.md').write_text((cwd / 'AGENTS.md').read_text() + '\nUncommitted note.\n')
        (cwd / 'scratch.txt').write_text('untracked work\n')
        dirty = {k: v for k, v in snapshot(cwd).items() if k in ('AGENTS.md', 'scratch.txt')}
        role_body = {r: (ROOT / 'agents' / f'{r}.md').read_text().split('---\n', 2)[2].strip().splitlines()[0]
                     for r in ('coder', 'reviewer')}

        def live(name, prompt, mode, agent, permissions='trusted', config=None):
            reset(cwd)
            fw.records.clear(); fw.failed = None; fw.role_text = role_body[agent]
            before = snapshot(cwd)
            p, records, result = run(args, cwd, name, prompt, mode, agent, permissions, secrets, config)
            assert fw.failed is None, (name, fw.failed)
            wire = list(fw.records)
            rows.append(summary(name, p, result, wire, cwd, extra='wire=' + json.dumps(
                dict(tools=sorted({t for r in wire for t in r['tools']}), marker=[r['marker'] for r in wire],
                     role=[r['role'] for r in wire]))))
            return p, records, result, wire, changed(before, snapshot(cwd))

        def started(records, route, agent, capacity):
            (s,) = [r for r in records if r['type'] == 'attempt.started' and r['route'] == route]
            assert s['agent'] == dict(name=agent, capacity=capacity) and s['permissions'] in ('trusted', 'deny'), s
            return s

        def primary_requests(wire):
            return [r for r in wire if r['tools']]  # the title helper has no tools

        # 1. Coding role, LiteLLM: real edit and test; instructions and role text reach the model.
        p, records, result, wire, diff = live('coder local-only', FIX, 'local-only', 'coder')
        started(records, 'local-only', 'coder', 'primary')
        assert p.returncode == 0 and result['outcome'] == 'succeeded' and diff == ['calc.py', 'verified'], (p.returncode, diff)
        assert subprocess.run(['python3', 'test_calc.py'], cwd=cwd, capture_output=True).returncode == 0
        req = primary_requests(wire)
        assert req and all(r['model'] == args.local_model and r['marker'] and r['role'] for r in req), req
        assert set().union(*(set(r['tools']) for r in req)) <= CODER_TOOLS
        assert (cwd / '.opencode/agents/coder.md').is_file()

        # 2. Constrained reviewer, LiteLLM: read-only tool set on the wire; no project change.
        p, records, result, wire, diff = live('reviewer local-only', REVIEW, 'local-only', 'reviewer')
        started(records, 'local-only', 'reviewer', 'specialized')
        req = primary_requests(wire)
        assert p.returncode == 0 and diff == [] and result['response'], (p.returncode, diff)
        assert req and all(set(r['tools']) == REVIEWER_TOOLS and r['marker'] and r['role'] for r in req), req

        # 3. Prohibited operation for the reviewer: edit/shell are not offered and nothing changes.
        p, records, result, wire, diff = live('reviewer prohibited local-only', PROHIBITED, 'local-only', 'reviewer')
        assert p.returncode in (0, 3) and diff == [], (p.returncode, diff)
        assert all(set(r['tools']) == REVIEWER_TOOLS for r in primary_requests(wire))

        # 4. Deny invocation narrows the coder below its trusted ceiling.
        p, records, result, wire, diff = live('coder deny-invocation local-only', FIX, 'local-only', 'coder', permissions='deny')
        assert started(records, 'local-only', 'coder', 'primary')['permissions'] == 'deny'
        assert p.returncode in (0, 3) and diff == [] and result['attempts'][-1]['grants'] == 0, (p.returncode, diff)
        assert all(set(r['tools']) <= {'skill'} for r in wire), wire

        # 5–6. Native route: coding role edits; reviewer refuses the prohibited operation.
        p, records, result, wire, diff = live('coder cloud-only', FIX, 'cloud-only', 'coder')
        started(records, 'cloud-only', 'coder', 'primary')
        assert not wire and p.returncode == 0 and diff == ['calc.py', 'verified'], (p.returncode, diff)
        assert subprocess.run(['python3', 'test_calc.py'], cwd=cwd, capture_output=True).returncode == 0
        p, records, result, wire, diff = live('reviewer prohibited cloud-only', PROHIBITED, 'cloud-only', 'reviewer')
        started(records, 'cloud-only', 'reviewer', 'specialized')
        assert not wire and p.returncode in (0, 3) and diff == [], (p.returncode, diff)

        # 7. Local-first: unreachable LiteLLM falls back natively with the same constrained role.
        p, records, result, wire, diff = live('reviewer local-first fallback', REVIEW, 'local-first', 'reviewer', config=fallback_cfg)
        started(records, 'local-first fallback', 'reviewer', 'specialized')
        assert not wire and p.returncode == 0 and diff == [] and result['fallback'], (p.returncode, diff, result['fallback'])
        assert [r['type'] for r in records].count('fallback') == 1

        # 8. Unsupported restriction: non-default effort refuses on every route before launch or writes.
        for mode, config in (('local-only', None), ('cloud-only', None), ('local-first', fallback_cfg)):
            reset(cwd)
            before = snapshot(cwd)
            p, records, result = run(args, cwd, f'effort {mode}', REVIEW, mode, 'deep-reviewer', 'trusted', secrets, config)
            assert p.returncode == 2 and result['outcome'] == 'rejected' and result['reason'], result
            assert result['attempts'] == [] and snapshot(cwd) == before
            print('ROW', json.dumps(dict(case=f'effort high {mode}', exit=2, outcome='rejected', reason=result['reason'],
                                         attempts=0, project_changed=False)), flush=True)
        preview = subprocess.run([str(args.binary), 'single', REVIEW, '--project', str(cwd), '--agent', 'deep-reviewer', '--preview'],
                                 capture_output=True, text=True)
        assert 'execution refused' in preview.stdout + preview.stderr, preview.returncode
        print('ROW', json.dumps(dict(case='effort high preview', exit=preview.returncode, refusal_reported=True)), flush=True)
        fallback_cfg.unlink()
        assert {k: v for k, v in snapshot(cwd).items() if k in dirty} == dirty
        status = subprocess.run(['git', 'status', '--porcelain'], cwd=cwd, capture_output=True, text=True).stdout
        assert ' M AGENTS.md' in status and '?? scratch.txt' in status and 'calc.py' not in status, status
        print('ROW', json.dumps(dict(case='dirty and untracked work', preserved=True)), flush=True)
    print(f'PASS {len(rows)} live role runs and 3 effort refusals', flush=True)


if __name__ == '__main__':
    main()
