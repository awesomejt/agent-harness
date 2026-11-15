#!/usr/bin/env python3
"""D095 opt-in disposable no-auth warning diagnostic; setup review precedes launch."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from antigravity_feasibility import LIMIT, TIMEOUT, check, signal_group
import chatgpt_230_observer as base
from chatgpt_230_source_audit import audit, verify_files
import chatgpt_230_warning_log as log
from chatgpt_contained import diagnostic
from chatgpt_retained_state import acquire, create_root, lock_probe

MANIFEST = Path(__file__).resolve().parents[2] / 'docs/evidence/p7-9-230-warning-source-manifest.json'


@contextmanager
def server(executable, project, env, sandbox, port, windows, pipes):
    """Keep bounded private pipes and an observed lifetime; always reap the group."""
    started = time.time()
    child = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', sandbox, str(executable),
                              'serve', '--stdio', '--hostname', '127.0.0.1', '--port', str(port)],
                             cwd=project, env=env, start_new_session=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ready, lock = queue.Queue(), threading.Lock()
    output = {'out': bytearray(), 'err': bytearray()}
    state = {'bytes': 0, 'overflow': False, 'read_error': False}

    def drain(pipe, label):
        announced = False
        try:
            while True:
                chunk = os.read(pipe.fileno(), 65536)
                if not chunk:
                    break
                with lock:
                    state['bytes'] += len(chunk)
                    if state['bytes'] > LIMIT:
                        state['overflow'] = True
                    if not state['overflow']:
                        output[label].extend(chunk)
                if state['overflow']:
                    signal_group(child.pid, signal.SIGKILL)
                    break
                if label == 'out' and not announced and b'\n' in output['out']:
                    ready.put(bytes(output['out']).split(b'\n', 1)[0])
                    announced = True
        except Exception:
            state['read_error'] = True
        finally:
            if label == 'out' and not announced:
                ready.put(None)

    threads = [threading.Thread(target=drain, args=(pipe, label), daemon=True)
               for pipe, label in ((child.stdout, 'out'), (child.stderr, 'err'))]
    for thread in threads:
        thread.start()
    first = None
    try:
        first = ready.get(timeout=TIMEOUT)
        try:
            valid = first is not None and json.loads(first) == {'url': f'http://127.0.0.1:{port}'}
        except (ValueError, TypeError):
            valid = False
        base.require(valid, 'server-readiness')
        check(child.poll() is None and not state['overflow'] and not state['read_error'])
        yield f'http://127.0.0.1:{port}'
        check(child.poll() is None)
    finally:
        close_error = False
        try:
            try:
                child.stdin.close()
            except OSError:
                close_error = True
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                signal_group(child.pid, signal.SIGTERM)
        finally:
            try:
                signal_group(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
            finally:
                windows['SERVER'] = (started, time.time())
                for thread in threads:
                    thread.join(timeout=2)
                child.stdout.close()
                child.stderr.close()
        check(all(not thread.is_alive() for thread in threads))
        check(not close_error and not state['overflow'] and not state['read_error'] and child.returncode == 0)
        check(first is not None and bytes(output['out']) == first + b'\n')
        pipes['SERVER'] = bytes(output['err'])


def client(runtime, project, env, sandbox, name, url, windows, pipes):
    label = {'config': 'DEBUG_CONFIG', 'agents': 'DEBUG_AGENTS'}[name]
    started = time.time()
    raw, err = diagnostic(runtime, project, env, sandbox, ('debug', name), url)
    windows[label] = (started, time.time())  # capture() requires successful child exit/reap.
    pipes[label] = err
    return raw


def targets(work, home, project):
    # Only exact fixture paths existing before launch are eligible warning targets.
    value = {str(path): 'OTHER_OWNED' for path in work.rglob('*')}
    value.update({str(work): 'OTHER_OWNED', str(home / 'repo'): 'PARENT_REPO',
                  str(project): 'PROJECT', str(work / 'CONFIG/opencode'): 'GLOBAL_CONFIG'})
    return value


def evaluate(raw, expected, owned_targets, windows, pipes):
    # Pipes remain private. No plaintext stderr allowlist or diagnostic fallback.
    if set(pipes) != {'SERVER', 'DEBUG_CONFIG', 'DEBUG_AGENTS'} or any(pipes.values()):
        raise base.Refusal('stderr')
    return log.classify(raw, expected, owned_targets, windows=windows)


def log_controls(raw, work):
    # Strict parse/provenance has already succeeded; preserve every non-warning
    # D094 log/filesystem gate even when the classifier found a warning.
    watches, spawns, _ = base.old.log_inventory(raw.decode('utf-8'), work)
    base.require(not any(message == 'watcher failed' for _, _, message in watches), 'watcher')
    base.require(('MACHINE_PARENT', 'entries', 'watcher started') in watches, 'machine-parent-watch')
    base.require(set(spawns) <= {('git', 'rev-parse')}, 'spawn')
    base.require(not any(path.name == 'node_modules' for path in work.rglob('*')), 'node-modules')
    base.require(not any((work / 'denied-bin').iterdir()), 'mcp-command')


def run_case(executable, builtin, listing_denied):
    with tempfile.TemporaryDirectory(prefix='ah-230-warning-') as directory:
        work, _ = create_root(Path(directory).resolve())
        lock = acquire(work)
        check(lock is not None)
        try:
            lock_probe(work)
            runtime = work / 'opencode-cli'
            shutil.copy2(executable, runtime)
            base.require(hashlib.sha256(runtime.read_bytes()).hexdigest() == base.SHA256, 'executable-pin')
            old = base.old
            home, project, env, password = old.build(work, True, False)
            content = json.loads(env['OPENCODE_CONFIG_CONTENT'])
            content['permissions'] = base.DENY
            env['OPENCODE_CONFIG_CONTENT'] = json.dumps(content)
            old.static_guards(work, home, project, env)
            owned_targets = targets(work, home, project)
            port = old.fresh_port()
            sandbox = base.policy(work, port, home, True, listing_denied)
            wanted = old.expected(True, False)
            windows, pipes = {}, {}
            with server(runtime, project, env, sandbox, port, windows, pipes) as url:
                observer = base.Observer(port, password, project)
                check(observer.locations() == [])
                current = base.settle(observer, work, builtin, wanted)
                check(observer.locations() == [str(project)])
                raw = client(runtime, project, env, sandbox, 'config', url, windows, pipes)
                documents = {old.owned_relative(s['path'], (work,)) for s in json.loads(raw)
                             if s.get('type') == 'document' and 'path' in s}
                check(documents == {'CONFIG/opencode/opencode.json', 'home/repo/opencode.json',
                                    'home/repo/project/opencode.json'})
                raw = client(runtime, project, env, sandbox, 'agents', url, windows, pipes)
                agents = json.loads(raw)
                expected_agents = {'ah-global-agent', 'ah-project-agent', 'ah-parent-agent'}
                check({a['id'] for a in agents} & expected_agents == expected_agents)
                for agent in agents:
                    rules = agent['permissions']
                    index = [i for i in range(len(rules)) if rules[i:i + len(base.DENY)] == base.DENY]
                    check(index and all(r['effect'] == 'deny' for r in rules[index[-1] + len(base.DENY):]))
            expected = {'SERVER': ['serve', '--stdio', '--hostname', '127.0.0.1', '--port', str(port)],
                        'DEBUG_CONFIG': ['debug', 'config', '--server', url],
                        'DEBUG_AGENTS': ['debug', 'agents', '--server', url]}
            raw = log.read_log(work / 'DATA/opencode/log/opencode.log', work)
            summary = evaluate(raw, expected, owned_targets, windows, pipes)
            log_controls(raw, work)
            check(len(current[1]) == base.PUBLISHED_INTEGRATION_COUNT)
            # A warning classification is diagnostic evidence only, always a refusal.
            print(json.dumps({'listing_denied': listing_denied, 'diagnostic': summary}, sort_keys=True), flush=True)
            base.require(not summary['warnings'], 'runtime-warning')
            return summary
        finally:
            os.close(lock)


def qualify(source):
    observation = audit(source)
    manifest = json.loads(MANIFEST.read_text())
    check(manifest['kind'] == 'p7-9-230-warning-source/v1' and
          manifest['source_commit'] == observation['source_commit'])
    verify_files(source.resolve() / 'packages', manifest['files'])
    # Classifier additionally verifies each finite message/severity against these bytes.
    log.verify_messages(source.resolve() / 'packages')
    return frozenset(observation['plugins']['ids'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='clean official v2.3.0 checkout')
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path(base.old.PYTHON).is_file())
    builtin = qualify(args.source)
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-230-warning-binary-') as directory:
        executable = Path(directory).resolve() / 'opencode-cli'
        shutil.copy2(installed, executable)
        base.require(hashlib.sha256(executable.read_bytes()).hexdigest() == base.SHA256, 'executable-pin')
        print('START: pinned disposable transport/containment controls', flush=True)
        base.transport_controls(executable)
        print('START: listing-allowed diagnostic control', flush=True)
        run_case(executable, builtin, False)
        print('PASS: listing-allowed diagnostic control', flush=True)
        print('START: listing-denied case-3 diagnostic', flush=True)
        run_case(executable, builtin, True)
        print('PASS: diagnostic non-reproduction; historical cause remains unknown', flush=True)
    print('LIMIT: full matrix/catalog/retained/authenticated qualification remains pending')


if __name__ == '__main__':
    try:
        main()
    except (base.Refusal, log.Refusal) as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('REFUSED: control-gate; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
