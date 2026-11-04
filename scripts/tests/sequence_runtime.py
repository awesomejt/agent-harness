#!/usr/bin/env python3
"""P5.2 installed OpenCode 2.2.5 sequence check against a local deterministic model stub.

Four gated steps run through `ah sequence run`: steps 1 and 2 create files
through the real shell tool (step 2 only if step 1's file exists), step 3's
agent succeeds without creating its file, so its gate fails and step 4 must
never reach the model. No credentials or model traffic leave the host.
Build target/debug/ah first.
"""
import contextlib
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
SHELL = {'STEP-ONE': 'touch one.txt', 'STEP-TWO': 'test -f one.txt && touch two.txt'}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            assert self.path == '/v1/chat/completions' and 0 < size <= 2_000_000
            body = json.loads(self.rfile.read(size))
            assert body['model'] == 'fixture'
            tools = [t['function']['name'] for t in body.get('tools', [])]
            users = [m for m in body['messages'] if m['role'] == 'user']
            text = json.dumps(users[-1]['content']) if users else ''
            marker = next((m for m in ['STEP-ONE', 'STEP-TWO', 'STEP-THREE', 'STEP-FOUR'] if m in text), None)
            answered = any(m['role'] == 'tool' for m in body['messages'])
            if tools and marker and not answered:
                self.server.markers.append(marker)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()

            def event(delta, finish=None):
                packet = dict(id='fixture', object='chat.completion.chunk', model='fixture',
                              choices=[dict(index=0, delta=delta, finish_reason=finish)])
                self.wfile.write(('data: ' + json.dumps(packet) + '\n\n').encode())
                self.wfile.flush()
            if tools and marker in SHELL and not answered:
                arguments = dict(command=SHELL[marker], description='Create step file')
                event(dict(role='assistant', tool_calls=[dict(index=0, id='call-' + marker, type='function',
                      function=dict(name='shell', arguments=json.dumps(arguments)))]))
                event({}, 'tool_calls')
            else:
                event(dict(role='assistant', content='Done.'))
                event({}, 'stop')
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.server.failed = True
            self.send_error(502, 'test request failed')


@contextlib.contextmanager
def server():
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    s.daemon_threads = True
    s.markers = []
    s.failed = False
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    try:
        yield s, 'http://127.0.0.1:' + str(s.server_port) + '/v1'
    finally:
        s.shutdown()
        s.server_close()
        t.join(timeout=2)


def main():
    binary = ROOT / 'target/debug/ah'
    with server() as (s, endpoint), tempfile.TemporaryDirectory(prefix='ah-sequence-runtime-') as d:
        # The state directory must lie outside the project (D044).
        cwd = Path(d).resolve() / 'project'
        state = Path(d).resolve() / 'state'
        subprocess.run(['git', 'init', '-q', str(cwd)], check=True)
        test = shutil.which('test')
        checks = {name: dict(argv=[test, '-f', f'{name}.txt'], timeout_secs=30) for name in ['one', 'two', 'three']}
        (cwd / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only', model='fixture',
            litellm=dict(api_base=endpoint, api_key_env='TEST_KEY'), checks=checks)))
        prompts = cwd / 'prompts'
        prompts.mkdir()
        (prompts / '1-one.md').write_text('STEP-ONE: create one.txt with the shell tool. Reply briefly.\n')
        (prompts / '2-two.md').write_text('---\nverify: two\n---\nSTEP-TWO: create two.txt only if one.txt exists.\n')
        (prompts / '3-three.md').write_text('---\nverify: three\n---\nSTEP-THREE: reply briefly.\n')
        (prompts / '4-four.md').write_text('STEP-FOUR: must never run.\n')
        p = subprocess.run([str(binary), 'sequence', 'run', str(prompts), '--project', str(cwd),
                            '--permissions', 'trusted', '--verify', 'one', '--timeout-secs', '120'],
                           env={**os.environ, 'TEST_KEY': 'unused', 'XDG_STATE_HOME': str(state)}, capture_output=True, text=True, timeout=600)
        print('CLI exit:', p.returncode, flush=True)
        print('stderr:', p.stderr.strip(), flush=True)
        print('Model turns by step:', s.markers, flush=True)
        assert p.returncode == 1 and not s.failed, p.returncode
        assert s.markers == ['STEP-ONE', 'STEP-TWO', 'STEP-THREE'], s.markers
        assert (cwd / 'one.txt').exists() and (cwd / 'two.txt').exists() and not (cwd / 'three.txt').exists()
        err = p.stderr
        assert 'verification="one" "passed"' in err and 'verification="two" "passed"' in err
        assert 'verification="three" "failed"' in err
        assert 'stopped at step 3/4 3-three.md (outcome failed); 1 later steps pending and not launched' in err
        assert err.count('runtime_state_removed') == 0 and err.count('outcome=') == 3
        # P5.3: the durable record shows the same stop, with no prompt text.
        record = next((state / 'agent-harness/sequences').glob('s*.json'))
        text = record.read_text()
        assert 'STEP-' not in text and 'unused' not in text
        r = json.loads(text)
        assert r['status'] == 'stopped', r['status']
        assert [s['status'] for s in r['steps']] == ['succeeded', 'succeeded', 'failed', 'pending']
        three = r['steps'][2]['attempts'][0]
        assert three['agent_outcome'] == 'succeeded' and three['verification']['status'] == 'failed'
        assert three['backends'][0]['prompt_submitted'] is True
        print('PASS installed OpenCode 2.2.5 sequence: ordered gated steps, filesystem continuity, '
              'failed gate stopped step 4 before launch; durable record matches; local deterministic model stub', flush=True)


if __name__ == '__main__':
    main()
