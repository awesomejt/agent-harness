#!/usr/bin/env python3
"""OpenCode 2.3.0 native-key isolation regression; no prompt reaches a model.

The harness invokes a disposable PATH shim.  Its ordinary preflight commands
exec the installed OpenCode unmodified.  On ACP startup only, the shim starts a
second, owned loopback server with the exact generated environment/configuration
that the harness supplied, waits for plugin activation, checks two stable integration lists, and records only counts.
It then proxies ACP initialization and intercepts the first prompt.
"""
import base64
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 256 * 1024


class NotReady(RuntimeError):
    """Only a missing activation marker may be retried; unsafe connections fail immediately."""


def port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def stop_group(child):
    if child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=3)


def get(server_port, password, project, path):
    """Bounded authenticated metadata GET; no session, auth or model route."""
    assert path in ('/api/provider', '/api/integration')
    authorization = 'Basic ' + base64.b64encode(f'opencode:{password}'.encode()).decode()
    query = urllib.parse.urlencode({'location[directory]': str(project)})
    connection = http.client.HTTPConnection('127.0.0.1', server_port, timeout=2)
    try:
        connection.request('GET', path + '?' + query, headers={
            'Authorization': authorization, 'Connection': 'close', 'Accept': 'application/json'})
        response = connection.getresponse()
        body = response.read(LIMIT + 1)
        assert response.status == 200 and len(body) <= LIMIT
        assert (response.getheader('content-type') or '').split(';')[0].strip() == 'application/json'
    finally:
        connection.close()
    envelope = json.loads(body)
    assert set(envelope) == {'location', 'data'} and envelope['location'] == {'directory': str(project)}
    return envelope['data']


def integrations(server_port, password, project):
    """Wait for plugin activation, then require a stable no-connection list."""
    providers = get(server_port, password, project, '/api/provider')
    assert isinstance(providers, list)
    if not any(item.get('id') == 'opencode' for item in providers if isinstance(item, dict)):
        raise NotReady('provider activation pending')
    entries = get(server_port, password, project, '/api/integration')
    assert isinstance(entries, list)
    if not entries:
        raise NotReady('integration activation pending')
    connections = {}
    methods = set()
    for entry in entries:
        assert isinstance(entry, dict) and isinstance(entry.get('id'), str) and isinstance(entry.get('connections'), list)
        # Do not retain or serialize method, label, identity, status or other metadata.
        connections[entry['id']] = len(entry['connections'])
        if entry['id'] == 'opencode':
            assert isinstance(entry.get('methods'), list)
            methods = {item.get('type') for item in entry['methods'] if isinstance(item, dict)}
    assert len(connections) == len(entries)
    time.sleep(.2)
    repeated = get(server_port, password, project, '/api/integration')
    shape = sorted((item['id'], len(item['connections'])) for item in repeated
                   if isinstance(item, dict) and isinstance(item.get('id'), str) and isinstance(item.get('connections'), list))
    assert shape == sorted(connections.items())
    assert all(value == 0 for value in connections.values())
    if 'opencode' not in connections or not {'oauth', 'key'} <= methods:
        raise NotReady('Console integration methods pending')
    return {'integrations': len(connections), 'connections': 0}


def observe(runtime):
    """Run before ACP prompt forwarding, in harness-provided private XDG state."""
    project = Path.cwd().resolve()
    config = json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])
    assert os.environ.get('AH_RUNTIME_API_KEY') == 'native-synthetic-key'
    assert 'OPENCODE_API_KEY' not in os.environ
    assert config['providers'] == {'opencode': {'settings': {'apiKey': '{env:AH_RUNTIME_API_KEY}'}}}
    assert 'native-synthetic-key' not in os.environ['OPENCODE_CONFIG_CONTENT']
    server_port, password = port(), secrets.token_urlsafe(24)
    server_env = dict(os.environ, OPENCODE_PASSWORD=password)
    child = subprocess.Popen([runtime, 'serve', '--hostname', '127.0.0.1', '--port', str(server_port)], cwd=project,
                             env=server_env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                summary = integrations(server_port, password, project)
                break
            except (NotReady, ConnectionRefusedError, ConnectionResetError, TimeoutError, http.client.HTTPException):
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise
                time.sleep(.05)
        (project / 'native-isolation-observation.json').write_text(json.dumps(summary, sort_keys=True))
    finally:
        stop_group(child)


def shim(runtime):
    args = sys.argv[3:]
    if 'acp' not in args:
        os.execv(runtime, [runtime, *args])
    observe(runtime)
    child = subprocess.Popen([runtime, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    lock = threading.Lock()

    def output():
        for line in child.stdout:
            with lock:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()

    threading.Thread(target=output, daemon=True).start()
    try:
        for line in sys.stdin.buffer:
            message = json.loads(line)
            if message.get('method') == 'session/prompt':
                Path('intercepted-native-prompt').touch()
                with lock:
                    print(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': {'stopReason': 'end_turn'}}), flush=True)
            else:
                assert message.get('method') != 'session/cancel'
                child.stdin.write(line)
                child.stdin.flush()
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)


def main():
    runtime = shutil.which('opencode')
    assert runtime and subprocess.run([runtime, '--version'], capture_output=True, text=True, timeout=10).stdout.strip() == 'opencode v2.3.0'
    binary = ROOT / 'target/debug/ah'
    assert binary.is_file() and os.access(binary, os.X_OK)
    with tempfile.TemporaryDirectory(prefix='ah-native-isolation-') as directory:
        base = Path(directory).resolve()
        bin_dir, project = base / 'bin', base / 'project'
        bin_dir.mkdir()
        project.mkdir()
        wrapper = bin_dir / 'opencode'
        wrapper.write_text('#!' + sys.executable + '\nimport os\nos.execv(' + repr(sys.executable) + ', ' +
                           repr([sys.executable, str(Path(__file__).resolve()), '--shim', str(Path(runtime).resolve())]) +
                           ' + __import__("sys").argv[1:])\n')
        wrapper.chmod(0o755)
        (project / 'ah.json').write_text(json.dumps({'version': 1, 'mode': 'cloud-only',
            'native': {'target': 'opencode', 'model': 'gpt-5.4', 'api_key_env': 'NATIVE_KEY'}}))
        env = {**os.environ, 'PATH': str(bin_dir) + ':' + os.environ['PATH'], 'NATIVE_KEY': 'native-synthetic-key',
               'OPENCODE_API_KEY': 'poison', 'OPENCODE_CONFIG_CONTENT': 'poison', 'OPENCODE_AUTH_CONTENT': 'poison'}
        result = subprocess.run([str(binary), 'single', 'Prompt must be intercepted.', '--project', str(project),
                                 '--timeout-secs', '45'], env=env, capture_output=True, text=True, timeout=75)
        assert result.returncode == 0, (result.returncode, result.stderr)
        assert (project / 'intercepted-native-prompt').is_file()
        summary = json.loads((project / 'native-isolation-observation.json').read_text())
        assert set(summary) == {'integrations', 'connections'} and summary['integrations'] > 0 and summary['connections'] == 0
        assert 'native-synthetic-key' not in result.stdout + result.stderr
    print('PASS installed OpenCode 2.3.0 native settings key: integration list has zero connections before intercepted ACP prompt')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--shim':
        shim(sys.argv[2])
    else:
        main()
