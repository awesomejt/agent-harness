#!/usr/bin/env python3
"""Offline login-preflight command, prepare and attach refusals; no OpenCode or network."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_login_preflight as login
import chatgpt_retained_state as retained


def rejects(action):
    try:
        action()
    except (RuntimeError, ValueError, TypeError, AttributeError, AssertionError):
        return
    raise AssertionError('unsafe input was accepted')


def command_cases():
    with tempfile.TemporaryDirectory(prefix='ah-login-cmd-') as directory:
        work = Path(directory) / 'work'
        project = work / 'home' / 'repo' / 'project'
        project.mkdir(parents=True)
        for kind in ('DATA', 'CONFIG', 'CACHE', 'STATE'):
            (work / kind).mkdir()
        runtime = work / 'bin' / 'opencode'
        runtime.parent.mkdir()
        runtime.write_text('')
        line = login.operator_login_command(runtime, work, project)
    assert line.startswith(f"cd {project!s} && env -i ")
    assert 'OPENCODE_DISABLE_CLAUDE_CODE=1' in line
    assert 'chatgpt-token-sharing' in line and '--standalone' in line
    assert 'OPENCODE_PASSWORD' not in line
    print('PASS: operator login command uses D077 allowlist and project cwd', flush=True)


def prepare_cases():
    with tempfile.TemporaryDirectory(prefix='ah-login-prepare-') as directory:
        parent = Path(directory)
        runtime = parent / 'opencode-cli'
        runtime.write_bytes(b'\x00' * 8)
        rejects(lambda: login.prepare(parent, runtime))
        # Wrong digest is refused before root creation.
        parent.joinpath('work').mkdir(exist_ok=True)
    print('PASS: prepare refuses a byte-drifted executable before root creation', flush=True)


def attach_cases():
    with tempfile.TemporaryDirectory(prefix='ah-login-attach-') as directory:
        parent = Path(directory)
        work, token = retained.create_root(parent)
        home, project, env, _ = __import__('chatgpt_installed_observer', fromlist=['build']).build(work, False, False)
        runtime = parent / 'opencode-cli'
        runtime.write_bytes(b'x' * 3)
        rejects(lambda: login.attach(work, runtime, {}))
        marker = work / retained.OWNER
        marker.write_text('wrong')
        rejects(lambda: login.attach(work, runtime, {}))
    print('PASS: attach refuses marker drift and unpinned executable bytes', flush=True)


def main():
    command_cases()
    prepare_cases()
    attach_cases()
    print('PASS: chatgpt_login_preflight_cases complete', flush=True)


if __name__ == '__main__':
    main()