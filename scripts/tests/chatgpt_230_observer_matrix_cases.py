#!/usr/bin/env python3
"""Offline D102 reduced-matrix cases; never runs OpenCode/sandbox."""
import ast
import inspect
import io
from pathlib import Path
import sys
import textwrap
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_observer as d094
import chatgpt_230_observer_matrix as helper


def merged_matrix():
    """Extract the literal row tuple from the merged D094 main() without running it."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(d094.main)))
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
    assert len(loops) == 1
    return ast.literal_eval(loops[0].iter)


def matrix_cases():
    assert helper.D094_MATRIX == merged_matrix()
    assert helper.RETIRED == frozenset({3})
    assert [number for number, _ in helper.ROWS] == [1, 2, 4, 5, 6]
    assert [row for _, row in helper.ROWS] == [r for i, r in enumerate(merged_matrix(), 1) if i != 3]
    # Case 3 is the only listing-denied row, so no retained row denies listing (D101 invariant).
    assert [i for i, r in enumerate(merged_matrix(), 1) if r[4]] == [3]
    assert not any(row[4] for _, row in helper.ROWS)
    # Case 6 stays the only ancestor-undenied positive control.
    assert [number for number, row in helper.ROWS if not row[3]] == [6]
    print('PASS: rows equal merged D094 literal minus case 3; no listing-denied row; case 6 control kept')


def reuse_cases():
    # No local replacement of the reviewed D094 pieces.
    for name in ('run_case', 'transport_controls', 'audit', 'SHA256', 'policy'):
        assert not hasattr(helper, name) or getattr(helper, name) is getattr(d094, name), name
    source = inspect.getsource(helper)
    for marker in ('BUN_', 'os.environ', 'import os', 'OPENCODE_', 'listing_denied=True', 'env['):
        assert marker not in source, marker
    print('PASS: merged D094 run_case/controls/pin reused; no child-environment or policy change')


def run_cases():
    calls = []

    def fake(executable, builtin, *row):
        calls.append(row)
        return {'row': row}
    output = io.StringIO()
    with patch.object(d094, 'run_case', side_effect=fake), patch('sys.stdout', output):
        cases = helper.run_matrix('exe', frozenset())
    assert calls == [row for _, row in helper.ROWS]
    assert [c['case'] for c in cases] == [1, 2, 4, 5, 6]
    lines = output.getvalue().splitlines()
    assert lines[:2] == ['START: disposable resource/inventory case 1', 'PASS: disposable resource/inventory case 1']
    assert 'case 3' not in output.getvalue()

    calls.clear()

    def stop_at_four(executable, builtin, *row):
        calls.append(row)
        if row == helper.D094_MATRIX[3]:
            raise d094.Refusal('warning')
        return {}
    output = io.StringIO()
    with patch.object(d094, 'run_case', side_effect=stop_at_four), patch('sys.stdout', output):
        try:
            helper.run_matrix('exe', frozenset())
            raise AssertionError('refusal swallowed')
        except d094.Refusal as error:
            assert str(error) == 'warning'
    assert calls == list(helper.D094_MATRIX[:2]) + [helper.D094_MATRIX[3]]  # 5 and 6 never start
    assert output.getvalue().splitlines()[-1] == 'START: disposable resource/inventory case 4'
    print('PASS: D094 order and labels; first refusal stops before later rows')


def order_cases():
    events = []
    with patch.object(sys, 'argv', ['x', '--source', '/unused']), \
         patch.object(d094, 'audit', side_effect=lambda _: events.append('audit') or
                      {'source_commit': 'c', 'plugins': {'ids': []}}), \
         patch.object(helper.shutil, 'which', return_value=None), \
         patch.object(d094, 'transport_controls', side_effect=lambda _: events.append('transport')), \
         patch.object(helper, 'run_matrix', side_effect=lambda *_: events.append('matrix') or []):
        try:
            helper.main()
            raise AssertionError('missing executable accepted')
        except Exception:
            pass
    assert events == ['audit'] or sys.platform != 'darwin'
    assert 'transport' not in events and 'matrix' not in events
    body = inspect.getsource(helper.main)
    assert body.index("'executable-pin'") < body.index('transport_controls') < body.index('run_matrix')
    print('PASS: source audit and executable pin precede controls; controls precede any case')


if __name__ == '__main__':
    matrix_cases()
    reuse_cases()
    run_cases()
    order_cases()
