#!/usr/bin/env python3
"""Disposable 2.3.0 no-auth observer/containment qualification. No retained-root input."""
import argparse
from contextlib import ExitStack
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import time

from antigravity_feasibility import capture, check
from chatgpt_230_source_audit import audit
from chatgpt_contained import diagnostic, network_controls, owned_server, spawn_controls
import chatgpt_installed_observer as old
from chatgpt_retained_state import (
    acquire, create_root, integration_digest, lock_probe, redact_integrations,
    PUBLISHED_INTEGRATION_COUNT, PUBLISHED_INTEGRATION_DIGEST,
)

SHA256 = '95af97f3638e0f0c0e6d4ae6b9b9ec546dde49a570344365ea60fab22e602db7'
INTEGRATION = '/api/integration'
PROVIDER = '/api/provider'
DENY = [{'action': '*', 'resource': '*', 'effect': 'deny'},
        {'action': 'external_directory', 'resource': '*', 'effect': 'deny'}]


class Refusal(RuntimeError):
    """Only static diagnostic codes may leave the experiment."""


def require(value, code):
    if not value:
        raise Refusal(code)


class StartupPending(RuntimeError):
    """Only the activation barrier's initial connection can be retried."""


class Observer(old.Observer):
    allowed = dict(old.ALLOWED, **{INTEGRATION: True, PROVIDER: True})


def resources(observer, work):
    result = {}
    for kind, route in old.KINDS.items():
        items = observer.get(route)
        if kind != 'skill':
            result[kind] = old.redact(kind, items, (work,))
        else:
            check(isinstance(items, list))
            record = []
            for item in items:
                check(isinstance(item, dict) and {'id', 'name', 'path', 'content'} <= set(item)
                      <= {'id', 'name', 'description', 'autoinvoke', 'path', 'content'})
                check(isinstance(item['content'], str))
                identifier, path = item['id'], item['path']
                if identifier in old.BUILTIN_SKILLS:
                    check(path == f'skill://{identifier}/SKILL.md')
                else:
                    path = old.owned_relative(path, (work,))
                body = item['content'].encode()
                record.append((identifier, item['name'], path, hashlib.sha256(body).hexdigest(), len(body)))
            result[kind] = sorted(record)
    return result


def validate(current, builtin, wanted, late=False):
    """Unsafe observations refuse even when activation/sentinels are incomplete."""
    view, integrations = current
    # Connection refusal precedes inventory/readiness. Never wait away a connection.
    require(not any(connections for _, connections in integrations.values()), 'connection')
    require(len(integrations) == PUBLISHED_INTEGRATION_COUNT and
            integration_digest(integrations) == PUBLISHED_INTEGRATION_DIGEST, 'integration-set')
    require(not any(method[0] == 'command' for methods, _ in integrations.values() for method in methods),
            'command-method')
    plugins = view['plugin']
    require(len({p[0] for p in plugins}) == len(plugins), 'duplicate-plugin')
    require(all(p[0] in builtin and p[1:] == ('builtin', None, 'active') for p in plugins), 'plugin')
    commands, skills, mcp = wanted
    for kind, names in (('command', commands), ('skill', skills)):
        identifiers = [item[0] for item in view[kind]]
        require(len(set(identifiers)) == len(identifiers) and set(identifiers) <= names, 'resource')
    require(len(set(view['mcp'])) == len(view['mcp']) and set(view['mcp']) <= mcp, 'mcp')
    require(all(s[0] == s[1] for s in view['skill'] if s[0] not in old.BUILTIN_SKILLS), 'skill-name')
    complete = (old.plugins_ready(plugins, builtin) and {c[0] for c in view['command']} == commands
                and {s[0] for s in view['skill']} == skills and set(view['mcp']) == mcp)
    return complete and (not late or ('ah-global-command', 'replaced global sentinel') in view['command'])


