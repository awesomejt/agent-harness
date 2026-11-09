#!/usr/bin/env python3
"""Offline protocol/refusal/lifecycle checks; never launches installed Pi."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'experiments/pi_feasibility.py'
spec = importlib.util.spec_from_file_location('pi_probe', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
REPORT = {'type': 'ah_inventory', 'active': [], 'all': [], 'mcp': [], 'skills': [], 'templates': [], 'sentinelLoaded': False, 'sentinels': []}
STATE = {'isStreaming': False, 'isCompacting': False, 'autoCompactionEnabled': False,
         'messageCount': 0, 'pendingMessageCount': 0, 'model': {
             'provider': 'ah-feasibility', 'id': 'ah-no-inference',
             'baseUrl': 'http://127.0.0.1:9/v1', 'api': 'openai-completions'}}
VALID = [{'type': 'response', 'id': ident, 'command': command, 'success': True}
         for ident, command in probe.COMMANDS]
VALID[-1]['data'] = STATE


def refuses(callback):
    try:
        callback()
    except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        return
    raise AssertionError('unsafe input accepted')


def encode(records):
    return b'\n'.join(json.dumps(record).encode() for record in records)


def validate(records=VALID, report=REPORT):
    return probe.validate(encode(records), encode([report]))


def main():
    validate()
    controls = {'retryEnabled': False, 'compactionEnabled': False, 'providerRetries': 0,
                'settingsSentinel': 'private', 'keySource': 'environment',
                'authOk': True, 'authOverrides': False,
                'available': ['ah-feasibility/ah-no-inference']}
    probe.validate_controls({'controls': controls})
    for key, value in [('retryEnabled', True), ('compactionEnabled', True),
                       ('providerRetries', False), ('providerRetries', 7),
                       ('settingsSentinel', 'project'), ('keySource', 'stored'),
                       ('keySource', 'unset'), ('keySource', 'unexpected'),
                       ('authOk', False), ('authOverrides', True),
                       ('available', ['unexpected/model'])]:
        refuses(lambda: probe.validate_controls({'controls': {**controls, key: value}}))
    for report in [None, [], {}, {'controls': None}]:
        refuses(lambda: probe.validate_controls(report))
    probe.validate_controls({'controls': {**controls, 'keySource': 'stored'}}, stored_auth=True)
    probe.validate_controls({'controls': {**controls, 'retryEnabled': True,
        'compactionEnabled': True, 'providerRetries': 7, 'settingsSentinel': 'project'}},
        project_trusted=True)
    refuses(lambda: probe.unique_object([('id', 'first'), ('id', 'second')]))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'file').write_text('one')
        original = probe.tree_hash(root)
        (root / 'file').write_text('two')
        assert probe.tree_hash(root) != original
        (root / 'link').symlink_to('file')
        linked = probe.tree_hash(root)
        (root / 'link').unlink()
        (root / 'link').symlink_to('other')
        assert probe.tree_hash(root) != linked
    for records in [[], VALID[:2], VALID + VALID[:1], VALID[::-1], [None, *VALID[1:]]]:
        refuses(lambda: validate(records))
    for key, value in [('id', 'other'), ('type', 'event'), ('command', 'prompt'),
                       ('success', 1), ('error', 'synthetic')]:
        records = copy.deepcopy(VALID)
        records[0][key] = value
        refuses(lambda: validate(records))
    for key, value in [('isStreaming', True), ('isCompacting', True),
                       ('autoCompactionEnabled', True), ('messageCount', False),
                       ('pendingMessageCount', 1), ('sessionFile', 'synthetic')]:
        records = copy.deepcopy(VALID)
        records[-1]['data'][key] = value
        refuses(lambda: validate(records))
    for key in STATE['model']:
        records = copy.deepcopy(VALID)
        records[-1]['data']['model'][key] = 'wrong-route'
        refuses(lambda: validate(records))
    for key in ['active', 'all', 'mcp', 'skills', 'templates']:
        refuses(lambda: validate(report={**REPORT, key: ['unexpected']}))
    refuses(lambda: validate(report={**REPORT, 'sentinelLoaded': True}))
    probe.validate(encode(VALID), encode([{**REPORT, 'skills': ['skill:inert'],
                   'templates': ['inert']}]), resources_loaded=True)
    refuses(lambda: probe.validate(encode(VALID), encode([REPORT]), resources_loaded=True))
    unsafe_records = copy.deepcopy(VALID)
    unsafe_records[-1]['data']['autoCompactionEnabled'] = True
    unsafe_report = {**REPORT, 'sentinelLoaded': True, 'sentinels': ['AH_UNPLANNED_SYSTEM']}
    refuses(lambda: probe.validate(encode(unsafe_records), encode([unsafe_report])))
    probe.validate(encode(unsafe_records), encode([unsafe_report]), project_trusted=True)
    for sentinels in [[], ['AH_UNPLANNED_PROJECT'], ['AH_UNPLANNED_SYSTEM', 'AH_UNPLANNED_HOME']]:
        refuses(lambda: probe.validate(encode(unsafe_records),
            encode([{**unsafe_report, 'sentinels': sentinels}]), project_trusted=True))
    refuses(lambda: validate(report={**REPORT, 'sentinels': ['AH_UNPLANNED_SYSTEM']}))
    for out, err in [(b'not-json', encode([REPORT])), (encode(VALID), b''),
                     (encode(VALID), encode([REPORT, REPORT]))]:
        refuses(lambda: probe.validate(out, err))
    assert [r['type'] for r in map(json.loads, probe.requests().splitlines())] == [
        'set_auto_compaction', 'set_auto_retry', 'get_state']
    with patch.object(probe.subprocess, 'Popen') as popen:
        for data in [b'{}', b'{"type":"prompt"}\n', probe.requests() + b'\n']:
            refuses(lambda: probe.capture(['never-launch'], '.', {}, data))
        popen.assert_not_called()
    with tempfile.TemporaryDirectory(prefix='ah-pi-offline-') as directory:
        root = Path(directory)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(root)}
        out, err = probe.capture([sys.executable, '-c',
            'import sys; print(sys.stdin.read())'], root, env, probe.requests())
        assert not err and out.strip() == probe.requests().strip()
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
            result = subprocess.run(['ps', '-o', 'stat=', '-p', pidfile.read_text()],
                                    capture_output=True, text=True, timeout=2)
            assert result.returncode != 0 or result.stdout.strip().startswith('Z')
        result = subprocess.run([sys.executable, '-B', str(path), '--release', str(root),
                                 '--node', '/nonexistent/node'], capture_output=True, text=True, timeout=5)
        assert result.returncode == 1 and result.stderr == probe.FAILURE + '\n'
    print('PASS: Pi correlated protocol, inventories, route refusals, no-prompt allowlist, '
          'sanitized failures, output/deadline bounds and descendant cleanup')


if __name__ == '__main__':
    main()
