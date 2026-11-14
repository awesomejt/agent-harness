#!/usr/bin/env python3
"""Opt-in pinned macOS operator-login retained-root preflight (D077 login variant).

The harness never runs or prompts for login. The operator prepares a dedicated root, runs the
official command printed by ``--prepare``, then runs this helper with ``--root`` to prove the
login-mode invariants under the D076 composed profile with network denied.
"""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import sys
import tempfile
from pathlib import Path

from antigravity_feasibility import check
from chatgpt_feasibility import SHA256
from chatgpt_installed_observer import build, expected_plugins, static_guards, verify_source
from chatgpt_retained_state import (
    OWNER,
    PUBLISHED_INTEGRATION_COUNT,
    PUBLISHED_INTEGRATION_DIGEST,
    acquire,
    boot,
    boundary_controls,
    create_root,
    env_from_owned_root,
    evaluate,
    integration_digest,
    lock_probe,
    root_shape,
)

PREPARE_RECORD = '.ah-prepare.json'


class LoginPreflightRefusal(RuntimeError):
    """Login-mode preflight invariant failures; message holds violation labels only."""


def write_prepare_record(parent, work, token):
    path = parent / PREPARE_RECORD
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as handle:
        json.dump({'work': str(work.resolve()), 'token': token}, handle)


def read_prepare_record(parent, work):
    path = parent / PREPARE_RECORD
    check(path.is_file() and not path.is_symlink())
    payload = json.loads(path.read_text())
    check(payload.get('work') == str(work.resolve()))
    token = payload.get('token')
    check(isinstance(token, str) and token)
    return token


def operator_login_command(executable, work, project):
    """D077 allowlisted environment; the operator runs this outside harness containment."""
    home = work / 'home'
    term = os.environ.get('TERM', 'xterm-256color')
    env = {
        'HOME': str(home),
        'XDG_DATA_HOME': str(work / 'DATA'),
        'XDG_CONFIG_HOME': str(work / 'CONFIG'),
        'XDG_CACHE_HOME': str(work / 'CACHE'),
        'XDG_STATE_HOME': str(work / 'STATE'),
        'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
        'TERM': term,
        'OPENCODE_DISABLE_PROJECT_CONFIG': '1',
        'OPENCODE_DISABLE_CLAUDE_CODE': '1',
    }
    prefix = ['env', '-i', *(f'{key}={value}' for key, value in env.items())]
    body = shlex.join(prefix + [str(executable), 'auth', 'login', 'openai', '--method',
                                'chatgpt-token-sharing', '--standalone'])
    return f'cd {shlex.quote(str(project))} && {body}'


def prepare_parent(parent):
    parent = parent.resolve()
    if parent.exists():
        check(parent.is_dir() and parent.stat().st_mode & 0o777 == 0o700
              and parent.stat().st_uid == os.getuid())
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    check(parent.stat().st_mode & 0o777 == 0o700 and parent.stat().st_uid == os.getuid())


def prepare(parent, runtime_path):
    """Create a fresh owned root and print the operator login command."""
    check(runtime_path.is_file())
    check(hashlib.sha256(runtime_path.read_bytes()).hexdigest() == SHA256)
    prepare_parent(parent)
    work, token = create_root(parent)
    work = work.resolve()
    home, project, env, _ = build(work, False, False)
    check(not root_shape(work, token, env))
    static_guards(work, home, project, env)
    write_prepare_record(parent, work, token)
    return work, token, project, operator_login_command(runtime_path, work, project)


def attach(work, runtime_path, builtin):
    """Load an operator-prepared owned root for contained preflight boots."""
    work = work.resolve()
    expected = read_prepare_record(work.parent, work)
    marker = work / OWNER
    check(marker.is_file() and not marker.is_symlink())
    runtime = runtime_path.resolve()
    check(runtime.is_file())
    check(hashlib.sha256(runtime.read_bytes()).hexdigest() == SHA256)
    home, project, env = env_from_owned_root(work, False, True)
    check(home.is_dir() and project.is_dir())
    env.pop('OPENCODE_PASSWORD', None)
    violations = root_shape(work, expected, env)
    if violations:
        raise RuntimeError(f'root shape refused: {violations}')
    static_guards(work, home, project, env)
    return {'runtime': runtime, 'work': work, 'home': home, 'project': project, 'env': env, 'token': expected,
            'builtin': builtin}


def run_preflight(ctx):
    """Two contained boots on one retained login root; both must pass login-mode preflight."""
    held = acquire(ctx['work'])
    check(held is not None)
    try:
        check(lock_probe(ctx['work']) == 'refused')
        first = boot(ctx)
        second = boot(ctx)
    finally:
        os.close(held)
    check(lock_probe(ctx['work']) == 'acquired')
    for record in (first['before'], first['after'], second['before'], second['after']):
        integrations = record[1]
        check(integration_digest(integrations) == PUBLISHED_INTEGRATION_DIGEST)
        check(len(integrations) == PUBLISHED_INTEGRATION_COUNT)
    check(first['before'] == first['after'] == second['before'] == second['after'])
    expected_set = frozenset(first['after'][1])
    login_refusals = evaluate(first['after'], expected_set, ctx['builtin'])[1]
    if login_refusals:
        raise LoginPreflightRefusal(f'login preflight failed: {login_refusals!r}; complete operator login first')
    return {'boots': 2, 'identical': True, 'lock': ['refused', 'acquired'],
            'preflight_login': login_refusals, 'integration_count': len(expected_set)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode', help='installed executable on PATH')
    parser.add_argument('--source', type=Path, help='official v2.2.5 checkout (D071 procedure)')
    parser.add_argument('--prepare', type=Path, metavar='PARENT',
                        help='create a new owned root under PARENT and print the login command')
    parser.add_argument('--root', type=Path, help='existing owned root after operator login')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-login-bin-') as directory:
        runtime = Path(directory).resolve() / 'opencode-cli'
        shutil.copy2(installed, runtime)
        check(hashlib.sha256(runtime.read_bytes()).hexdigest() == SHA256)
        if args.prepare is not None:
            parent = args.prepare.resolve()
            prepare_parent(parent)
            pinned = parent / 'opencode-cli'
            shutil.copy2(runtime, pinned)
            work, _, _, command = prepare(parent, pinned)
            print('OPERATOR: run the following official login in your own shell (not from this helper):')
            print(command)
            print('OPERATOR: after login succeeds, run login preflight with:')
            print(f'  python3 -B {Path(__file__).resolve()} --root {work} '
                  f'--source <v2.2.5 checkout>')
            return
        check(args.root is not None and args.source is not None)
        packages, _ = verify_source(args.source.resolve())
        builtin, _, _ = expected_plugins(packages)
        boundary = boundary_controls(args.root.resolve())
        ctx = attach(args.root, runtime, builtin)
        results = run_preflight(ctx)
    print('PASS: login root retained across two contained boots with login-mode preflight clean', flush=True)
    print(json.dumps({'origin_boundary': boundary, 'cases': results}, indent=1, sort_keys=True))
    print('LIMIT: login-mode retained preflight only; method, endpoint, permission and account gates remain open')


if __name__ == '__main__':
    try:
        main()
    except LoginPreflightRefusal as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('Login preflight failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)