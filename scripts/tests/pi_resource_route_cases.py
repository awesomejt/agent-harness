#!/usr/bin/env python3
"""Offline schema/refusal checks for Pi resource-route probe; never launches installed Pi."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pi_route', root / 'experiments/pi_resource_route.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
REPORT = {'type': 'ah_resource_route', 'providers': [], 'configured': ['ah-feasibility'],
          'registry': {'all': 1, 'available': 1, 'chat': 1, 'image': 0, 'classifier': 0},
          'tools': [], 'active': [], 'mcp': []}
STATE_LINE = {'type': 'response', 'id': 'inventory-state', 'command': 'get_state', 'success': True,
              'data': {'messageCount': 0, 'pendingMessageCount': 0,
                       'model': {'provider': 'ah-feasibility', 'id': 'ah-no-inference',
                                 'baseUrl': 'http://127.0.0.1:9/v1', 'api': 'openai-completions'}}}
INVENTORY = [
    {'type': 'response', 'id': 'disable-compaction', 'command': 'set_auto_compaction', 'success': True},
    {'type': 'response', 'id': 'disable-retry', 'command': 'set_auto_retry', 'success': True},
    STATE_LINE,
]


def refuses(callback):
    try:
        callback()
    except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        return
    raise AssertionError('unsafe input accepted')


def encode(records):
    return '\n'.join(json.dumps(record) for record in records).encode()


def validate_inventory(stdout=encode(INVENTORY), stderr=encode([REPORT])):
    probe.validate_inventory(stdout, stderr)


def main():
    validate_inventory()
    for key in ('providers', 'configured', 'registry', 'tools', 'mcp'):
        refuses(lambda key=key: validate_inventory(stderr=encode([{**REPORT, key: None}])))
    refuses(lambda: validate_inventory(stderr=encode([{**REPORT, 'type': 'ah_inventory'}])))
    refuses(lambda: validate_inventory(stderr=encode([{**REPORT,
        'registry': {**REPORT['registry'], 'available': 9}}])))
    refuses(lambda: validate_inventory(stderr=encode([{**REPORT, 'configured': ['unexpected']}])))
    bad_tool = {**REPORT, 'tools': [{'name': 'x', 'sourceInfo': {'path': '/secret'}}]}
    refuses(lambda: validate_inventory(stderr=encode([bad_tool])))
    adversarial_ok = encode([
        {'type': 'response', 'id': 'deny-prompt', 'command': 'prompt', 'success': True,
         'data': {'disposition': 'started'}},
        {'type': 'response', 'id': 'deny-bash', 'command': 'bash', 'success': False, 'error': 'denied'},
        {'type': 'response', 'id': 'post-adversarial', 'command': 'get_state', 'success': True,
         'data': {'messageCount': 0, 'pendingMessageCount': 0}},
    ]) + b'\nHarness blocked user bash\nHarness blocked provider request\n'
    with tempfile.TemporaryDirectory() as directory:
        marker = Path(directory) / 'marker'
        probe.validate_adversarial(adversarial_ok, b'', marker)
        refuses(lambda: probe.validate_adversarial(
            adversarial_ok.replace(b'Harness blocked user bash', b''), b'', marker))
        bad_state = {'type': 'response', 'id': 'post-adversarial', 'command': 'get_state',
                     'success': True, 'data': {'messageCount': 2, 'pendingMessageCount': 0}}
        hostile = encode([
            {'type': 'response', 'id': 'deny-prompt', 'command': 'prompt', 'success': True,
             'data': {'disposition': 'started'}},
            {'type': 'response', 'id': 'deny-bash', 'command': 'bash', 'success': False, 'error': 'denied'},
            bad_state,
        ]) + b'\n{"type":"extension_error","event":"before_provider_request"}\n'
        refuses(lambda: probe.validate_adversarial(hostile, b'Harness blocked user bash\n', marker))
    trap = encode([{'type': 'ah_http_trap', 'requests': [
        {'method': 'GET', 'path': '/v1/models', 'headers': ['authorization', 'host'],
         'authorizationSynthetic': True}]}])
    probe.validate_trap(trap)
    refuses(lambda: probe.validate_trap(encode([{'type': 'ah_http_trap', 'requests': [
        {'method': 'POST', 'path': '/v1/models', 'headers': ['authorization'],
         'authorizationSynthetic': True}]}])))
    refuses(lambda: probe.validate_trap(encode([{'type': 'ah_http_trap', 'requests': [
        {'method': 'GET', 'path': '/v1/models', 'headers': ['authorization'],
         'authorizationSynthetic': False}]}])))
    refuses(lambda: probe.validate_trap(encode([{'type': 'ah_http_trap', 'requests': []}])))
    assert probe.contained_profile(Path('/tmp/a'), Path.home(), 54321).count('localhost:54321') == 2
    with tempfile.TemporaryDirectory(prefix='ah-pi-route-offline-') as directory:
        scratch = Path(directory)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(scratch)}
        out, err = probe.bound_capture([sys.executable, '-c', 'import sys; print(sys.stdin.read())'],
                                       scratch, env, probe.inventory_requests())
        assert not err and out.strip() == probe.inventory_requests().strip()
        with patch.object(probe, 'LIMIT', 512):
            refuses(lambda: probe.bound_capture([sys.executable, '-c',
                'import sys; sys.stdout.write("x"*600)'], scratch, env))
        result = subprocess.run([sys.executable, '-B', str(root / 'experiments/pi_resource_route.py'),
                                 '--release', str(scratch), '--node', '/nonexistent/node'],
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 1 and result.stderr == probe.FAILURE + '\n'
    print('PASS: Pi resource inventory schema, adversarial refusal rules, trap shape and capture bounds')


if __name__ == '__main__':
    main()
