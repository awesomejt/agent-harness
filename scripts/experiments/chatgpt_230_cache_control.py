#!/usr/bin/env python3
"""D100 opt-in D099 pair with Bun's runtime transpiler cache disabled; setup review MUST precede installed use."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile

import chatgpt_230_parent_watch as watch
import chatgpt_230_state_inventory as inventory
from chatgpt_230_parent_watch import Refusal, require

# Bun 1.4.4 RuntimeTranspilerCache: "0" (or empty) disables the cache before
# XDG_CACHE_HOME is consulted. The embedded Bun is not pinned, so the unchanged
# state gate and inventory, not this value, decide whether it was honoured.
CACHE_CONTROL = {'BUN_RUNTIME_TRANSPILER_CACHE_PATH': '0'}


def child_env(env):
    """The only addition to D099's child environment."""
    require(not set(CACHE_CONTROL) & set(env), 'env-collision')
    return dict(env, BUN_BE_BUN='1', **CACHE_CONTROL)


def run_case(executable, denied):
    # Mirrors inventory.run_case; only the child environment differs (child_env).
    with tempfile.TemporaryDirectory(prefix='ah-state-inventory-') as directory:
        work, _ = watch.create_root(Path(directory).resolve())
        lock = watch.acquire(work)
        require(lock is not None, 'lock')
        try:
            home, project, env = watch.env_from_owned_root(work, project_on=True)
            for path in (project, *(work / name for name in inventory.ROOTS)):
                path.mkdir(parents=True)
            runtime, script = work / 'opencode-cli', work / 'primitive.mjs'
            shutil.copy2(executable, runtime)
            require(watch.digest_owned(runtime) == watch.base.SHA256, 'executable-pin')
            require(watch.lock_probe(work) == 'refused', 'lock')
            script.write_bytes(watch.SCRIPT.read_bytes())
            fixture = watch.Fixture(work, home, project, runtime, script)
            nonce = secrets.token_hex(16)
            command = ['/usr/bin/sandbox-exec', '-p', watch.policy(work, home, runtime, denied),
                       str(runtime), str(script), str(home / 'repo'), 'deny' if denied else 'allow', nonce]
            with watch.supervised(command, project, child_env(env), nonce) as channel:
                result = watch.observe(channel, fixture, denied)
            fixture.check(0 if result['watch'] == 'INCOMPATIBLE' else 3, full=True)
            inventory.settle(work)
        finally:
            os.close(lock)
    return dict(listing='DENIED' if denied else 'ALLOWED', **result)


def run_pair(executable):
    # Reuse D099's ordering/printing exactly, with this module's run_case.
    original = inventory.run_case
    inventory.run_case = run_case
    try:
        inventory.run_pair(executable)
    finally:
        inventory.run_case = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    require(sys.platform == 'darwin', 'platform')
    watch.qualify(args.source)  # All source gates before any runtime launch.
    installed = shutil.which(args.opencode)
    require(installed is not None, 'executable')
    run_pair(Path(installed))
    print('LIMIT: primitive only; OpenCode/matrix/catalog/authenticated gates remain pending')


def entry():
    try:
        main()
    except Refusal as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        return 1
    except Exception:
        print('REFUSED: control-gate; raw diagnostics withheld', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(entry())
