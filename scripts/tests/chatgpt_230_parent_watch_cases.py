#!/usr/bin/env python3
"""Offline D097 parent-watch primitive refusal and lifecycle cases; never runs OpenCode/sandbox."""
from contextlib import contextmanager
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_parent_watch as helper


def rejects(action, code=None):
    try:
        action()
    except helper.Refusal as error:
        if code is not None:
            assert str(error) == code
        return
    raise AssertionError('unsafe primitive accepted')


class Fixture:
    def __init__(self): self.phases = []
    def check(self, phase): self.phases.append(('check', phase))
    def mutate(self, phase): self.phases.append(('mutate', phase))


class Channel:
    def __init__(self, labels): self.labels, self.sent, self.finished = list(labels), [], False
    def next(self, allowed):
        value = self.labels.pop(0)
        helper.require(value in allowed, 'unexpected-stage')
        return value
    def send(self, value): self.sent.append(value)
    def finish(self): self.finished = True


def observe_cases():
    clean = Channel(['PROBES_OK', 'READY', 'ARMED_1', 'EVENT_1', 'ARMED_2', 'EVENT_2',
                     'ARMED_3', 'EVENT_3', 'CLOSED'])
    fixture = Fixture()
    assert helper.observe(clean, fixture, False) == {'watch': 'COMPATIBLE', 'phases': 3}
    assert clean.sent == ['ARM_1', 'ARM_2', 'ARM_3', 'CLOSE'] and clean.finished
    assert fixture.phases == [('check', 0), ('mutate', 1), ('check', 1), ('mutate', 2),
                              ('check', 2), ('mutate', 3), ('check', 3), ('check', 3)]
    for code in ('EPERM', 'EACCES'):
        channel, fixture = Channel(['PROBES_OK', 'SYNC_' + code]), Fixture()
        assert helper.observe(channel, fixture, True) == {'watch': 'INCOMPATIBLE', 'stage': 'SYNC', 'code': code}
        assert channel.finished and channel.sent == []
        rejects(lambda: helper.observe(Channel(['PROBES_OK', 'SYNC_' + code]), Fixture(), False), 'watch-start')
    for label in ('SYNC_ENOENT', 'SYNC_UNKNOWN'):
        rejects(lambda label=label: helper.observe(Channel(['PROBES_OK', label]), Fixture(), True), 'watch-start')
    for label in ('ASYNC_EPERM', 'ASYNC_EACCES', 'ASYNC_ENOENT', 'ASYNC_UNKNOWN'):
        rejects(lambda label=label: helper.observe(Channel(['PROBES_OK', label]), Fixture(), True), 'unexpected-stage')
    rejects(lambda: helper.observe(Channel(['PROBES_OK', 'READY', 'ARMED_1', 'EVENT_1', 'EVENT_2']), Fixture(), False),
            'unexpected-stage')


def channel_and_supervision_cases():
    original = subprocess.Popen
    children = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        nonce = 'a' * 32
        def launch(script):
            def start(*args, **kwargs):
                child = original([sys.executable, '-c', script], **kwargs)
                children.append(child)
                return child
            return start
        good = "import sys; print('" + nonce + " READY',flush=True); sys.stdin.read()"
        with patch.object(helper.subprocess, 'Popen', side_effect=launch(good)):
            with helper.supervised(['unused'], root, {}, nonce, timeout=2) as channel:
                assert channel.next({'READY'}) == 'READY'
            assert children[-1].poll() is not None and children[-1].stdout.closed and children[-1].stderr.closed
        for script, code in (("import sys;sys.stderr.write('SECRET_STDERR');sys.stderr.flush()", 'stderr'),
                             ("print('SECRET_BAD_PROTOCOL',flush=True)", 'protocol')):
            with patch.object(helper.subprocess, 'Popen', side_effect=launch(script)):
                with helper.supervised(['unused'], root, {}, nonce, timeout=2) as channel:
                    rejects(lambda: channel.next({'READY'}), code)
                assert children[-1].poll() is not None
        noisy = "import sys;print('" + nonce + " READY',flush=True);sys.stdout.write('x'*2048);sys.stdout.flush();sys.stdin.read()"
        with patch.object(helper, 'LIMIT', 128), patch.object(helper.subprocess, 'Popen', side_effect=launch(noisy)):
            with helper.supervised(['unused'], root, {}, nonce, timeout=2) as channel:
                rejects(lambda: channel.next({'READY'}), 'pipe-overflow')
            assert children[-1].poll() is not None


