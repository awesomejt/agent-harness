#!/usr/bin/env python3
"""Offline D100 cache-control cases; never runs OpenCode/sandbox."""
import inspect
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_cache_control as helper
import chatgpt_230_state_inventory as inventory


def env_cases():
    base = {'HOME': '/h', 'XDG_CACHE_HOME': '/c'}
    assert helper.child_env(base) == dict(base, BUN_BE_BUN='1', BUN_RUNTIME_TRANSPILER_CACHE_PATH='0')
    assert base == {'HOME': '/h', 'XDG_CACHE_HOME': '/c'}  # caller env untouched
    assert helper.CACHE_CONTROL == {'BUN_RUNTIME_TRANSPILER_CACHE_PATH': '0'}
    try:
        helper.child_env(dict(base, BUN_RUNTIME_TRANSPILER_CACHE_PATH='/elsewhere'))
        raise AssertionError('colliding cache path accepted')
    except helper.Refusal as error:
        assert str(error) == 'env-collision'


def mirror_case():
    """run_case may differ from the merged D099 run_case only in the child environment."""
    def body(function, renames):
        lines = []
        for line in inspect.getsource(function).splitlines():
            if line.strip().startswith('#'):
                continue
            for old, new in renames:
                line = line.replace(old, new)
            lines.append(line)
        return lines
    ours = body(helper.run_case, [('child_env(env)', "dict(env, BUN_BE_BUN='1')"),
                                  ('inventory.ROOTS', 'ROOTS'), ('inventory.settle', 'settle')])
    theirs = body(inventory.run_case, [])
    assert ours == theirs, [pair for pair in zip(ours, theirs) if pair[0] != pair[1]]
    assert inspect.getsource(helper.run_case).count('child_env(env)') == 1


def pair_cases():
    summary = {'entries': [{'root': 'CACHE', 'depth': 1, 'type': 'DIR', 'name': 'N:bun'}],
               'truncated': False, 'unreadable_roots': []}
    output = io.StringIO()
    with patch.object(helper, 'run_case', side_effect=inventory.StateCreated(summary)) as run, \
         patch('sys.stdout', output):
        try:
            helper.run_pair(Path('unused'))
            raise AssertionError('state-created accepted')
        except inventory.StateCreated:
            pass
    assert run.call_count == 1 and run.call_args.args[1] is False  # denied leg never runs
    assert json.loads(output.getvalue()) == dict(listing='ALLOWED', state='CREATED', **summary)
    assert inventory.run_case.__module__ == 'chatgpt_230_state_inventory'  # restored after refusal
    clean = [{'listing': 'ALLOWED', 'watch': 'COMPATIBLE', 'phases': 3},
             {'listing': 'DENIED', 'watch': 'COMPATIBLE', 'phases': 3}]
    with patch.object(helper, 'run_case', side_effect=clean) as run, patch('sys.stdout', io.StringIO()):
        helper.run_pair(Path('unused'))
        assert [call.args[1] for call in run.call_args_list] == [False, True]
    incompatible = [{'watch': 'COMPATIBLE'}, {'watch': 'INCOMPATIBLE', 'stage': 'SYNC', 'code': 'EPERM'}]
    with patch.object(helper, 'run_case', side_effect=incompatible), patch('sys.stdout', io.StringIO()):
        try:
            helper.run_pair(Path('unused'))
            raise AssertionError('incompatible accepted')
        except helper.Refusal as error:
            assert str(error) == 'parent-watch-incompatible'
    assert inventory.run_case.__module__ == 'chatgpt_230_state_inventory'


def entry_sanitizes():
    errors = io.StringIO()
    with patch.object(helper, 'main', side_effect=RuntimeError('SECRET_UNTRUSTED')), \
         patch('sys.stdout', io.StringIO()), patch('sys.stderr', errors):
        assert helper.entry() == 1
    assert errors.getvalue().strip() == 'REFUSED: control-gate; raw diagnostics withheld'


def main():
    env_cases()
    mirror_case()
    pair_cases()
    entry_sanitizes()
    print('PASS: cache-control env/collision, D099 mirror, inventory/stop ordering and sanitization')


if __name__ == '__main__':
    main()