def observe(observer, work):
    # The pinned provider handler awaits plugin activation; integration.list does not.
    try:
        providers = observer.get(PROVIDER)
    except (ConnectionRefusedError, ConnectionResetError, http.client.RemoteDisconnected):
        raise StartupPending from None
    check(isinstance(providers, list))
    identifiers = set()
    for provider in providers:
        required = {'id', 'name', 'activation', 'package'}
        optional = {'canonical', 'integrationID', 'compatibility', 'settings', 'headers', 'body'}
        check(isinstance(provider, dict) and required <= set(provider) <= required | optional)
        check(all(isinstance(provider[k], str) for k in required))
        check(provider['activation'] in ('auto', 'enabled', 'disabled') and provider['id'] not in identifiers)
        check(all(isinstance(provider[k], dict) for k in ('settings', 'headers', 'body', 'compatibility') if k in provider))
        check(all(isinstance(provider[k], str) for k in ('canonical', 'integrationID') if k in provider))
        identifiers.add(provider['id'])
    # Discard provider bodies; no credential/identity/setting fields are recorded.
    del providers
    items = observer.get(INTEGRATION)
    integrations, _ = redact_integrations(items)
    require(all('metadata' not in item for item in items), 'integration-metadata')
    require(not any(connections for _, connections in integrations.values()), 'connection')
    return resources(observer, work), integrations


def settle(observer, work, builtin, wanted, late=False, clock=time.monotonic, sleep=time.sleep):
    deadline, previous = clock() + old.WINDOW, None
    started = False
    while clock() < deadline:
        try:
            current = observe(observer, work)
        except StartupPending:
            require(not started, 'barrier-reset')
            previous = None
            sleep(old.POLL)
            continue
        started = True
        # Unknown HTTP/schema/timeout failures are not startup readiness exceptions.
        if validate(current, builtin, wanted, late):
            if current == previous:
                return current
            previous = current
            sleep(old.SETTLE)
        else:
            previous = None
            sleep(old.POLL)
    raise Refusal('readiness-timeout')


def policy(work, port, home, ancestor_denied=True, listing_denied=False):
    value = old.combined_profile(work, port, old.ancestor_denials(home, () if ancestor_denied else (work.parent,)))
    if listing_denied:
        value += '(deny file-read-data (literal ' + json.dumps(str(home / 'repo')) + '))'
    return value


def logs(work):
    watches, spawns, problems = old.log_inventory((work / 'DATA/opencode/log/opencode.log').read_text(), work)
    require(not problems, 'runtime-warning')
    require(not any(message == 'watcher failed' for _, _, message in watches), 'watcher')
    require(('MACHINE_PARENT', 'entries', 'watcher started') in watches, 'machine-parent-watch')
    require(set(spawns) <= {('git', 'rev-parse')}, 'spawn')
    require(not any(path.name == 'node_modules' for path in work.rglob('*')), 'node-modules')
    require(not any((work / 'denied-bin').iterdir()), 'mcp-command')
    return {'watches': watches, 'spawns': spawns, 'warnings': problems}


