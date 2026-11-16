#!/usr/bin/env python3
"""D099 opt-in D098 pair plus content-free created-state inventory; setup review MUST precede installed use."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys
import tempfile
import argparse

import chatgpt_230_parent_watch as watch
from chatgpt_230_parent_watch import Refusal, require

ROOTS = ('CONFIG', 'DATA', 'CACHE', 'STATE')
MAX_DEPTH = 6
MAX_ENTRIES = 128
# Hypothesized names are emitted literally only because these bytes are ours.
KNOWN = frozenset({'bun', '.bun', '@t@', 'install', 'cache', 'opencode', 'tmp', 'log', 'bin'})


class StateCreated(Refusal):
    """state-created with a caller-built finite inventory, printed only after cleanup."""
    def __init__(self, summary):
        super().__init__('state-created')
        self.summary = summary


def label(name):
    if name in KNOWN:
        return 'N:' + name
    # Never emit an unknown name; a truncated digest lets hypotheses be checked offline.
    return 'H:' + hashlib.sha256(os.fsencode(name)).hexdigest()[:16]


def size_bucket(size):
    return 'ZERO' if size == 0 else 'LE_4K' if size <= 4096 else 'LE_1M' if size <= 1 << 20 else 'GT_1M'


def inventory(work):
    """Metadata only: lstat/scandir without following links; no file is ever opened."""
    entries, truncated = [], False

    def visit(directory, root, depth):
        nonlocal truncated
        with os.scandir(directory) as items:
            children = sorted(items, key=lambda item: os.fsencode(item.name))
        for item in children:
            if len(entries) >= MAX_ENTRIES:
                truncated = True
                return
            info = item.stat(follow_symlinks=False)
            mode = info.st_mode
            kind = ('DIR' if stat.S_ISDIR(mode) else 'FILE' if stat.S_ISREG(mode) else
                    'LINK' if stat.S_ISLNK(mode) else 'OTHER')
            entry = {'root': root, 'depth': depth, 'type': kind, 'name': label(item.name)}
            if kind == 'FILE':
                entry['size'] = size_bucket(info.st_size)
            entries.append(entry)
            if kind == 'DIR':
                if depth >= MAX_DEPTH:
                    truncated = True
                else:
                    visit(item.path, root, depth + 1)

    for root in ROOTS:
        watch.identity(work / root, True)
        visit(work / root, root, 1)
    return {'entries': entries, 'truncated': truncated}


def settle(work):
    """D098 emptiness gate, unchanged except that a refusal carries the inventory."""
    if all(not any((work / name).iterdir()) for name in ROOTS):
        return
    raise StateCreated(inventory(work))


def run_case(executable, denied):
    # Mirrors watch.run_case; only the final state gate differs (settle).
    with tempfile.TemporaryDirectory(prefix='ah-state-inventory-') as directory:
        work, _ = watch.create_root(Path(directory).resolve())
        lock = watch.acquire(work)
        require(lock is not None, 'lock')
        try:
            home, project, env = watch.env_from_owned_root(work, project_on=True)
            for path in (project, *(work / name for name in ROOTS)):
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
            with watch.supervised(command, project, dict(env, BUN_BE_BUN='1'), nonce) as channel:
                result = watch.observe(channel, fixture, denied)
            fixture.check(0 if result['watch'] == 'INCOMPATIBLE' else 3, full=True)
            settle(work)
        finally:
            os.close(lock)
    return dict(listing='DENIED' if denied else 'ALLOWED', **result)


def run_pair(executable):
    for denied in (False, True):
        listing = 'DENIED' if denied else 'ALLOWED'
        try:
            result = run_case(executable, denied)
        except StateCreated as error:
            # Root, lock and child are gone here; print the finite inventory, then stop.
            print(json.dumps(dict(listing=listing, state='CREATED', **error.summary), sort_keys=True), flush=True)
            raise
        print(json.dumps(result, sort_keys=True), flush=True)
        require(result['watch'] == 'COMPATIBLE', 'parent-watch-incompatible' if denied else 'control')


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