def fixture_identity_cases():
    with tempfile.TemporaryDirectory() as directory:
        work, _ = helper.create_root(Path(directory).resolve())
        lock = helper.acquire(work)
        assert lock is not None
        home = work / 'home'; project = home / 'repo' / 'project'
        for path in (project, *(work / name for name in ('CONFIG', 'DATA', 'CACHE', 'STATE'))):
            path.mkdir(parents=True)
        runtime, script = work / 'opencode-cli', work / 'primitive.mjs'
        runtime.write_bytes(b'R'); script.write_bytes(b'S')
        try:
            fixture = helper.Fixture(work, home, project, runtime, script)
            fixture.check(0); fixture.mutate(1); fixture.mutate(2); fixture.mutate(3)
            runtime.unlink(); runtime.symlink_to(script)
            rejects(lambda: fixture.check(3), 'owned-path')
        finally:
            os.close(lock)


@contextmanager
def owned_fixture():
    """Exact helper layout for offline Node supervision; no sandbox or installed CLI."""
    with tempfile.TemporaryDirectory() as directory:
        work, _ = helper.create_root(Path(directory).resolve())
        lock = helper.acquire(work)
        assert lock is not None
        home, project = work / 'home', work / 'home' / 'repo' / 'project'
        for path in (project, *(work / name for name in ('CONFIG', 'DATA', 'CACHE', 'STATE'))):
            path.mkdir(parents=True)
        runtime, script = work / 'opencode-cli', work / 'primitive.mjs'
        runtime.write_bytes(b'OFFLINE_NODE')
        script.write_bytes(helper.SCRIPT.read_bytes())
        try:
            yield work, home, project, helper.Fixture(work, home, project, runtime, script)
        finally:
            os.close(lock)


def node_command(wrapper, parent, mode, nonce):
    node = shutil.which('node') or '/opt/homebrew/bin/node'
    if not Path(node).exists():
        return None
    return [node, '--input-type=module', '-e', wrapper, str(parent), mode, nonce]


def node_wrapper():
    # `fs` is a default object shared by the subsequently imported primitive.
    # The fake watcher watches owned state only and emits null filenames with
    # rename/change values, exercising the source-faithful callback path.
    return """
import fs from 'node:fs'; import {EventEmitter} from 'node:events';
const [parent, mode, nonce] = process.argv.slice(-3);
const originalList = fs.readdirSync, originalWatch = fs.watch;
const fail = (code, extra='') => Object.assign(new Error('PRIVATE_'+extra), {code, secret:'SECRET'});
if (mode === 'deny-sync') {
  fs.readdirSync = (p,...a) => { if (p === parent) throw fail('EPERM'); return originalList(p,...a); };
  fs.watch = () => { throw fail('EPERM'); };
} else if (mode === 'deny-async') {
  fs.readdirSync = (p,...a) => { if (p === parent) throw fail('EACCES'); return originalList(p,...a); };
  fs.watch = () => { const e = new EventEmitter(); e.close = () => {}; setTimeout(() => e.emit('error', fail('EACCES','ASYNC')), 25); return e; };
} else if (mode === 'close-throws') {
  fs.watch = () => { const e = new EventEmitter(); e.close = () => { throw fail('EIO'); }; setTimeout(() => e.emit('error', fail('EACCES','ASYNC')), 25); return e; };
} else if (mode === 'bad-list') {
  fs.readdirSync = (p,...a) => p === parent ? ['opencode.json'] : originalList(p,...a);
} else if (mode === 'null-events') {
  fs.watch = (p, _o, cb) => {
    const e = new EventEmitter(); let prior = '';
    const timer = setInterval(() => {
      let current = 'missing';
      try { current = fs.readFileSync(p + '/opencode.jsonc','utf8'); } catch {}
      if (current !== prior) { prior = current; cb(current === 'AH_UPDATE' ? 'change' : 'rename', null); }
    }, 10);
    e.close = () => clearInterval(timer); return e;
  };
} else if (mode === 'swapped-events') {
  // Candidate filename with inverted eventType, plus unwatched-name noise that must be ignored.
  fs.watch = (p, _o, cb) => {
    const e = new EventEmitter(); let prior = '';
    const timer = setInterval(() => {
      cb('rename', 'unrelated.txt');
      let current = 'missing';
      try { current = fs.readFileSync(p + '/opencode.jsonc','utf8'); } catch {}
      if (current !== prior) { prior = current; cb(current === 'AH_UPDATE' ? 'rename' : 'change', 'opencode.jsonc'); }
    }, 10);
    e.close = () => clearInterval(timer); return e;
  };
}
const {run} = await import(""" + repr(helper.SCRIPT.as_uri()) + """); run(parent, mode.startsWith('deny') ? 'deny' : 'allow', nonce);
"""