def run_case(executable, builtin, project_on, claude_on, reload, ancestor_denied=True, listing_denied=False):
    with tempfile.TemporaryDirectory(prefix='ah-230-observer-') as directory:
        work, _ = create_root(Path(directory).resolve())
        lock = acquire(work)
        check(lock is not None)
        try:
            lock_probe(work)
            runtime = work / 'opencode-cli'
            shutil.copy2(executable, runtime)
            check(hashlib.sha256(runtime.read_bytes()).hexdigest() == SHA256)
            home, project, env, password = old.build(work, project_on, claude_on)
            content = json.loads(env['OPENCODE_CONFIG_CONTENT'])
            content['permissions'] = DENY
            env['OPENCODE_CONFIG_CONTENT'] = json.dumps(content)
            old.static_guards(work, home, project, env)
            port = old.fresh_port()
            sandbox = policy(work, port, home, ancestor_denied, listing_denied)
            wanted = old.expected(project_on, claude_on)
            with owned_server(runtime, project, env, sandbox, port) as url:
                observer = Observer(port, password, project)
                check(observer.locations() == [])
                current = settle(observer, work, builtin, wanted)
                check(observer.locations() == [str(project)])
                raw, _ = diagnostic(runtime, project, env, sandbox, ('debug', 'config'), url)
                documents = {old.owned_relative(s['path'], (work,)) for s in json.loads(raw)
                             if s.get('type') == 'document' and 'path' in s}
                check(documents == {'CONFIG/opencode/opencode.json'} | (
                    {'home/repo/opencode.json', 'home/repo/project/opencode.json'} if project_on else set()))
                raw, _ = diagnostic(runtime, project, env, sandbox, ('debug', 'agents'), url)
                agents = json.loads(raw)
                expected_agents = {'ah-global-agent'} | ({'ah-project-agent', 'ah-parent-agent'} if project_on else set())
                check({a['id'] for a in agents} & {'ah-global-agent', 'ah-project-agent', 'ah-parent-agent'} == expected_agents)
                for agent in agents:
                    rules = agent['permissions']
                    index = [i for i in range(len(rules)) if rules[i:i + len(DENY)] == DENY]
                    check(index and all(r['effect'] == 'deny' for r in rules[index[-1] + len(DENY):]))
                if reload:
                    old.late_changes(work, home, project)
                    commands, skills, mcp = wanted
                    wanted = (commands | {'ah-late-command'} | ({'ah-late-project-command'} if project_on else set()),
                              skills | {'ah-late-skill', 'ah-late-agents-skill'} |
                              ({'ah-late-project-skill'} if project_on else set()) |
                              ({'ah-late-claude-skill'} if claude_on else set()),
                              mcp | {('ah-late-mcp', 'disabled')} |
                              ({('ah-ancestor-mcp', 'disabled')} if project_on and not ancestor_denied else set()))
                    current = settle(observer, work, builtin, wanted, late=True)
                    check(observer.locations() == [str(project)])
            inventory = logs(work)
            return {'project': project_on, 'claude': claude_on, 'reload': reload,
                    'ancestor_denied': ancestor_denied, 'listing_denied': listing_denied,
                    'integrations': len(current[1]), 'connections': 0, **inventory}
        finally:
            os.close(lock)


def discovery_controls(executable):
    """Pair the pinned discovery algorithm's listing and direct-probe fallback branches."""
    with tempfile.TemporaryDirectory(prefix='ah-230-discovery-') as directory:
        work = Path(directory).resolve()
        parent = work / 'parent'
        parent.mkdir()
        (parent / 'opencode.json').write_text('AH_INERT_DISCOVERY')
        fixture = work / 'discovery.js'
        fixture.write_text("""const fs=require('node:fs'), path=require('node:path');
const parent=process.argv[2];let entries;let branch='listing';
try {entries=new Set(fs.readdirSync(parent).map(x=>x.toLowerCase()))} catch {branch='fallback'}
let read='missing';
if (!entries || entries.has('opencode.json')) {
 try {read=fs.readFileSync(fs.realpathSync(path.join(parent,'opencode.json')),'utf8')==='AH_INERT_DISCOVERY'?'canary':'wrong'}
 catch(e) {read=e.code}
}
console.log(JSON.stringify({branch,read}));""")
        env = {'HOME': str(work / 'home'), 'TMPDIR': str(work), 'PATH': '/usr/bin:/bin', 'BUN_BE_BUN': '1'}
        for listing_denied in (False, True):
            for candidate_denied in (False, True):
                sandbox = old.combined_profile(work, old.fresh_port())
                if listing_denied:
                    sandbox += '(deny file-read-data (literal ' + json.dumps(str(parent)) + '))'
                if candidate_denied:
                    sandbox += '(deny file-read* (literal ' + json.dumps(str(parent / 'opencode.json')) + '))'
                out, err = capture(['/usr/bin/sandbox-exec', '-p', sandbox, str(executable), str(fixture), str(parent)], work, env)
                check(not err and json.loads(out) == {
                    'branch': 'fallback' if listing_denied else 'listing',
                    'read': 'EPERM' if candidate_denied else 'canary'})
        print('PASS: Bun listing/fallback discovery branches and candidate read denials paired', flush=True)


