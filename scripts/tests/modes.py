#!/usr/bin/env python3
"""P3.4 three-mode boundary matrix (AC02/AC03). No model traffic. Build target/debug/ah first.

Every scenario runs in every mode against one combined config (litellm + native)
and against a reachable and an unreachable LiteLLM endpoint. Assertions use
effective behavior: launched routes, runtime inputs, endpoint contact, attempts,
project writes and exit status, not the selected mode value.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'
MODES = ['local-only', 'cloud-only', 'local-first']
DECOYS = ['claude', 'codex', 'grok', 'gemini', 'pi']
RUNTIME_ENV = {'HOME', 'PATH', 'OPENCODE_CONFIG_CONTENT',
               *(f'XDG_{k}_HOME' for k in ['CONFIG', 'DATA', 'CACHE', 'STATE']),
               *(f'OPENCODE_DISABLE_{k}' for k in ['MODELS_FETCH', 'AUTOUPDATE', 'PROJECT_CONFIG'])}

# Exit status is route-independent: the fake behaves identically on both routes.
SCENARIOS = {
    'success': 0,
    # Inherited default/helper/subagent/provider/permission choices.
    'route': 2, 'inherit-agent': 2, 'inherit-subagent': 2, 'inherit-mode': 2,
    'inherit-provider': 2, 'widened': 2, 'agent-widened': 2, 'subagent-widened': 2, 'agent-model': 2,
    'project-source': 2, 'version': 2,
    # Failures after launch are final in every mode.
    'session-model': 1, 'known-failure': 1, 'backend-cancelled': 3, 'cancel-deadline': 3,
    # Ambiguous side effects stop with uncertainty and are never replayed.
    'rpc-error': 4, 'eof': 4, 'deny-completed': 4, 'unexpected-write': 4, 'home-cleanup-failure': 4,
}
TRUSTED = {'unexpected-write'}
UNPROMPTED = {'session-model'}


class Listener:
    """LiteLLM stand-in and discovery trap: counts connections and received bytes."""
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

    def settle(self, before, expected):
        until = time.monotonic() + 2
        while self.connections - before < expected and time.monotonic() < until:
            time.sleep(.02)
        time.sleep(.05)
        return self.connections - before


def closed_endpoint():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return f'http://127.0.0.1:{s.getsockname()[1]}/v1'


listener = Listener()
REACHABLE = listener.endpoint
# Ambient endpoint variables point at a separate trap, so a configured stand-in
# can never mask an ambient-URL leak.
ambient = Listener()
AMBIENT = ambient.endpoint
UNREACHABLE = closed_endpoint()


def config(mode, endpoint, **overrides):
    cfg = dict(version=1, mode=mode, model='group:coder',
               litellm=dict(api_base=endpoint, api_key_env='TEST_KEY', groups=dict(coder='fixture')),
               native=dict(target='opencode', model='fixture', api_key_env='NATIVE_KEY'))
    cfg.update(overrides)
    return {k: v for k, v in cfg.items() if v is not None}


def run(case, cfg, *, extra=(), env_drop=(), timeout='15'):
    """Run once in a disposable project; return (exit, stderr, launched, records, base-state)."""
    with tempfile.TemporaryDirectory(prefix='ah-modes-') as d:
        base = Path(d).resolve()
        (base/'opencode').symlink_to(FAKE)
        for name in DECOYS:
            (base/name).write_text('#!/bin/sh\ntouch "$(dirname "$0")/cloud-native-launched"\nexit 99\n')
            (base/name).chmod(0o755)
        for marker in ['track-runtime-home', 'track-config']:
            (base/marker).touch()
        (base/'case').write_text(case)
        (base/'user.txt').write_bytes(b'preserve dirty user content')
        (base/'ah.json').write_text(json.dumps(cfg))
        env = {**os.environ, 'PATH': str(base)+':'+os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'NATIVE_KEY': 'SECRET_SENTINEL',
               # Ambient credentials/endpoints must never become runtime inputs.
               'OPENCODE_API_KEY': 'poison', 'OPENCODE_CONFIG_CONTENT': 'poison', 'OPENCODE_CONFIG': 'poison',
               'ANTHROPIC_API_KEY': 'poison', 'OPENAI_API_KEY': 'poison', 'LITELLM_API_KEY': 'poison',
               'OPENAI_BASE_URL': AMBIENT, 'LITELLM_API_BASE': AMBIENT}
        for name in env_drop:
            env.pop(name)
        args = [str(BINARY), 'single', 'Task', '--project', str(base), '--timeout-secs', timeout, *extra]
        p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=40)
        homes = (base/'runtime-homes').read_text().split() if (base/'runtime-homes').exists() else []
        retained = [h for h in dict.fromkeys(homes) if Path(h).exists()]
        for h in retained:
            Path(h).chmod(0o700)
            shutil.rmtree(h)
        assert 'SECRET_SENTINEL' not in p.stdout+p.stderr and 'poison' not in p.stdout+p.stderr, (case, p.stderr)
        assert not (base/'cloud-native-launched').exists(), case
        assert (base/'user.txt').read_bytes() == b'preserve dirty user content', case
        state = dict(
            launched=(base/'launch-routes').read_text().split() if (base/'launch-routes').exists() else [],
            records=[json.loads(line) for line in (base/'runtime-config.jsonl').read_text().splitlines()]
            if (base/'runtime-config.jsonl').exists() else [],
            prompted=(base/'prompted').exists(),
            managed=(base/'opencode.json').exists() or (base/'.ah-opencode-owner.json').exists(),
            retained=retained)
        return p.returncode, p.stderr, state


ROUTING_KEYS = {'model', 'default_agent', 'update', 'share', 'permissions', 'policies', 'agents',
                'instructions', 'mcp', 'plugins', 'providers'}


def assert_records(records, route, endpoint, key, trusted=False):
    """Each runtime invocation receives only its route's routing and credential."""
    for record in records:
        cfg = record['config']
        # The fake's own interpreter adds PEP 538 locale coercion and the macOS
        # CoreFoundation encoding; neither comes from the harness.
        names = set(record['env']) - {'LC_CTYPE', '__CF_USER_TEXT_ENCODING'}
        assert names == RUNTIME_ENV | {key}, (route, sorted(names ^ (RUNTIME_ENV | {key})))
        # Exact outbound shape: no agent/mode/helper entries or other keys are sent.
        assert set(cfg) == ROUTING_KEYS, (route, sorted(set(cfg) ^ ROUTING_KEYS))
        rules = cfg['permissions']
        assert rules[0] == dict(action='*', resource='*', effect='deny'), rules
        assert all(r['resource'] == '*' and r['effect'] in ('deny', 'ask') for r in rules), rules
        asks = {r['action'] for r in rules if r['effect'] == 'ask'}
        assert asks == ({'read', 'glob', 'grep', 'edit', 'shell', 'external_directory'} if trusted else set()), rules
        provider = 'opencode' if route == 'native' else 'ah-litellm'
        assert cfg['policies'] == [dict(action='provider.use', resource='*', effect='deny'),
                                   dict(action='provider.use', resource=provider, effect='allow')], cfg['policies']
        assert cfg['model'] == dict(providerID=provider, model='fixture'), cfg['model']
        assert cfg['agents'] == {'title': {'model': cfg['model']}}, cfg['agents']
        text = json.dumps(cfg)
        assert 'poison' not in text and AMBIENT not in text, (route, text)
        assert REACHABLE not in text or (route == 'local' and endpoint == REACHABLE), (route, text)
        if route == 'native':
            assert cfg['providers'] == {}, cfg
            assert 'ah-litellm' not in text and endpoint not in text, cfg
        else:
            assert list(cfg['providers']) == ['ah-litellm'], cfg
            assert cfg['providers']['ah-litellm']['settings'] == dict(apiKey='{env:AH_RUNTIME_API_KEY}', baseURL=endpoint), cfg
        assert cfg['plugins'] == [] and cfg['mcp'] == {} and cfg['default_agent'] == 'build', cfg
        # Matrix projects have no AGENTS.md, so no instructions are named (D040).
        assert cfg['instructions'] == [], cfg
        assert cfg['update'] == 'disable' and cfg['share'] == 'disabled', cfg


