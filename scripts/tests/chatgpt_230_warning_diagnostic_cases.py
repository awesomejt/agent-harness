#!/usr/bin/env python3
"""Offline diagnostic supervision/order refusals; never launches installed OpenCode."""
from contextlib import contextmanager
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_warning_diagnostic as helper


def rejects(action, code=None):
    try:
        action()
    except (RuntimeError, ValueError) as error:
        if code is not None:
            assert str(error) == code
        return
    raise AssertionError('unsafe diagnostic accepted')


def main():
    expected = {'SERVER': [], 'DEBUG_CONFIG': [], 'DEBUG_AGENTS': []}
    pipes = dict.fromkeys(expected, b'')
    with patch.object(helper.log, 'classify', return_value={'warnings': []}) as classify:
        assert helper.evaluate(b'private', expected, {}, {}, pipes) == {'warnings': []}
        assert classify.call_count == 1
        for label in pipes:
            rejects(lambda: helper.evaluate(b'', expected, {}, {}, dict(pipes, **{label: b'SECRET'})), 'stderr')
        rejects(lambda: helper.evaluate(b'', expected, {}, {}, {}), 'stderr')
        assert classify.call_count == 1

    # Exercise actual pipe threads/lifetime/reaping with inert Python, no sandbox/OpenCode.
    original = subprocess.Popen
    child_pids = []
    with tempfile.TemporaryDirectory(prefix='ah-warning-supervision-') as directory:
        work = Path(directory)
        def start(script):
            def launch(*args, **kwargs):
                child = original([sys.executable, '-c', script], **kwargs)
                child_pids.append(child)
                return child
            return launch
        clean = "import sys;print('{\"url\":\"http://127.0.0.1:12345\"}',flush=True);sys.stdin.read()"
        for stderr in ('', 'SECRET_STDERR'):
            windows, captured = {}, {}
            script = clean.replace('sys.stdin.read()',
                                   'sys.stderr.write(' + repr(stderr) + ');sys.stderr.flush();sys.stdin.read()')
            with patch.object(helper.subprocess, 'Popen', side_effect=start(script)):
                with helper.server(work/'unused', work, {}, '', 12345, windows, captured) as url:
                    assert url == 'http://127.0.0.1:12345'
            assert windows['SERVER'][0] <= windows['SERVER'][1] <= time.time()
            assert captured == {'SERVER': stderr.encode()}
            assert child_pids[-1].poll() == 0
        for script in ("print('SECRET_BAD_START',flush=True)",
                       clean.replace('sys.stdin.read()', "print('EXTRA_STDOUT',flush=True);sys.stdin.read()")):
            with patch.object(helper.subprocess, 'Popen', side_effect=start(script)):
                def run():
                    with helper.server(work/'unused', work, {}, '', 12345, {}, {}):
                        pass
                rejects(run)
            assert child_pids[-1].poll() is not None
        # A failed stdin close must still reap the process and close both pipes.
        def broken_close(*args, **kwargs):
            child = start(clean)(*args, **kwargs)
            original_stdin = child.stdin
            class Broken:
                def close(self):
                    original_stdin.close()
                    raise BrokenPipeError('PRIVATE_CLOSE_ERROR')
            child.stdin = Broken()
            return child
        with patch.object(helper.subprocess, 'Popen', side_effect=broken_close):
            def close_failure():
                with helper.server(work/'unused', work, {}, '', 12345, {}, {}):
                    pass
            rejects(close_failure)
            assert child_pids[-1].poll() is not None
            assert child_pids[-1].stdout.closed and child_pids[-1].stderr.closed
        with patch.object(helper, 'LIMIT', 128), patch.object(helper.subprocess, 'Popen', side_effect=start(
                clean.replace('sys.stdin.read()', "sys.stderr.write('x'*1024);sys.stderr.flush();sys.stdin.read()"))):
            def overflow():
                with helper.server(work/'unused', work, {}, '', 12345, {}, {}):
                    time.sleep(.1)
            rejects(overflow)
            assert child_pids[-1].poll() is not None

    # Existing containment gates must run for both clean and warning results.
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        (work/'denied-bin').mkdir()
        good_watch = [('MACHINE_PARENT', 'entries', 'watcher started')]
        with patch.object(helper.base.old, 'log_inventory', return_value=(good_watch, [('git','rev-parse')], [])):
            helper.log_controls(b'', work)
            (work/'node_modules').mkdir()
            rejects(lambda: helper.log_controls(b'', work), 'node-modules')
            (work/'node_modules').rmdir()
            (work/'denied-bin'/'unexpected').touch()
            rejects(lambda: helper.log_controls(b'', work), 'mcp-command')
            (work/'denied-bin'/'unexpected').unlink()
        for watches, spawns, code in (([], [], 'machine-parent-watch'),
                                      (good_watch, [('unexpected', 'SECRET')], 'spawn'),
                                      (good_watch+[('OTHER_OWNED', 'entries', 'watcher failed')], [], 'watcher')):
            with patch.object(helper.base.old, 'log_inventory', return_value=(watches, spawns, [])):
                rejects(lambda: helper.log_controls(b'', work), code)

    # Keep real fixture creation/cleanup, isolate all runtime and observation boundaries.
    roots = []
    @contextmanager
    def fake_server(runtime, project, env, sandbox, port, windows, captured):
        windows['SERVER'] = (0, 1)
        captured['SERVER'] = b''
        yield 'http://127.0.0.1:12345'
    class Observer:
        def __init__(self, *args): self.calls = 0
        def locations(self):
            self.calls += 1
            return [] if self.calls == 1 else [str(roots[-1]/'home/repo/project')]
    def client(runtime, project, env, sandbox, name, url, windows, captured):
        windows['DEBUG_' + name.upper()] = (0, 1)
        captured['DEBUG_' + name.upper()] = b''
        if name == 'config':
            return json.dumps([{'type': 'document', 'path': str(roots[-1]/relative)} for relative in
                               ('CONFIG/opencode/opencode.json', 'home/repo/opencode.json',
                                'home/repo/project/opencode.json')]).encode()
        return json.dumps([{'id': name, 'permissions': helper.base.DENY} for name in
                           ('ah-global-agent', 'ah-project-agent', 'ah-parent-agent')]).encode()
    create = helper.create_root
    def track(parent):
        result = create(parent)
        roots.append(result[0])
        return result
    class Digest:
        def hexdigest(self): return helper.base.SHA256
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory)/'inert'
        executable.write_text('not an executable')
        for warnings in ([], [{'process': 'SERVER', 'family': 'WATCH_START', 'target': 'PARENT_REPO', 'count': 1}]):
            output = io.StringIO()
            with patch.object(helper, 'create_root', side_effect=track), \
                 patch.object(helper, 'lock_probe'), patch.object(helper, 'server', fake_server), \
                 patch.object(helper, 'client', client), patch.object(helper.base, 'Observer', Observer), \
                 patch.object(helper.base, 'settle', return_value=({}, dict.fromkeys(range(236)))), \
                 patch.object(helper.log, 'read_log', return_value=b'PRIVATE_LOG'), \
                 patch.object(helper, 'evaluate', return_value={'warnings': warnings}) as evaluate, \
                 patch.object(helper, 'log_controls') as old_logs, \
                 patch.object(helper.hashlib, 'sha256', return_value=Digest()), \
                 patch('sys.stdout', output):
                if warnings:
                    rejects(lambda: helper.run_case(executable, frozenset(), True), 'runtime-warning')
                    assert old_logs.call_count == 1
                else:
                    helper.run_case(executable, frozenset(), False)
                    assert old_logs.call_count == 1
                assert set(evaluate.call_args.args[3]) == {'SERVER', 'DEBUG_CONFIG', 'DEBUG_AGENTS'}
            assert not roots[-1].exists()
            assert 'PRIVATE_LOG' not in output.getvalue()
            assert json.loads(output.getvalue())['diagnostic']['warnings'] == warnings

    # Main must stop before denial when the listing-allowed control refuses.
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory)/'inert'
        executable.write_text('not an executable')
        with patch('sys.argv', ['helper', '--source', directory]), \
             patch.object(helper, 'qualify', return_value=frozenset()), \
             patch.object(helper.shutil, 'which', return_value=str(executable)), \
             patch.object(helper.hashlib, 'sha256', return_value=Digest()), \
             patch.object(helper.base, 'transport_controls') as transport, \
             patch.object(helper, 'run_case', side_effect=helper.base.Refusal('runtime-warning')) as run, \
             patch('sys.stdout', io.StringIO()):
            rejects(helper.main, 'runtime-warning')
            assert transport.call_count == run.call_count == 1
            assert run.call_args.args[-1] is False
    print('PASS: diagnostic pipes, supervision/cleanup, refusal output, inherited gate and pair ordering')


if __name__ == '__main__':
    main()