def js_protocol_cases():
    wrapper = node_wrapper()
    if node_command(wrapper, Path('/unused'), 'allow', 'a' * 32) is None:
        print('SKIP: node unavailable')
        return
    nonce = 'b' * 32
    # Null filenames and swapped rename/change eventTypes are both source-accepted.
    for mode in ('null-events', 'swapped-events'):
        with owned_fixture() as (_work, home, project, fixture):
            command = node_command(wrapper, home / 'repo', mode, nonce)
            with helper.supervised(command, project, {}, nonce, timeout=4) as channel:
                assert helper.observe(channel, fixture, False) == {'watch': 'COMPATIBLE', 'phases': 3}
    # Listing denial must reach a synchronous EPERM only after the direct probes,
    # and the real driver records it as INCOMPATIBLE with an untouched fixture.
    nonce = 'c' * 32
    with owned_fixture() as (_work, home, project, fixture):
        command = node_command(wrapper, home / 'repo', 'deny-sync', nonce)
        with helper.supervised(command, project, {}, nonce, timeout=2) as channel:
            assert helper.observe(channel, fixture, True) == \
                {'watch': 'INCOMPATIBLE', 'stage': 'SYNC', 'code': 'EPERM'}
    # An asynchronous watcher error follows READY (fs.watch returned) and must refuse
    # through the real driver before any mutation, never record incompatibility.
    with owned_fixture() as (_work, home, project, fixture):
        command = node_command(wrapper, home / 'repo', 'deny-async', nonce)
        with helper.supervised(command, project, {}, nonce, timeout=2) as channel:
            rejects(lambda: helper.observe(channel, fixture, True), 'unexpected-stage')
        fixture.check(0)
    # A watcher close that throws still terminates promptly with FAIL, never a hang.
    with owned_fixture() as (_work, home, project, fixture):
        command = node_command(wrapper, home / 'repo', 'close-throws', nonce)
        with helper.supervised(command, project, {}, nonce, timeout=2) as channel:
            assert channel.next({'PROBES_OK'}) == 'PROBES_OK' and channel.next({'READY'}) == 'READY'
            assert channel.next({'FAIL'}) == 'FAIL'
    # A listing that disagrees with the owned fixture is a probe failure.
    with owned_fixture() as (_work, home, project, fixture):
        command = node_command(wrapper, home / 'repo', 'bad-list', nonce)
        with helper.supervised(command, project, {}, nonce, timeout=2) as channel:
            fixture.check(0)
            assert channel.next({'PROBE_FAIL'}) == 'PROBE_FAIL'
            channel.finish()


def js_cases():
    node = next((value for value in ('node', '/opt/homebrew/bin/node') if os.path.exists(value) or shutil.which(value)), None)
    if node is None:
        print('SKIP: node unavailable')
        return
    code = "import {matches} from " + repr(helper.SCRIPT.as_uri()) + ";" + \
           "if(!matches(null,'x')||!matches('x','x')||matches('y','x'))process.exit(1);"
    assert subprocess.run([node, '--input-type=module', '-e', code], capture_output=True, timeout=5).returncode == 0


def entry_sanitizes():
    output, errors = io.StringIO(), io.StringIO()
    with patch.object(helper, 'main', side_effect=RuntimeError('SECRET_UNTRUSTED')), \
         patch('sys.stdout', output), patch('sys.stderr', errors):
        assert helper.entry() == 1
    assert output.getvalue() == '' and errors.getvalue().strip() == 'REFUSED: control-gate; raw diagnostics withheld'


def pair_ordering():
    with patch.object(helper, 'run_case', side_effect=[{'watch': 'INCOMPATIBLE'}, {'watch': 'COMPATIBLE'}]) as run, \
         patch('sys.stdout', io.StringIO()):
        rejects(lambda: helper.run_pair(Path('unused')), 'control')
        assert run.call_count == 1 and run.call_args.args[1] is False


def main():
    observe_cases()
    channel_and_supervision_cases()
    fixture_identity_cases()
    entry_sanitizes()
    pair_ordering()
    js_cases()
    js_protocol_cases()
    # `matches` specifically represents null filename and swapped rename/change semantics.
    # The Python driver intentionally ignores eventType, so JS direct import verifies only its finite matcher.
    print('PASS: parent-watch protocol/order, sync versus async refusal, pipes/cleanup, identity and sanitization')


if __name__ == '__main__':
    main()
