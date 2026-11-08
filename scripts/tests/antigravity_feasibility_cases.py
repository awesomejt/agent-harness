#!/usr/bin/env python3
"""Offline adversarial checks for the no-inference Antigravity probe."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'experiments/antigravity_feasibility.py'
spec = importlib.util.spec_from_file_location('antigravity_probe', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
VALID = {'jsonrpc': '2.0', 'id': 1, 'result': {
    'protocolVersion': 1, 'agentInfo': {'name': 'Antigravity ACP Server', 'version': '1.5.3'},
    'agentCapabilities': {}, 'authMethods': [{'id': x} for x in [
        'oauth-personal', 'oauth-business', 'gemini-api-key', 'agent-platform']]}}


def refuses(callback):
    try:
        callback()
    except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        return
    raise AssertionError('unsafe input was accepted')


def alive(pid):
    result = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)],
                            capture_output=True, text=True, timeout=2)
    return result.returncode == 0 and not result.stdout.strip().startswith('Z')


def main():
    probe.validate(json.dumps(VALID).encode())
    invalid = [None, [], 7, {'jsonrpc': '1.0', **{k: v for k, v in VALID.items() if k != 'jsonrpc'}},
               {**VALID, 'id': True}, {**VALID, 'id': 2},
               {**VALID, 'error': {}}, {**VALID, 'method': 'session/request_permission'}]
    for key, value in [('protocolVersion', True), ('protocolVersion', 2), ('agentInfo', {}),
                       ('agentCapabilities', []), ('authMethods', [None]), ('authMethods', []),
                       ('tools', []), ('models', [])]:
        bad = copy.deepcopy(VALID)
        bad['result'][key] = value
        invalid.append(bad)
    for payload in invalid:
        refuses(lambda: probe.validate(json.dumps(payload).encode()))
    for payload in [b'', b'private diagnostic', json.dumps(VALID).encode() + b'\n' + json.dumps(VALID).encode()]:
        refuses(lambda: probe.validate(payload))
    for method in ['authenticate', 'session/new', 'session/prompt', 'session/set_model', 'initialize\n']:
        refuses(lambda: probe.request(method))
    with patch.object(probe.subprocess, 'Popen') as popen:
        refuses(lambda: probe.capture(['must-not-launch'], '.', {}, b'{}'))
        popen.assert_not_called()
    with patch.object(probe.os, 'killpg', side_effect=PermissionError):
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 1, b'', b'')):
            probe.signal_group(12345, 9)
        with patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess(
                [], 0, b'S\n', b'')):
            refuses(lambda: probe.signal_group(12345, 9))
    with tempfile.TemporaryDirectory(prefix='ah-agy-offline-') as directory:
        root = Path(directory)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(root)}
        out, err = probe.capture([sys.executable, '-c',
            'import sys; print(sys.stdin.read())'], root, env, probe.request('initialize'))
        assert not err and json.loads(out)['method'] == 'initialize'
        # Combined stderr/stdout limit applies during reading, not after exit.
        with patch.object(probe, 'LIMIT', 1024):
            refuses(lambda: probe.capture([sys.executable, '-c',
                'import sys; sys.stdout.write("x"*600); sys.stdout.flush(); '
                'sys.stderr.write("y"*600)'], root, env))
        refuses(lambda: probe.capture([sys.executable, '-c', 'raise SystemExit(4)'], root, env))
        for behavior in ['sleep', 'leader-exit']:
            pidfile = root / behavior
            code = ('import subprocess,sys,time; from pathlib import Path; '
                    'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); '
                    f'Path({str(pidfile)!r}).write_text(str(child.pid)); '
                    + ('time.sleep(30)' if behavior == 'sleep' else 'sys.exit(0)'))
            with patch.object(probe, 'TIMEOUT', 1):
                refuses(lambda: probe.capture([sys.executable, '-c', code], root, env))
            assert not alive(int(pidfile.read_text())), 'descendant survived cleanup'
        # Use real process discovery: start_new_session has no terminal. A
        # simulated signal denial must not turn a live group into a gone group.
        if sys.platform == 'darwin':
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                     start_new_session=True)
            try:
                with patch.object(probe.os, 'killpg', side_effect=PermissionError):
                    refuses(lambda: probe.signal_group(child.pid, 9))
            finally:
                os.killpg(child.pid, 9)
                child.wait(timeout=2)
        # Main's sanitized failure path must never expose subprocess diagnostics.
        result = subprocess.run([sys.executable, str(path), '--agy', '/nonexistent/agy'],
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 1 and result.stderr == probe.FAILURE + '\n'
    print('PASS: Antigravity malformed responses, RPC allowlist, sanitized failure, '
          'combined output/deadline limits and descendant cleanup')


if __name__ == '__main__':
    main()
