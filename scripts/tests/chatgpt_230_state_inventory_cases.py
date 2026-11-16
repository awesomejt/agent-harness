#!/usr/bin/env python3
"""Offline D099 created-state inventory cases; never runs OpenCode/sandbox."""
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_state_inventory as helper

SECRET = 'SECRET_UNTRUSTED_NAME'


def owned_roots(directory):
    work = Path(directory).resolve()
    for name in helper.ROOTS:
        (work / name).mkdir(mode=0o700)
    return work


def no_opens():
    def refuse(*_args, **_kwargs):
        raise AssertionError('inventory opened a file')
    return patch.object(os, 'open', refuse), patch.object(builtins, 'open', refuse)


def inventory_cases():
    with tempfile.TemporaryDirectory() as directory:
        work = owned_roots(directory)
        assert helper.settle(work) is None  # empty roots pass unchanged
        (work / 'CACHE' / 'bun' / '@t@').mkdir(parents=True)
        (work / 'CACHE' / 'bun' / '@t@' / 'entry').write_bytes(b'x' * 5000)
        (work / 'STATE' / SECRET).write_bytes(b'')
        (work / 'DATA' / 'link').symlink_to('/etc/hosts')
        opened, built = no_opens()
        with opened, built:
            try:
                helper.settle(work)
                raise AssertionError('created state accepted')
            except helper.StateCreated as error:
                assert str(error) == 'state-created'
                summary = error.summary
        text = json.dumps(summary)
        assert SECRET not in text and '/etc/hosts' not in text
        assert not summary['truncated'] and summary['unreadable_roots'] == []
        assert summary['entries'] == [
            {'root': 'DATA', 'depth': 1, 'type': 'LINK', 'name': helper.label('link')},
            {'root': 'CACHE', 'depth': 1, 'type': 'DIR', 'name': 'N:bun'},
            {'root': 'CACHE', 'depth': 2, 'type': 'DIR', 'name': 'N:@t@'},
            {'root': 'CACHE', 'depth': 3, 'type': 'FILE', 'name': helper.label('entry'), 'size': 'LE_1M'},
            {'root': 'STATE', 'depth': 1, 'type': 'FILE', 'name': helper.label(SECRET), 'size': 'ZERO'},
        ], summary['entries']
        # Unknown names are digests a hypothesis can be checked against offline.
        assert helper.label(SECRET) == 'H:' + hashlib.sha256(SECRET.encode()).hexdigest()[:16]


def limit_cases():
    with tempfile.TemporaryDirectory() as directory:
        work = owned_roots(directory)
        deep = work / 'CONFIG'
        for i in range(helper.MAX_DEPTH + 2):
            deep = deep / ('d' + str(i))
        deep.mkdir(parents=True)
        summary = helper.inventory(work)
        assert summary['truncated'] and max(e['depth'] for e in summary['entries']) == helper.MAX_DEPTH
    with tempfile.TemporaryDirectory() as directory:
        work = owned_roots(directory)
        for i in range(helper.MAX_ENTRIES + 5):
            (work / 'DATA' / ('f%03d' % i)).write_bytes(b'')
        summary = helper.inventory(work)
        assert summary['truncated'] and len(summary['entries']) == helper.MAX_ENTRIES
    with tempfile.TemporaryDirectory() as directory:
        work = owned_roots(directory)
        (work / 'STATE').rmdir()
        (work / 'STATE').symlink_to(work / 'DATA')
        try:
            helper.inventory(work)
            raise AssertionError('linked root accepted')
        except helper.Refusal as error:
            assert str(error) == 'owned-path'