def expected_route(mode, endpoint):
    if mode == 'local-only':
        return 'local'
    if mode == 'cloud-only':
        return 'native'
    return 'local' if endpoint == REACHABLE else 'native'


count = 0
for mode in MODES:
    for endpoint in [REACHABLE, UNREACHABLE]:
        route = expected_route(mode, endpoint)
        fell_back = mode == 'local-first' and endpoint == UNREACHABLE
        probes = 1 if mode == 'local-first' and endpoint == REACHABLE else 0
        for case, expected in SCENARIOS.items():
            before = listener.connections
            extra = ['--permissions', 'trusted'] if case in TRUSTED else []
            code, err, s = run(case, config(mode, endpoint), extra=extra,
                               timeout='1' if case == 'cancel-deadline' else '15')
            where = (mode, endpoint == REACHABLE, case)
            assert code == expected, (*where, code, err)
            # Forbidden launches/requests: one route, one launch, no discovery.
            assert s['launched'] == ([route] if expected != 2 else []), (*where, s['launched'], err)
            assert {r for r in s['launched']} <= {route} and len(s['launched']) <= 1, where
            assert s['records'], where  # preflight always reaches the runtime
            assert_records(s['records'], route, endpoint, 'OPENCODE_API_KEY' if route == 'native' else 'AH_RUNTIME_API_KEY',
                           trusted=case in TRUSTED)
            assert listener.settle(before, probes) == probes, (*where, listener.connections - before)
            assert listener.received == b'', listener.received
            # Retry bounds: attempt 2 only for the eligible local-first fallback; never attempt 3.
            assert ('attempt=2' in err) == fell_back and 'attempt=3' not in err, (*where, err)
            if mode == 'local-first':
                assert 'attempt=1 local-first LiteLLM reachability check' in err, err
                assert ('fallback=attempt 2 (native)' in err) == fell_back, err
            else:
                assert 'reachability' not in err and 'no automatic retry or fallback' in err, (*where, err)
            # Uncertainty, prompts and project writes.
            assert s['prompted'] == (expected != 2 and case not in UNPROMPTED), (*where, s['prompted'])
            assert s['managed'] == (route == 'local' and expected != 2), (*where, s['managed'])
            assert ('uncertain completion or cleanup' in err) == (expected == 4), (*where, err)
            assert bool(s['retained']) == (case == 'home-cleanup-failure'), (*where, s['retained'])
            count += 1
        print('PASS', mode, 'reachable' if endpoint == REACHABLE else 'unreachable', len(SCENARIOS), 'scenarios', flush=True)

