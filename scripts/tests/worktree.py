#!/usr/bin/env python3
"""P2.8 real-Git / controlled-runtime preservation; disposable repositories only."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'


def git(project, *args):
    return subprocess.run(['/usr/bin/git', '-C', str(project), *args], check=True,
                          capture_output=True).stdout


def tree(directory):
    return {str(p.relative_to(directory)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.rglob('*') if p.is_file()}


for case, expected in [('version', 2), ('before-prompt', 3), ('cancel-ack', 3),
                       ('interrupt', 4), ('text', 0)]:
    with tempfile.TemporaryDirectory(prefix='ah-worktree-') as directory:
        base = Path(directory).resolve()
        project = base / 'project'
        project.mkdir()
        (base / 'opencode').symlink_to(FAKE)
        git(project, 'init', '-q')
        git(project, 'config', 'user.name', 'Fixture')
        git(project, 'config', 'user.email', 'fixture@example.invalid')
        config = dict(version=1, mode='local-only', model='fixture',
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'))
        (project / 'ah.json').write_text(json.dumps(config))
        (project / 'case').write_text(case)
        for name in ['both', 'unstaged', 'rename']:
            (project / name).write_text('committed\n')
        git(project, 'add', '.')
        git(project, 'commit', '-qm', 'baseline')
        (project / 'both').write_text('staged\n')
        git(project, 'add', 'both')
        (project / 'both').write_text('staged plus unstaged\n')
        (project / 'unstaged').write_text('user changes\n')
        git(project, 'mv', 'rename', 'rename\nSECRET_PATH')
        (project / 'untracked\nSECRET_PATH').write_bytes(b'user data\xff')
        # A repository fsmonitor command must never be run by observation.
        hook = base / 'fsmonitor'
        hook.write_text('#!/bin/sh\ntouch "' + str(base / 'HOOK_RAN') + '"\n')
        hook.chmod(0o755)
        git(project, 'config', 'core.fsmonitor', str(hook))
        baseline = {name: ((project / name).read_bytes(), (project / name).stat().st_mtime_ns)
                    for name in ['both', 'unstaged', 'rename\nSECRET_PATH',
                                 'untracked\nSECRET_PATH', 'ah.json', 'case']}
        git_before = tree(project / '.git')
        args = [str(BINARY), 'single', 'Task', '--project', str(project)]
        env = {**os.environ, 'PATH': str(base) + ':' + os.environ['PATH'],
               'TEST_KEY': 'SECRET_SENTINEL', 'GIT_DIR': '/nonexistent/poison'}
        process = subprocess.Popen(args, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        if case in ['before-prompt', 'cancel-ack', 'interrupt']:
            marker = project / ('pids.json' if case == 'before-prompt' else 'prompted')
            until = time.monotonic() + 15
            while not marker.exists() and process.poll() is None and time.monotonic() < until:
                time.sleep(.02)
            assert marker.exists(), case
            process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=30)
        assert process.returncode == expected, (case, process.returncode, err)
        assert 'project baseline: dirty; staged=2 unstaged=2 untracked=1;' in err, err
        assert 'authorized runtime edits' in err and 'attribution unknown' in err
        assert 'SECRET_PATH' not in out + err and 'SECRET_SENTINEL' not in out + err
        assert baseline == {name: ((project / name).read_bytes(), (project / name).stat().st_mtime_ns)
                            for name in baseline}, case
        assert tree(project / '.git') == git_before, case
        assert not (base / 'HOOK_RAN').exists(), case
        assert not (project / 'rename').exists(), case
        assert not list((project / '.git').glob('*lock')), case
        if case == 'version':
            assert not (project / 'opencode.json').exists()
        else:
            assert (project / 'opencode.json').exists()
            assert (project / '.ah-opencode-owner.json').exists()
        print('PASS preservation', case, flush=True)

print('dirty-project fixtures passed; no model traffic')

for scenario in ['clean', 'unborn', 'nonrepo', 'linked', 'filter-local', 'filter-included', 'filter-worktree']:
    with tempfile.TemporaryDirectory(prefix='ah-baseline-') as directory:
        base = Path(directory).resolve()
        project = base / 'project'
        project.mkdir()
        (base / 'opencode').symlink_to(FAKE)
        (project / 'case').write_text('version')
        (project / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only',
            model='fixture', litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'))))
        if scenario != 'nonrepo':
            git(project, 'init', '-q')
            git(project, 'config', 'user.name', 'Fixture')
            git(project, 'config', 'user.email', 'fixture@example.invalid')
            if scenario != 'unborn':
                git(project, 'add', '.')
                git(project, 'commit', '-qm', 'baseline')
            if scenario == 'linked':
                linked = base / 'linked'
                git(project, 'worktree', 'add', '-qb', 'fixture-linked', str(linked))
                project = linked
        if scenario.startswith('filter-'):
            hook = base / 'filter-trap'
            hook.write_text('#!/bin/sh\ntouch "' + str(base / 'FILTER_RAN') + '"\ncat\n')
            hook.chmod(0o755)
            (project / '.gitattributes').write_text('case filter=trap\n')
            # Ensure status would re-hash this tracked file.
            (project / 'case').write_text('version\n')
            if scenario == 'filter-included':
                included = base / 'included-config'
                included.write_text('[filter "trap"]\n clean = ' + str(hook) + '\n')
                git(project, 'config', 'include.path', str(included))
            elif scenario == 'filter-worktree':
                git(project, 'config', 'extensions.worktreeConfig', 'true')
                git(project, 'config', '--worktree', 'filter.trap.process', str(hook))
            else:
                git(project, 'config', 'filter.trap.clean', str(hook))
        before = tree(base)
        result = subprocess.run([str(BINARY), 'single', 'Task', '--project', str(project)],
            env={**os.environ, 'PATH': str(base) + ':' + os.environ['PATH'], 'TEST_KEY': 'sentinel'},
            capture_output=True, text=True, timeout=15)
        assert result.returncode == 2, result.stderr
        expected = ('unavailable (Git filter configuration present' if scenario.startswith('filter-') else
                    'unavailable' if scenario == 'nonrepo' else
                    'dirty; staged=0 unstaged=0 untracked=2;' if scenario == 'unborn' else
                    'clean; staged=0 unstaged=0 untracked=0;')
        assert 'project baseline: ' + expected in result.stderr, result.stderr
        assert before == tree(base), scenario
        print('PASS baseline', scenario, flush=True)