def unreadable_cases():
    """Unreadable created state is recorded, never escalated to a generic control-gate refusal."""
    with tempfile.TemporaryDirectory() as directory:
        work = owned_roots(directory)
        locked = work / 'CACHE' / 'bun'
        (locked / 'hidden').mkdir(parents=True)
        root = work / 'STATE'
        (root / 'inner').mkdir()
        try:
            locked.chmod(0)
            try:
                helper.settle(work)
                raise AssertionError('created state accepted')
            except helper.StateCreated as error:
                summary = error.summary
            assert summary['entries'] == [
                {'root': 'CACHE', 'depth': 1, 'type': 'DIR', 'name': 'N:bun', 'unreadable': True},
                {'root': 'STATE', 'depth': 1, 'type': 'DIR', 'name': helper.label('inner')},
            ], summary['entries']
            # A whole root made unreadable is reported, and is not provably empty.
            locked.chmod(0o700)
            locked.joinpath('hidden').rmdir(); locked.rmdir(); (root / 'inner').rmdir()
            root.chmod(0)
            try:
                helper.settle(work)
                raise AssertionError('unreadable root accepted as empty')
            except helper.StateCreated as error:
                assert error.summary == {'entries': [], 'truncated': False, 'unreadable_roots': ['STATE']}
        finally:
            for path in (locked, root):
                if path.exists():
                    path.chmod(0o700)


def pair_ordering():
    summary = {'entries': [{'root': 'CACHE', 'depth': 1, 'type': 'DIR', 'name': 'N:bun'}], 'truncated': False}
    output = io.StringIO()
    with patch.object(helper, 'run_case', side_effect=helper.StateCreated(summary)) as run, \
         patch('sys.stdout', output):
        try:
            helper.run_pair(Path('unused'))
            raise AssertionError('state-created accepted')
        except helper.StateCreated:
            pass
    assert run.call_count == 1 and run.call_args.args[1] is False  # denied leg never runs
    assert json.loads(output.getvalue()) == dict(listing='ALLOWED', state='CREATED', **summary)
    # Clean state proceeds to the D098 pair unchanged.
    with patch.object(helper, 'run_case', side_effect=[{'listing': 'ALLOWED', 'watch': 'COMPATIBLE', 'phases': 3},
                                                       {'listing': 'DENIED', 'watch': 'COMPATIBLE', 'phases': 3}]) as run, \
         patch('sys.stdout', io.StringIO()):
        helper.run_pair(Path('unused'))
        assert run.call_count == 2
    with patch.object(helper, 'run_case', side_effect=[{'watch': 'COMPATIBLE'}, {'watch': 'INCOMPATIBLE'}]), \
         patch('sys.stdout', io.StringIO()):
        try:
            helper.run_pair(Path('unused'))
            raise AssertionError('incompatible accepted')
        except helper.Refusal as error:
            assert str(error) == 'parent-watch-incompatible'


def print_after_cleanup():
    """The inventory is collected inside the root but printed only after its deletion."""
    seen = {}
    real = helper.inventory
    def collect(work):
        seen['work'] = work
        return real(work)
    def fake_case(_executable, _denied):
        with tempfile.TemporaryDirectory() as directory:
            work = owned_roots(directory)
            (work / 'CACHE' / 'bun').mkdir()
            helper.settle(work)
    printed = []
    def record(*_args, **_kwargs):
        printed.append(seen['work'].exists())
    with patch.object(helper, 'inventory', side_effect=collect), \
         patch.object(helper, 'run_case', side_effect=fake_case), patch('builtins.print', record):
        try:
            helper.run_pair(Path('unused'))
        except helper.StateCreated:
            pass
    assert printed == [False]


def entry_sanitizes():
    errors = io.StringIO()
    with patch.object(helper, 'main', side_effect=helper.StateCreated({'entries': [], 'truncated': False})), \
         patch('sys.stdout', io.StringIO()), patch('sys.stderr', errors):
        assert helper.entry() == 1
    assert errors.getvalue().strip() == 'REFUSED: state-created'
    errors = io.StringIO()
    with patch.object(helper, 'main', side_effect=RuntimeError(SECRET)), \
         patch('sys.stdout', io.StringIO()), patch('sys.stderr', errors):
        assert helper.entry() == 1
    assert SECRET not in errors.getvalue()


def main():
    inventory_cases()
    limit_cases()
    unreadable_cases()
    pair_ordering()
    print_after_cleanup()
    entry_sanitizes()
    print('PASS: state inventory metadata-only/no-open, digest labels, limits, owned roots, '
          'print-after-cleanup and stop-before-denied ordering')


if __name__ == '__main__':
    main()