# --mode overrides the configured mode with identical effective behavior.
for configured, selected in [('cloud-only', 'local-only'), ('local-only', 'cloud-only'),
                             ('local-only', 'local-first'), ('cloud-only', 'local-first')]:
    for endpoint in [REACHABLE, UNREACHABLE]:
        for case, expected in [('success', 0), ('inherit-agent', 2)]:
            before = listener.connections
            code, err, s = run(case, config(configured, endpoint), extra=['--mode', selected])
            route = expected_route(selected, endpoint)
            probes = 1 if selected == 'local-first' and endpoint == REACHABLE else 0
            where = (configured, selected, endpoint == REACHABLE, case)
            assert code == expected and s['launched'] == ([route] if expected == 0 else []), (*where, code, s['launched'], err)
            assert ('attempt=2' in err) == (selected == 'local-first' and endpoint == UNREACHABLE), (*where, err)
            assert_records(s['records'], route, endpoint, 'OPENCODE_API_KEY' if route == 'native' else 'AH_RUNTIME_API_KEY')
            assert listener.settle(before, probes) == probes, where
            count += 1
print('PASS --mode override selects the same effective routes', flush=True)

# --no-sync validates effective routing too; a fresh project has nothing to reuse locally.
for mode in MODES:
    for case, expected in [('success', 0), ('inherit-agent', 2), ('route', 2)]:
        before = listener.connections
        code, err, s = run(case, config(mode, UNREACHABLE), extra=['--no-sync'])
        if mode == 'cloud-only':
            assert code == expected and s['launched'] == (['native'] if expected == 0 else []), (mode, case, code, err)
            assert_records(s['records'], 'native', UNREACHABLE, 'OPENCODE_API_KEY')
        else:
            # The static plan rejects before any probe, runtime or fallback.
            assert code == 2 and s['launched'] == [] and s['records'] == [], (mode, case, code, err)
        assert not s['managed'] and listener.settle(before, 0) == 0, (mode, case)
        count += 1
