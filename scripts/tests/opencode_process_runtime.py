#!/usr/bin/env python3
"""OpenCode 2.3.0 trusted-shell cancellation and descendant-cleanup regression.

This runs one disposable local-only turn against a loopback model stub.  The
stub asks for a permitted shell tool, whose synthetic Python parent creates a
synthetic child.  Both write only their own PIDs beneath the disposable project.
The test interrupts ``ah`` after both processes are live, then requires the
harness terminal record to confirm cleanup and both marker-labelled processes to
be gone.  It never contacts a provider or inspects any user/runtime state.
"""
import contextlib
import http.server
import json
import os
from pathlib import Path
import shlex
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]


def command_for(project, marker):
    parent = project / 'synthetic-parent.pid'
    child = project / 'synthetic-child.pid'
    child_code = (
        'import os,pathlib,sys,time; p=pathlib.Path(sys.argv[1]); '
        't=p.with_suffix(".tmp"); t.write_text(str(os.getpid())); '
        't.replace(p); time.sleep(600)'
    )
    code = (
        'import pathlib,subprocess,sys,time; '
        'root=pathlib.Path(sys.argv[1]); marker=sys.argv[2]; '
        'p=root / "synthetic-parent.pid"; t=p.with_suffix(".tmp"); '
        't.write_text(str(__import__("os").getpid())); t.replace(p); '
        'child=subprocess.Popen([sys.executable,"-c",' + repr(child_code) + ','
        'str(root / "synthetic-child.pid"),marker]); '
        'time.sleep(600)'
    )
    return ' '.join(shlex.quote(value) for value in [sys.executable, '-c', code, str(project), marker]), parent, child


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert self.path == '/v1/chat/completions' and body['model'] == 'fixture'
            tools = {item['function']['name'] for item in body.get('tools', [])}
            self.server.requests.append(tools)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            if not self.server.sent:
                assert 'shell' in tools
                self.server.sent = True
                call = dict(index=0, id='ah-shell-cleanup', type='function',
                            function=dict(name='shell', arguments=json.dumps({
                                'command': self.server.command, 'description': 'Run disposable cancellation probe'})))
                event = dict(id='fixture', object='chat.completion.chunk', model='fixture',
                             choices=[dict(index=0, delta=dict(role='assistant', tool_calls=[call]),
                                           finish_reason=None)])
                self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
                terminal = dict(id='fixture', object='chat.completion.chunk', model='fixture',
                                choices=[dict(index=0, delta={}, finish_reason='tool_calls')])
                self.wfile.write(('data: ' + json.dumps(terminal) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush()
            else:
                # The process should be interrupted while its tool result is pending.
                while not self.server.stop.wait(.1):
                    pass
        except (BrokenPipeError, ConnectionResetError):
            pass


@contextlib.contextmanager
def server(command):
    value = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    value.daemon_threads = True
    value.command, value.sent, value.stop, value.requests = command, False, threading.Event(), []
    thread = threading.Thread(target=value.serve_forever, daemon=True)
    thread.start()
    try:
        yield value
    finally:
        value.stop.set()
        value.shutdown()
        value.server_close()
        thread.join(timeout=2)


def process_command(pid):
    result = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else ''


def marker_pid(path, marker):
    value = int(path.read_text())
    command = process_command(value)
    assert marker in command, (value, command)
    return value


def known_pids(paths, marker):
    """Recover only live PIDs whose command still carries this run's marker."""
    found = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            value = int(path.read_text())
        except ValueError:
            continue
        if marker in process_command(value):
            found.append(value)
    return found


def still_live(pid, marker):
    return marker in process_command(pid)


def cleanup(pids, marker):
    """Only signal processes this test can prove it created."""
    for pid in pids:
        if still_live(pid, marker):
            os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and any(still_live(pid, marker) for pid in pids):
        time.sleep(.05)
    for pid in pids:
        if still_live(pid, marker):
            os.kill(pid, signal.SIGKILL)


def main():
    runtime = shutil.which('opencode')
    assert runtime and subprocess.run([runtime, '--version'], capture_output=True, text=True, timeout=10).stdout.strip() == 'opencode v2.3.0'
    binary = ROOT / 'target/debug/ah'
    assert binary.is_file() and os.access(binary, os.X_OK)
    with tempfile.TemporaryDirectory(prefix='ah-opencode-shell-cancel-') as directory:
        project = Path(directory).resolve()
        marker = 'ah-process-cleanup-' + str(os.getpid()) + '-' + str(time.monotonic_ns())
        command, parent_file, child_file = command_for(project, marker)
        pids = []
        proc = None
        stdout = stderr = ''
        with server(command) as stub:
            (project / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only', model='fixture',
                litellm=dict(api_base=f'http://127.0.0.1:{stub.server_port}/v1', api_key_env='SHELL_KEY'))))
            subprocess.run(['git', 'init', '-q', str(project)], check=True)
            proc = subprocess.Popen([str(binary), 'single', 'Run the shell probe.', '--project', str(project),
                                     '--permissions', 'trusted', '--timeout-secs', '60', '--output', 'jsonl'],
                                    env={**os.environ, 'SHELL_KEY': 'unused'}, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and not (parent_file.is_file() and child_file.is_file()):
                    time.sleep(.05)
                assert parent_file.is_file() and child_file.is_file(), 'shell process pair did not start'
                pids = [marker_pid(parent_file, marker), marker_pid(child_file, marker)]
                proc.send_signal(signal.SIGINT)
                stdout, stderr = proc.communicate(timeout=30)
                # This is the assertion under test.  The fallback reaper below runs
                # only after this observation, so it cannot turn a leaked child into
                # a passing result.
                assert not any(still_live(pid, marker) for pid in pids), pids
            finally:
                # A failed/partial startup can still have created one labelled child.
                # Recover it from the disposable files, but never signal an arbitrary PID.
                pids = list(dict.fromkeys([*pids, *known_pids([parent_file, child_file], marker)]))
                if proc.poll() is None:
                    proc.send_signal(signal.SIGINT)
                    try:
                        proc.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                cleanup(pids, marker)
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
        records = [json.loads(line) for line in stdout.splitlines()]
        result = records[-1]
        attempt, = result['attempts']
        assert proc.returncode == 3 and result['outcome'] == 'cancelled', (proc.returncode, result)
        assert attempt['cleanup_confirmed'] is True and attempt['runtime_state_removed'] is True, attempt
        assert len(stub.requests) >= 1 and 'shell' in stub.requests[0]
        assert 'process cleanup started' in stderr and 'cleanup=true; terminal=3;' in stderr, stderr
    print('PASS installed OpenCode 2.3.0: interrupted trusted shell cleaned labelled parent and child')


if __name__ == '__main__':
    main()
