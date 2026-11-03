#!/usr/bin/env python3
"""P3.3 local-first coordinator fixtures (D034). No model traffic. Build target/debug/ah first."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'


class Listener:
    """Reachable LiteLLM stand-in: records connections and any bytes received."""
    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(16)
        self.connections = 0
        self.received = b''
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            self.connections += 1
            conn.settimeout(2)
            try:
                while chunk := conn.recv(4096):
                    self.received += chunk
            except OSError:
                pass
            conn.close()

    @property
    def endpoint(self):
        return f'http://127.0.0.1:{self.sock.getsockname()[1]}/v1'


def closed_endpoint():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return f'http://127.0.0.1:{s.getsockname()[1]}/v1'


def blackholed(address='10.255.255.1'):
    """True when a SYN to the address neither connects nor fails quickly."""
    with socket.socket() as s:
        s.settimeout(1)
        try:
            s.connect((address, 4000))
        except socket.timeout:
            return True
        except OSError:
            return False
    return False


def check(case, expected, routes, endpoint, *, extra=(), env_drop=(), timeout='15', signal_after=None):
    with tempfile.TemporaryDirectory(prefix='ah-local-first-') as d:
        base = Path(d).resolve()
        (base/'opencode').symlink_to(FAKE)
        (base/'case').write_text(case)
        (base/'track-runtime-home').touch()
        (base/'user.txt').write_bytes(b'preserve dirty user content')
        cfg = dict(version=1, mode='local-first', model='group:coder',
                   litellm=dict(api_base=endpoint, api_key_env='TEST_KEY', groups=dict(coder='fixture')),
                   native=dict(target='opencode', model='fixture', api_key_env='NATIVE_KEY'))
        (base/'ah.json').write_text(json.dumps(cfg))
        env = {**os.environ, 'PATH': str(base)+':'+os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'NATIVE_KEY': 'SECRET_SENTINEL',
               'OPENCODE_API_KEY': 'poison', 'OPENCODE_CONFIG_CONTENT': 'poison', 'ANTHROPIC_API_KEY': 'poison'}
        for name in env_drop:
            env.pop(name)
        args = [str(BINARY), 'single', 'Task', '--project', str(base), '--timeout-secs', timeout, *extra]
        p = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if signal_after is not None:
            time.sleep(signal_after)
            p.send_signal(signal.SIGINT)
        out, err = p.communicate(timeout=40)
        assert p.returncode == expected, (case, p.returncode, err)
        assert 'SECRET_SENTINEL' not in out+err and 'poison' not in out+err, case
        launched = (base/'launch-routes').read_text().split() if (base/'launch-routes').exists() else []
        assert launched == routes, (case, launched, err)
        homes = (base/'runtime-homes').read_text().split() if (base/'runtime-homes').exists() else []
        assert all(not Path(h).exists() for h in homes), (case, homes)
        assert (base/'user.txt').read_bytes() == b'preserve dirty user content'
        local = 'local' in routes
        fell_back = 'attempt=2 fallback from attempt=1' in err
        if '--preview' not in extra and expected != 2:
            assert 'attempt=1 local-first LiteLLM reachability check' in err, err
        if fell_back:
            # The local attempt never launched: no runtime state, no project writes.
            assert 'attempt=1 LiteLLM endpoint unreachable before submission' in err, err
            assert 'fallback=attempt 2 (native)' in err, err
            assert not (base/'opencode.json').exists() and not (base/'.ah-opencode-owner.json').exists(), case
            assert 'local' not in launched, case
        if local:
            assert not fell_back and 'attempt=2' not in err, (case, err)
            assert 'fallback not eligible after the reachability check' in err, err
        print('PASS', case, expected, launched, flush=True)
        return err


listener = Listener()
reachable = listener.endpoint
unreachable = closed_endpoint()

# Reachable LiteLLM: local attempt only; every later outcome is final.
check('success', 0, ['local'], reachable)
check('session-model', 1, ['local'], reachable)
check('rpc-error', 4, ['local'], reachable)
check('version', 2, [], reachable)
check('success', 2, [], reachable, extra=['--no-sync'])  # static plan rejects before the check
assert listener.connections >= 4 and listener.received == b'', (listener.connections, listener.received)

# Unreachable before launch: exactly one native attempt with the same constraints.
err = check('success', 0, ['native'], unreachable)
assert 'attempt=2 local-first fallback via OpenCode 1.18.30; model opencode/fixture' in err, err
check('read', 0, ['native'], unreachable, extra=['--permissions', 'trusted'])
check('success', 0, ['native'], 'http://ah-unresolvable.invalid:4000/v1')
check('rpc-error', 4, ['native'], unreachable)
check('session-model', 1, ['native'], unreachable)
check('version', 2, [], unreachable)  # native preflight failure ends the run; no further attempt
check('cancel-deadline', 3, ['native'], unreachable, timeout='1')

# Static validation and preview precede any network contact.
before = listener.connections
check('success', 2, [], reachable, env_drop=['NATIVE_KEY'])
check('success', 2, [], reachable, env_drop=['TEST_KEY'])
check('success', 0, [], reachable, extra=['--preview'])
assert listener.connections == before, 'preview or invalid input contacted LiteLLM'

if blackholed():
    check('success', 3, [], 'http://10.255.255.1:4000/v1', signal_after=1)
    check('success', 3, [], 'http://10.255.255.1:4000/v1', timeout='2')
    print('PASS reachability-check interrupt/deadline stop without fallback')
else:
    print('SKIP interrupt/deadline during reachability check: 10.255.255.1 is not blackholed on this network')
print('PASS local-first coordinator fixtures')
