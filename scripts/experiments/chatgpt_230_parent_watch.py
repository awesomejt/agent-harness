#!/usr/bin/env python3
"""D097 opt-in disposable parent-watch primitive; setup review MUST precede installed use."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

from antigravity_feasibility import LIMIT, TIMEOUT, signal_group
import chatgpt_230_observer as base
from chatgpt_230_warning_diagnostic import qualify as warning_qualify
from chatgpt_230_source_audit import verify_files
from chatgpt_retained_state import acquire, create_root, env_from_owned_root, lock_probe

MANIFEST = Path(__file__).resolve().parents[2] / 'docs/evidence/p7-9-230-parent-watch-source-manifest.json'
SCRIPT = Path(__file__).with_name('chatgpt_parent_watch.mjs')
PHASE_BYTES = (b'AH_CREATE', b'AH_UPDATE')
CODES = {'EPERM', 'EACCES', 'ENOENT', 'UNKNOWN'}
LABELS = {'PROBES_OK', 'READY', 'CLOSED', 'FAIL', 'PROBE_FAIL', 'PREMATURE',
          'STATE_FAIL', 'PROTOCOL_FAIL', 'TIMEOUT'} | {
              prefix + code for prefix in ('SYNC_', 'ASYNC_') for code in CODES} | {
              prefix + str(i) for prefix in ('ARMED_', 'EVENT_') for i in (1, 2, 3)}


class Refusal(RuntimeError):
    """Only caller-owned finite labels may be exposed."""


def require(value, code):
    if not value:
        raise Refusal(code)


def identity(path, directory=False):
    info = path.lstat()
    require(not stat.S_ISLNK(info.st_mode) and info.st_uid == os.getuid(), 'owned-path')
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'owned-path')
    require(path.resolve() == path, 'owned-path')
    return info.st_dev, info.st_ino


def read_owned(path):
    before = identity(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require((info.st_dev, info.st_ino) == before and info.st_size <= LIMIT, 'owned-file')
        result = os.read(fd, LIMIT + 1)
        require(len(result) == info.st_size and identity(path) == before, 'owned-file')
        return result
    finally:
        os.close(fd)


def digest_owned(path):
    before = identity(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require((info.st_dev, info.st_ino) == before and info.st_size <= 512 * 1024 * 1024,
                'owned-file')
        digest, count = hashlib.sha256(), 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            count += len(chunk)
            require(count <= info.st_size, 'owned-file')
            digest.update(chunk)
        require(count == info.st_size and identity(path) == before and
                os.fstat(fd).st_mtime_ns == info.st_mtime_ns, 'owned-file')
        return digest.hexdigest()
    finally:
        os.close(fd)


def metadata(path):
    """Cheap in-window drift check: any content write changes ctime, which callers cannot restore."""
    identity(path)
    info = path.lstat()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


class Channel:
    """Selector-driven private pipes with a whole-process deadline and total byte bound."""
    def __init__(self, child, nonce, timeout=TIMEOUT):
        self.child, self.nonce = child, nonce
        self.selector = selectors.DefaultSelector()
        self.selector.register(child.stdout, selectors.EVENT_READ, 'out')
        self.selector.register(child.stderr, selectors.EVENT_READ, 'err')
        self.pending = bytearray()
        self.count = 0
        self.deadline = time.monotonic() + timeout

    def pump(self):
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'timeout')
        for key, _ in self.selector.select(min(remaining, .1)):
            chunk = os.read(key.fileobj.fileno(), 65536)
            if not chunk:
                self.selector.unregister(key.fileobj)
                continue
            self.count += len(chunk)
            require(self.count <= LIMIT, 'pipe-overflow')
            require(key.data == 'out', 'stderr')
            self.pending.extend(chunk)

    def next(self, allowed):
        while b'\n' not in self.pending:
            require(bool(self.selector.get_map()), 'missing-output')
            self.pump()
        raw, _, tail = self.pending.partition(b'\n')
        self.pending = bytearray(tail)
        # Compare bytes, never decode/emit an untrusted field or exception.
        tokens = {self.nonce.encode() + b' ' + label.encode(): label for label in LABELS}
        raw = bytes(raw)
        require(raw in tokens, 'protocol')
        label = tokens[bytes(raw)]
        require(label in allowed, 'unexpected-stage')
        return label

    def send(self, label):
        require(label in {'ARM_1', 'ARM_2', 'ARM_3', 'CLOSE'}, 'command')
        require(not self.pending, 'premature-output')
        self.child.stdin.write((self.nonce + ' ' + label + '\n').encode())
        self.child.stdin.flush()

    def finish(self):
        self.child.stdin.close()
        while self.selector.get_map():
            self.pump()
        require(not self.pending, 'extra-output')
        require(self.child.wait(timeout=max(.01, self.deadline - time.monotonic())) == 0, 'child-exit')


@contextmanager
def supervised(command, cwd, env, nonce, timeout=TIMEOUT):
    child = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    channel = None
    try:
        channel = Channel(child, nonce, timeout)
        yield channel
    finally:
        # Attempt every cleanup step even if a close/signal/wait itself fails.
        failed = False
        try:
            if child.stdin is not None and not child.stdin.closed:
                child.stdin.close()
        except Exception:
            failed = True
        for sig, timeout_after in ((signal.SIGTERM, .5), (signal.SIGKILL, 2)):
            try:
                signal_group(child.pid, sig)
            except Exception:
                failed = True
            try:
                child.wait(timeout=timeout_after)
            except subprocess.TimeoutExpired:
                if sig == signal.SIGKILL:
                    failed = True
            except Exception:
                failed = True
        try:
            if channel is not None:
                channel.selector.close()
        except Exception:
            failed = True
        for pipe in (child.stdout, child.stderr):
            try:
                pipe.close()
            except Exception:
                failed = True
        require(not failed, 'cleanup')


class Fixture:
    """Only exact owned paths; check identity before and after every driver mutation."""
    def __init__(self, work, home, project, runtime, script):
        self.work, self.parent = work, home / 'repo'
        self.target = self.parent / 'opencode.jsonc'
        self.direct = self.parent / 'opencode.json'
        self.direct.write_bytes(b'AH_DIRECT')
        self.dirs = {p: identity(p, True) for p in
                     (work, home, self.parent, project,
                      *(work / name for name in ('CONFIG', 'DATA', 'CACHE', 'STATE')))}
        self.files = {p: (identity(p), digest_owned(p)) for p in (script, self.direct, work / '.ah-owner', work / '.ah-lock')}
        # The large runtime is fully hashed before launch and after child exit (full=True);
        # in-window phase checks compare identity/size/mtime/ctime instead of re-hashing it.
        self.runtime = runtime
        self.runtime_meta, self.runtime_digest = metadata(runtime), digest_owned(runtime)
        self.target_id = None

    def check(self, phase, full=False):
        require(metadata(self.runtime) == self.runtime_meta, 'file-drift')
        if full:
            require(digest_owned(self.runtime) == self.runtime_digest, 'file-drift')
        require(all(identity(p, True) == expected for p, expected in self.dirs.items()), 'directory-drift')
        require(set(self.work.iterdir()) == {self.work / name for name in
                ('.ah-owner', '.ah-lock', 'home', 'CONFIG', 'DATA', 'CACHE', 'STATE',
                 'opencode-cli', 'primitive.mjs')}, 'fixture-shape')
        require(set((self.work / 'home').iterdir()) == {self.parent} and
                not any((self.parent / 'project').iterdir()), 'fixture-shape')
        for path, (expected, content) in self.files.items():
            require(identity(path) == expected and digest_owned(path) == content, 'file-drift')
        require(set(self.parent.iterdir()) == {self.direct, self.parent / 'project'} |
                ({self.target} if phase in (1, 2) else set()), 'fixture-shape')
        if phase in (1, 2):
            require(identity(self.target) == self.target_id and read_owned(self.target) == PHASE_BYTES[phase - 1],
                    'candidate-drift')
        else:
            require(not os.path.lexists(self.target), 'candidate-drift')

    def mutate(self, phase):
        self.check(phase - 1)
        if phase == 1:
            staged = self.work / 'staged-candidate'
            fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                require(os.write(fd, PHASE_BYTES[0]) == len(PHASE_BYTES[0]), 'fixture-write')
            finally:
                os.close(fd)
            identity(staged)
            require(not os.path.lexists(self.target), 'candidate-drift')
            staged.rename(self.target)
            self.target_id = identity(self.target)
        elif phase == 2:
            fd = os.open(self.target, os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                require((info.st_dev, info.st_ino) == self.target_id, 'candidate-drift')
                require(os.write(fd, PHASE_BYTES[1]) == len(PHASE_BYTES[1]), 'fixture-write')
                os.ftruncate(fd, len(PHASE_BYTES[1]))
            finally:
                os.close(fd)
        elif phase == 3:
            self.target.unlink()
        else:
            raise Refusal('phase')
        self.check(phase)


def observe(channel, fixture, denied):
    fixture.check(0)
    channel.next({'PROBES_OK'})
    stage = channel.next({'READY'} | {'SYNC_' + code for code in CODES})
    if stage != 'READY':
        channel.finish()
        fixture.check(0)
        require(denied and stage in ('SYNC_EPERM', 'SYNC_EACCES'), 'watch-start')
        return {'watch': 'INCOMPATIBLE', 'stage': 'SYNC', 'code': stage[5:]}
    for phase in (1, 2, 3):
        channel.send('ARM_' + str(phase))
        channel.next({'ARMED_' + str(phase)})
        fixture.mutate(phase)
        channel.next({'EVENT_' + str(phase)})
        fixture.check(phase)
    channel.send('CLOSE')
    channel.next({'CLOSED'})
    channel.finish()
    fixture.check(3)
    return {'watch': 'COMPATIBLE', 'phases': 3}


def policy(work, home, runtime, denied):
    # No owned TCP port is needed. Tighten the inherited composition to zero network and no forks.
    value = base.old.combined_profile(work, None, base.old.ancestor_denials(home))
    value += '(deny process-fork)(deny process-exec (require-not (literal ' + json.dumps(str(runtime)) + ')))'
    if denied:
        value += '(deny file-read-data (literal ' + json.dumps(str(home / 'repo')) + '))'
    return value


def qualify(source):
    warning_qualify(source)
    manifest = json.loads(MANIFEST.read_text())
    require(manifest['kind'] == 'p7-9-230-parent-watch-source/v1' and
            manifest['source_commit'] == 'a6b15d33daf6ab7d35569f6d711fdb630b9f04e7', 'source-pin')
    verify_files(source.resolve() / 'packages', manifest['files'])


def run_case(executable, denied):
    with tempfile.TemporaryDirectory(prefix='ah-parent-watch-') as directory:
        work, _ = create_root(Path(directory).resolve())
        lock = acquire(work)
        require(lock is not None, 'lock')
        try:
            home, project, env = env_from_owned_root(work, project_on=True)
            for path in (project, *(work / name for name in ('CONFIG', 'DATA', 'CACHE', 'STATE'))):
                path.mkdir(parents=True)
            runtime, script = work / 'opencode-cli', work / 'primitive.mjs'
            shutil.copy2(executable, runtime)
            require(digest_owned(runtime) == base.SHA256, 'executable-pin')
            require(lock_probe(work) == 'refused', 'lock')
            script.write_bytes(SCRIPT.read_bytes())
            fixture = Fixture(work, home, project, runtime, script)
            nonce = secrets.token_hex(16)
            command = ['/usr/bin/sandbox-exec', '-p', policy(work, home, runtime, denied),
                       str(runtime), str(script), str(home / 'repo'), 'deny' if denied else 'allow', nonce]
            with supervised(command, project, dict(env, BUN_BE_BUN='1'), nonce) as channel:
                result = observe(channel, fixture, denied)
            # No service/state/extra executable/resource side effects are accepted.
            fixture.check(0 if result['watch'] == 'INCOMPATIBLE' else 3, full=True)
            require(all(not any((work / name).iterdir()) for name in ('CONFIG', 'DATA', 'CACHE', 'STATE')),
                    'state-created')
        finally:
            os.close(lock)
    # Print only after child/group, lock and disposable root cleanup have completed.
    return dict(listing='DENIED' if denied else 'ALLOWED', **result)


def run_pair(executable):
    result = run_case(executable, False)
    print(json.dumps(result, sort_keys=True), flush=True)
    require(result['watch'] == 'COMPATIBLE', 'control')
    result = run_case(executable, True)
    print(json.dumps(result, sort_keys=True), flush=True)
    require(result['watch'] == 'COMPATIBLE', 'parent-watch-incompatible')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    require(sys.platform == 'darwin', 'platform')
    qualify(args.source)  # All source gates before any runtime launch.
    installed = shutil.which(args.opencode)
    require(installed is not None, 'executable')
    # run_case exclusively creates/copies/rechecks each binary before use.
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
