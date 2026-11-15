#!/usr/bin/env python3
"""Offline source-audit refusal cases; no OpenCode process, credentials or network."""
import hashlib
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_source_audit as helper


def rejects(action):
    try:
        action()
    except (RuntimeError, OSError, ValueError):
        return
    raise AssertionError('unsafe source accepted')


def main():
    assert helper.websearch_registrations('const x = {id: "unrelated"}') == []
    assert helper.websearch_registrations('WebSearchProvider.register(ctx, { id: "exa", name: "Exa" })') == ['exa']
    for call in ('register(ctx, { id: variable, name: "x" })',
                 'register(ctx, { name: "x", id: "exa" })',
                 'register(other, { id: "exa", name: "x" })'):
        rejects(lambda: helper.websearch_registrations('WebSearchProvider.' + call))
    rejects(lambda: helper.websearch_registrations(
        'WebSearchProvider.register(ctx, { id: "exa", }); WebSearchProvider.register(ctx, { id: "exa", })'))
    with tempfile.TemporaryDirectory(prefix='ah-230-source-cases-') as directory:
        packages = Path(directory).resolve()
        path = packages / 'fixture.ts'
        path.write_bytes(b'public source')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        helper.verify_files(packages, {'fixture.ts': digest})
        path.write_bytes(b'changed')
        rejects(lambda: helper.verify_files(packages, {'fixture.ts': digest}))
        path.unlink()
        rejects(lambda: helper.verify_files(packages, {'fixture.ts': digest}))
        target = packages / 'target.ts'
        target.write_bytes(b'public source')
        path.symlink_to(target)
        rejects(lambda: helper.verify_files(packages, {'fixture.ts': digest}))
        for name in ('../target.ts', str(target)):
            rejects(lambda: helper.verify_files(packages, {name: digest}))
        rejects(lambda: helper.verify_files(packages, {}))
        # Wrong revision and dirty trees must refuse before parsing any source.
        for head, status in (('wrong', ''), (helper.PIN, ' M tracked.ts'), (helper.PIN, '?? untracked.ts')):
            def git(args, **kwargs):
                from subprocess import CompletedProcess
                return CompletedProcess(args, 0, head if 'rev-parse' in args else status, '')
            with patch.object(helper.subprocess, 'run', side_effect=git), patch.object(helper, 'derive') as derive:
                rejects(lambda: helper.audit(packages))
                derive.assert_not_called()
    print('PASS: websearch registration projection, source byte/path refusals and revision/dirty-tree gates')


if __name__ == '__main__':
    main()