def transport_controls(executable):
    with tempfile.TemporaryDirectory(prefix='ah-230-transport-') as directory, ExitStack() as cleanup:
        work, _ = create_root(Path(directory).resolve())
        lock = acquire(work)
        check(lock is not None)
        cleanup.callback(os.close, lock)
        lock_probe(work)
        home, project, env, password = old.build(work, False, False)
        old.static_guards(work, home, project, env)
        # The old spawn fixture is version-neutral but asserts the embedded Bun
        # baseline; a drift is a stop, never an implicit re-pin.
        spawn_controls(work, executable, env)
        port = old.fresh_port()
        with tempfile.TemporaryDirectory(prefix='.ah-230-read-', dir=Path.home()) as protected:
            target = Path(protected) / 'sentinel'
            target.write_text('AH_READ_DENIAL_SENTINEL')
            with tempfile.TemporaryDirectory(prefix='ah-230-write-') as fence:
                network_controls(work, policy(work, port, home), env, port, target, Path(fence) / 'write')
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            reservation.listen(1)
            port = reservation.getsockname()[1]
            entered = False
            try:
                with owned_server(executable, project, env, policy(work, port, home), port):
                    entered = True
            except RuntimeError:
                pass
            check(not entered)
            reservation.setblocking(False)
            try:
                connection, _ = reservation.accept()
            except BlockingIOError:
                pass
            else:
                connection.close()
                check(False)
        print('PASS: occupied port refused without a connection', flush=True)
        port = old.fresh_port()
        sandbox = policy(work, port, home)
        with owned_server(executable, project, env, sandbox, port) as url:
            for password, message in ((None, b'requires a password'), ('AH_WRONG_SYNTHETIC_PASSWORD', b'rejected the password')):
                unauthorized = dict(env)
                if password is None:
                    del unauthorized['OPENCODE_PASSWORD']
                else:
                    unauthorized['OPENCODE_PASSWORD'] = password
                out, err = diagnostic(executable, project, unauthorized, sandbox, ('debug', 'config'), url, status=1)
                check(not out.strip() and message in err)
        print('PASS: absent and wrong private-server passwords refused', flush=True)
        old.bun_controls(executable, old.fresh_port())
        discovery_controls(executable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='clean official v2.3.0 checkout')
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path(old.PYTHON).is_file())
    source = audit(args.source)
    builtin = frozenset(source['plugins']['ids'])
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-230-binary-') as directory:
        executable = Path(directory).resolve() / 'opencode-cli'
        shutil.copy2(installed, executable)
        require(hashlib.sha256(executable.read_bytes()).hexdigest() == SHA256, 'executable-pin')
        print('START: pinned disposable transport/containment controls', flush=True)
        transport_controls(executable)
        cases = []
        for case in ((False, False, True, True, False), (True, False, False, True, False),
                     (True, False, False, True, True), (False, True, False, True, False),
                     (True, True, True, True, False), (True, False, True, False, False)):
            print('START: disposable resource/inventory case ' + str(len(cases) + 1), flush=True)
            cases.append(run_case(executable, builtin, *case))
            print('PASS: disposable resource/inventory case ' + str(len(cases)), flush=True)
    print(json.dumps({'source_commit': source['source_commit'], 'executable_sha256': SHA256, 'cases': cases}, sort_keys=True))
    print('LIMIT: disposable no-auth qualification only; catalog/retained/authenticated gates remain open')


if __name__ == '__main__':
    try:
        main()
    except Refusal as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('REFUSED: control-gate; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