print('PASS --no-sync keeps effective validation in every mode', flush=True)

# D052: a Claude fallback is valid without a native key. When LiteLLM is
# reachable it still runs only OpenCode; all decoy native CLIs stay untouched.
before = listener.connections
code, err, s = run('success', config('local-first', REACHABLE,
                                    native=dict(target='claude', model='sonnet')),
                   env_drop=['NATIVE_KEY'])
assert code == 0 and s['launched'] == ['local'], (code, err)
assert_records(s['records'], 'local', REACHABLE, 'AH_RUNTIME_API_KEY')
assert listener.settle(before, 1) == 1
count += 1
print('PASS Claude fallback selection retains the OpenCode primary without a native key', flush=True)

# Invalid fallback/route configuration rejects before any runtime, probe or input.
native = dict(target='opencode', model='fixture', api_key_env='NATIVE_KEY')
REQUIRES = 'local-first requires litellm and native configuration'
KEY = 'set the environment variable named by the selected route api_key_env'
MODE = 'mode must be local-only, cloud-only or local-first'
invalid = [
    ('local-first without native', config('local-first', REACHABLE, native=None), (), (), REQUIRES),
    ('local-first without litellm', config('local-first', REACHABLE, litellm=None, model='fixture'), (), (), REQUIRES),
    ('local-first native target', config('local-first', REACHABLE, native={**native, 'target': 'codex'}), (), (), 'native target must be opencode'),
    ('local-first native group model', config('local-first', REACHABLE, native={**native, 'model': 'group:coder'}), (), (), 'model must be a 1–128 byte identifier'),
    ('local-first native proxy field', config('local-first', REACHABLE, native={**native, 'api_base': REACHABLE}), (), (), 'strict version-1 JSON schema'),
    ('local-first native key missing', config('local-first', REACHABLE), (), ['NATIVE_KEY'], KEY),
    ('local-first local key missing', config('local-first', REACHABLE), (), ['TEST_KEY'], KEY),
    ('local-first undefined group', config('local-first', REACHABLE), ['--model', 'group:missing'], (), 'not defined in litellm.groups'),
    ('override to local-first without native', config('local-only', REACHABLE, native=None), ['--mode', 'local-first'], (), REQUIRES),
    ('cloud-only group model', config('cloud-only', REACHABLE), ['--model', 'group:coder'], (), 'model groups apply only to the LiteLLM route'),
    ('cloud-only native key missing', config('cloud-only', REACHABLE), (), ['NATIVE_KEY'], KEY),
    ('local-only local key missing', config('local-only', REACHABLE), (), ['TEST_KEY'], KEY),
    ('unsupported mode flag', config('local-only', REACHABLE), ['--mode', 'cloud-first'], (), MODE),
    ('unsupported mode config', config('native-first', REACHABLE), (), (), MODE),
]
for name, cfg, extra, drop, reason in invalid:
    before = listener.connections
    code, err, s = run('success', cfg, extra=extra, env_drop=drop)
    assert code == 2 and reason in err, (name, code, err)
    assert s['launched'] == [] and s['records'] == [] and not s['managed'], (name, s)
    assert listener.settle(before, 0) == 0, name
    assert 'attempt=' not in err, (name, err)
    count += 1
print('PASS', len(invalid), 'invalid route/fallback configurations reject before launch or contact', flush=True)

assert listener.received == b''
assert ambient.connections == 0 and ambient.received == b'', 'ambient endpoint contacted'
print(f'PASS {count} mode-matrix cases; forbidden launches/requests absent; uncertainty never replayed')
