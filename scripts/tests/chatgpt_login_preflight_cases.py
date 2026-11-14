#!/usr/bin/env python3
"""Offline login-preflight command, prepare and attach refusals; no OpenCode or network."""
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
        assert not (parent / 'work').exists()
    print('PASS: prepare refuses a byte-drifted executable before root creation', flush=True)


def marker_cases():
    with tempfile.TemporaryDirectory(prefix='ah-login-marker-') as directory:
        parent = Path(directory)
        work, token = retained.create_root(parent)
        work = work.resolve()
        login.write_prepare_record(parent, work, token)
        _, project, env = retained.env_from_owned_root(work, False, True)
        env.pop('OPENCODE_PASSWORD', None)
        assert not retained.root_shape(work, token, env)
        (work / retained.OWNER).write_text('tampered')
        assert retained.root_shape(work, token, env) == ['root-marker']
        assert login.read_prepare_record(parent, work) == token
    print('PASS: prepare record token differs from a tampered in-root marker', flush=True)


def main():
    command_cases()
    prepare_cases()
    marker_cases()
    print('PASS: chatgpt_login_preflight_cases complete', flush=True)


if __name__ == '__main__':
    main()