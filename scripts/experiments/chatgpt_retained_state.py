#!/usr/bin/env python3
"""Opt-in pinned macOS no-auth OpenCode retained-state preflight experiment on owned roots (D077)."""
import argparse
import base64
import fcntl
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

from antigravity_feasibility import capture, check
from chatgpt_contained import diagnostic, network_controls, owned_server, PYTHON
from chatgpt_feasibility import SHA256
from chatgpt_installed_observer import (
    ALLOWED, BODY_LIMIT, KINDS, POLL, REQUEST_TIMEOUT, SETTLE, WINDOW, Observer, ancestor_denials,
    array_entries, build, combined_profile, expected, expected_plugins, fresh_port, log_inventory,
    imports, module_file, owned_relative, plugins_ready, redact, resolve_entries, static_guards, verify_source)

# Pinned files this helper consumes beyond the D075/D076/D077 tables; all paths are under packages/.
FINGERPRINTS = {
    'core/src/wellknown/plugin.ts': 'dd71fc144c5c99303f61cfd7d61ffd516c418f5bac3ebcac6433d4f1ab014bed',
    'core/src/plugin/models-dev.ts': '5b456026359976407f2be11456d1974ee795ce3cc2a6ec41b0d0d0ac6a96ef74',
    'core/src/models-dev/snapshot.txt': '5d5740c70071aa628d1efe317f6885faf1f20b32a9fcb502553f57cce15cf9f1',
    'core/src/console-access.ts': '7ae41c74078b9c5a3887bec4908e9ee0ab00e632d3ce1f5eaf37d9da23c0eec5',
    'cli/src/server-process.ts': '37e89b2eed32bc9324f4cdf0a639387dfe6fc0ef8e6f37fc33c43987869b4bc2',
    'core/src/config.ts': 'df2d83dff70a6cb3ef3e3a1d735bd397facc96ccf15794c6eb1a3646cef17390',
    'schema/src/provider.ts': 'e06382adea1a5823aea72024461064319647117c8b08abad72490efd6191a404',
    'core/src/plugin/provider/claude-agent/integration.ts': 'e4b31a6ef179823f1520f88914d260734d28b70d66cc6ef691657815eda1e1c3',
    'core/src/plugin/provider/claude-agent/provider.ts': 'b7cb78d7962c1f871cb54a5b1c299a3dd34b62dc6c6ce668fd85a8c3954433e3',
    # D077 table, re-verified because this helper depends on them.
    'core/src/wellknown.ts': '1983793d5ce0fbc2abec598d8f95b70b0ba118430b2ff9cce2205c4d0938c52b',
    'core/src/plugin/provider/opencode.ts': '1a757ab84e8dc2d96de1ebe75b64cbe4b8b1e82bcea07bf9ead681977d63f4ed',
    'core/src/integration.ts': 'ec5f1299df972928baf457b277ecb2146acd1b429870b9e61f96eb96a3f82ebe',
    'server/src/handlers/integration.ts': 'f2f69342bfaa56706466b547f237433c8135ecc87c2639942544d44a7fccbe78',
    'protocol/src/groups/integration.ts': '3f3010e8b66f378b9a862b789bfc079369f5ce7c9a9b424ab2cfbf8623aceeb1',
    'schema/src/integration.ts': '2cf903a147260a405fa87504a07e05e3a5536ae62d351ddbacb3142af3274c82',
    'schema/src/connection.ts': 'b8bec346b315e6ef36174945c6b62ac467465c2777d0666e103c90b9e55adbf8',
    'util/src/global-roots.ts': '6cdc234ac155e308dadeb62682c687468ba656fd463482d00fce025c9dc819b6',
    'cli/src/database-path.ts': '921368eee69db647d2973d7dc529e86a8942027ee0032d3acb112d6a55e6b9d7',
}
PLUGIN_DIGEST = '68e17ecbace37051b8813c683dbaa955321fa76477c847659fc1eb0b9a919e42'  # D076: 91 files.
INTEGRATION = '/api/integration'
SEED_ROUTES = {'wellknown': '/api/experimental/integration/wellknown',
               'console': '/api/integration/opencode/connect/key'}
MARKER = 'AH_SYNTHETIC_NON_SECRET_CONSOLE_MARKER'
OWNER = '.ah-owner'
LOCK = '.ah-lock'
ID_SHAPE = re.compile(r'[a-z0-9][a-z0-9._-]*')
PUBLISHED_INTEGRATION_COUNT = 236
PUBLISHED_INTEGRATION_DIGEST = '2cd1b632219bbd635a2f7a5911d6c0e36d7205d75cc4c85d751cb90081de73af'
# Warnings a seeded boot is expected to log; every other WARN/ERROR line fails the run.
WELLKNOWN_WARNING = ('WARN', 'failed to load wellknown manifest')       # core/src/wellknown.ts
WELLKNOWN_CONFIG = ('WARN', 'failed to load wellknown config')           # core/src/config.ts: no credential
CONSOLE_WARNING = ('WARN', 'failed to load OpenCode provider config')    # provider/opencode.ts: fetch denied


# --- Pinned-source cross-check --------------------------------------------------

def plugin_files(packages):
    internal = packages / 'core/src/plugin/internal.ts'
    seen = {internal}
    text = internal.read_text()
    for group in ('pre', 'post'):
        resolve_entries(packages, internal, array_entries(text, group), seen)
    digest = hashlib.sha256(b''.join(path.read_bytes() for path in sorted(seen))).hexdigest()
    check(digest == PLUGIN_DIGEST)
    return sorted(seen)


LITERAL = re.compile(r'integrationID:\s*"([^"]+)"|Integration\.ID\.make\("([^"]+)"\)|connection\.active\("([^"]+)"\)')
EDITOR = re.compile(r'(?:editor|integrations)\.update\("([^"]+)"')
CONSTANT = re.compile(r'integrationID:\s*Provider\.ID\.(\w+)\b')
ALIAS = re.compile(r'integrationID:\s*(?!Integration\.)([A-Z]\w*)\.ID\b(?!\.)')  # Not the schema type.


def provider_constants(packages):
    text = (packages / 'schema/src/provider.ts').read_text()
    return dict(re.findall(r'\n\s+(\w+): schema\.make\("([^"]+)"\)', text))


def literal_integrations(packages, files):
    """Integration IDs the built-in plugins name in source: string literals, `Provider.ID` constants and
    `<Module>.ID` aliases of them, in each plugin file and its one-hop relative imports."""
    constants = provider_constants(packages)
    scanned = set(files)
    for path in files:
        _, table = imports(packages, path)
        scanned |= {module_file(packages, path, spec) for spec, _ in table.values()
                     if spec.startswith('.') and spec.endswith('.js')}
    found = {}
    for path in sorted(scanned):
        text = path.read_text()
        names = [next(group for group in match if group) for match in LITERAL.findall(text)]
        if 'integration.transform' in text:
            names += EDITOR.findall(text)
        names += [constants[name] for name in CONSTANT.findall(text)]
        _, table = imports(packages, path)
        for alias in ALIAS.findall(text):
            check(alias in table)
            target = module_file(packages, path, table[alias][0]).read_text()
            match = re.search(r'\nexport const ID = Provider\.ID\.(\w+)\n', target)
            check(match is not None)
            names.append(constants[match.group(1)])
        for name in names:
            check(ID_SHAPE.fullmatch(name) is not None)
            found.setdefault(name, set()).add(str(path.relative_to(packages)))
    # The only `command` method registration in the built-ins is the well-known plugin.
    commands = [p for p in scanned if re.search(r'method:\s*\{[^{}]*?type:\s*"command"', p.read_text())]
    check([str(p.relative_to(packages)) for p in commands] == ['core/src/wellknown/plugin.ts'])
    return found


def snapshot_providers(packages):
    catalog = json.loads((packages / 'core/src/models-dev/snapshot.txt').read_text())
    check(isinstance(catalog, dict))
    return {key for key, value in catalog.items() if isinstance(value, dict) and value.get('env')}


# --- Observer, seeder and synthetic origin -------------------------------------

class PreflightObserver(Observer):
    """The D076 observer plus `integration.list` only (D077)."""

    allowed = dict(ALLOWED, **{INTEGRATION: True})


METHOD_KEYS = {'oauth': ({'id', 'type', 'label'}, {'form'}), 'command': ({'id', 'type', 'label', 'command'}, set()),
               'key': ({'type'}, {'label', 'form'}), 'external': ({'id', 'type', 'label'}, {'form'}),
               'env': ({'type', 'names'}, set())}
CONNECTION_KEYS = {'credential': ({'type', 'id', 'label', 'method'}, {'status'}),
                   'env': ({'type', 'name'}, {'status'})}


def shape(value, keys):
    required, optional = keys
    check(isinstance(value, dict) and required <= set(value) <= required | optional)


def redact_integrations(items):
    """Strict schema check. Keep IDs, method signatures and connection kinds; hash connection identity in memory."""
    check(isinstance(items, list))
    record, identities = {}, {}
    for item in items:
        shape(item, ({'id', 'name', 'methods', 'connections'}, {'metadata'}))
        identifier = item['id']
        check(isinstance(identifier, str) and identifier not in record)
        methods = []
        for method in item['methods']:
            check(isinstance(method, dict) and method.get('type') in METHOD_KEYS)
            shape(method, METHOD_KEYS[method['type']])
            methods.append((method['type'], method.get('id', '')))
        connections = []
        for connection in item['connections']:
            check(isinstance(connection, dict) and connection.get('type') in CONNECTION_KEYS)
            shape(connection, CONNECTION_KEYS[connection['type']])
            status = connection.get('status')
            if status is not None:
                shape(status, ({'status', 'message'}, {'url'}))
                check(status['status'] == 'needs_auth')
            check(connection.get('method', 'oauth') in ('key', 'oauth', 'external'))
            connections.append((connection['type'], connection.get('method', ''), status['status'] if status else ''))
            # Identity and label are reduced to a digest that is compared in memory and never recorded.
            identity = json.dumps([identifier, connection.get('id', connection.get('name')), connection.get('label')])
            identities.setdefault(identifier, set()).add(hashlib.sha256(identity.encode()).hexdigest())
        record[identifier] = (tuple(sorted(methods)), tuple(sorted(connections)))
    return record, identities


class Seeder:
    """Exactly two official POST routes, each with one synthetic payload shape (D077 experiment only)."""

    def __init__(self, port, password, location, origin=None, connect=http.client.HTTPConnection):
        check(type(port) is int and isinstance(password, str) and password and location.is_absolute())
        check(origin is None or re.fullmatch(r'http://127\.0\.0\.1:\d{1,5}', origin) is not None)
        self.port, self.location, self.origin, self.connect = port, location, origin, connect
        self.authorization = 'Basic ' + base64.b64encode(f'opencode:{password}'.encode()).decode()

    def post(self, kind):
        check(kind in SEED_ROUTES and (kind != 'wellknown' or self.origin is not None))
        payload = {'url': self.origin} if kind == 'wellknown' else {'key': MARKER, 'label': 'ah-synthetic'}
        query = '?' + urllib.parse.urlencode({'location[directory]': str(self.location)})
        connection = self.connect('127.0.0.1', self.port, timeout=REQUEST_TIMEOUT * 4)
        try:
            connection.request('POST', SEED_ROUTES[kind] + query, body=json.dumps(payload).encode(), headers={
                'Authorization': self.authorization, 'Connection': 'close', 'Content-Type': 'application/json'})
            response = connection.getresponse()
            body = response.read(BODY_LIMIT + 1)
            check(response.status == 204 and not body)
        finally:
            connection.close()


class SyntheticOrigin:
    """Harness-written well-known origin on a second owned loopback port; it serves one manifest."""

    def __init__(self, port, command):
        self.hits = {'manifest': 0, 'other': 0}
        manifest = json.dumps({'auth': {'command': [str(command)], 'env': 'AH_SYNTHETIC_TOKEN'}}).encode()
        hits = self.hits

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                found = self.path == '/.well-known/opencode'
                hits['manifest' if found else 'other'] += 1
                self.send_response(200 if found else 404)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(manifest) if found else 0))
                self.end_headers()
                if found:
                    self.wfile.write(manifest)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
        self.url = f'http://127.0.0.1:{port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        check(not self.thread.is_alive())


# --- Owned root, lock and preflight --------------------------------------------

def create_root(parent):
    """Exclusive mode-0700 root with an ownership marker; nothing is copied, linked or imported into it."""
    work = parent / 'work'
    work.mkdir(mode=0o700)  # Fails if it exists.
    check(work.stat().st_mode & 0o777 == 0o700)
    token = secrets.token_hex(16)
    descriptor = os.open(work / OWNER, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as marker:
        marker.write(token)
    return work, token


def env_from_owned_root(work, project_on=False, claude_skills_off=True):
    """Rebuild the D076/D077 boot environment for an existing owned root."""
    home = work / 'home'
    project = home / 'repo' / 'project'
    password = secrets.token_urlsafe(32)
    env = {'HOME': str(home), 'TMPDIR': str(work), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
           'NO_COLOR': '1', 'TERM': 'dumb', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
           'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_PASSWORD': password,
           'OPENCODE_CONFIG_CONTENT': json.dumps({'update': 'disable', 'share': 'disabled'})}
    for kind in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
        env['XDG_' + kind + '_HOME'] = str(work / kind)
    if not project_on:
        env['OPENCODE_DISABLE_PROJECT_CONFIG'] = 'true'
    if claude_skills_off:
        env['OPENCODE_DISABLE_CLAUDE_CODE_SKILLS'] = 'true'
    return home, project, env


def acquire(work):
    descriptor = os.open(work / LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


LOCK_PROBE = r"""
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDWR | os.O_NOFOLLOW)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print('refused')
else:
    print('acquired')
"""


def lock_probe(work):
    """A separate process tries the run lock without waiting."""
    result = subprocess.run([PYTHON, '-B', '-c', LOCK_PROBE, str(work / LOCK)], capture_output=True, text=True,
                            timeout=10, env={'PATH': '/usr/bin:/bin'})
    check(result.returncode == 0 and not result.stderr)
    return result.stdout.strip()


def root_shape(work, token, env):
    """Name-only checks before any launch. `auth.json` is never opened."""
    violations = []
    marker = work / OWNER
    if marker.is_symlink() or not marker.is_file() or marker.read_text() != token:
        violations.append('root-marker')
    if os.path.lexists(work / 'DATA' / 'opencode' / 'auth.json'):
        violations.append('legacy-auth-file')
    if 'OPENCODE_DB' in env or env.get('XDG_DATA_HOME') != str(work / 'DATA'):
        violations.append('database-override')
    return violations


def database_path(runtime, project, env, policy, work):
    raw, _ = diagnostic(runtime, project, env, policy, ('debug', 'paths'))
    paths = dict(line.split(None, 1) for line in raw.decode().splitlines() if line.strip())
    return paths['db'] == str(work / 'DATA' / 'opencode' / 'opencode.db')


def preflight(integrations, resources, documents, expected_set, builtin, login):
    """D077 invariants after boot. `login=False` is the no-auth variant used by this experiment."""
    violations = set()
    if set(integrations) != expected_set:
        violations.add('integration-set')
    for identifier, (_, connections) in integrations.items():
        if identifier == 'openai':
            want = (('credential', 'oauth', ''),) if login else ()
            if connections != want:
                violations.add('openai-connection')
        elif connections:
            violations.add('console-connection' if identifier == 'opencode' else 'other-connection')
    if login and 'openai' not in integrations:
        violations.add('openai-connection')
    commands, skills, mcp = expected(False, False)
    if not (plugins_ready(resources['plugin'], builtin) and {c[0] for c in resources['command']} == commands
            and {s[0] for s in resources['skill']} == skills and set(resources['mcp']) == mcp):
        violations.add('resources')
    if documents != {'CONFIG/opencode/opencode.json'}:
        violations.add('config-documents')
    return sorted(violations)


def view(observer, owned):
    resources = {kind: redact(kind, observer.get(path), owned) for kind, path in KINDS.items()}
    integrations, identities = redact_integrations(observer.get(INTEGRATION))
    return resources, integrations, identities


def settle_view(observer, owned, ready, clock=time.monotonic, sleep=time.sleep):
    """Poll until `ready` holds, then require two identical reads >= SETTLE apart (D075)."""
    deadline = clock() + WINDOW
    previous = None
    while clock() < deadline:
        current = view(observer, owned)
        if ready(current):
            if previous == current:
                return current
            previous = current
            sleep(SETTLE)
        else:
            previous = None
            sleep(POLL)
    raise RuntimeError('observation changed; reassess control gate')


SENTINELS = {'ah-global-command', 'ah-global-skill', 'ah-home-agents-skill', 'ah-global-mcp'}


def resources_ready(builtin):
    def ready(current):
        resources, integrations, _ = current
        present = {i[0] for i in resources['command'] + resources['skill'] + resources['mcp']}
        return SENTINELS <= present and plugins_ready(resources['plugin'], builtin) and bool(integrations)
    return ready


# --- Installed boots ------------------------------------------------------------

def config_documents(runtime, project, env, policy, url, owned):
    raw, _ = diagnostic(runtime, project, env, policy, ('debug', 'config'), url)
    return {owned_relative(s['path'], owned) for s in json.loads(raw) if s.get('type') == 'document' and 'path' in s}


def origin_allowance(port):
    """D077 experiment authority: one extra owned loopback port, outbound only, for the synthetic origin."""
    check(type(port) is int and 1 <= port <= 65535)
    return '(allow network-outbound (remote tcp "localhost:' + str(port) + '"))'


ORIGIN_PROBE = r"""
import json, socket, sys
port, other = int(sys.argv[1]), int(sys.argv[2])
out = {}
for name, family, op in (('connect', socket.AF_INET, lambda s: s.connect(('127.0.0.1', port))),
                         ('connect_v6', socket.AF_INET6, lambda s: s.connect(('::1', port))),
                         ('bind', socket.AF_INET, lambda s: s.bind(('127.0.0.1', port))),
                         ('other', socket.AF_INET, lambda s: s.connect(('127.0.0.1', other)))):
    s = socket.socket(family); s.settimeout(1)
    try:
        op(s); out[name] = 'ok'
    except PermissionError:
        out[name] = 'denied'
    except OSError:
        out[name] = 'error'
    finally:
        s.close()
print(json.dumps(out))
"""


def boundary_controls(root):
    """Revalidate the composition each boot uses (D076 profile with ancestor denials), then pair the extra
    origin allowance with its absence, over IPv4 and IPv6 loopback."""
    denials = ancestor_denials(root / 'home')
    port = fresh_port()
    env = {'HOME': str(root), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin'}
    with tempfile.TemporaryDirectory(prefix='.ah-retained-read-', dir=Path.home()) as protected:
        target = Path(protected) / 'sentinel'
        target.write_text('AH_READ_DENIAL_SENTINEL')
        with tempfile.TemporaryDirectory(prefix='ah-retained-write-') as fence:
            network_controls(root, combined_profile(root, port, denials), env, port, target, Path(fence) / 'write')
    observed = {}
    with SyntheticOrigin(fresh_port(), root / 'absent') as origin, SyntheticOrigin(fresh_port(), root / 'absent') as other:
        origin_port, other_port = origin.server.server_address[1], other.server.server_address[1]
        # A real ::1 listener on the origin port, so the IPv6 result reflects the policy, not a refusal.
        v6 = socket.socket(socket.AF_INET6)
        v6.bind(('::1', origin_port))
        v6.listen(4)
        try:
            for allowed in (False, True):
                policy = combined_profile(root, fresh_port(), denials) + (
                    origin_allowance(origin_port) if allowed else '')
                out, err = capture(['/usr/bin/sandbox-exec', '-p', policy, PYTHON, '-B', '-c', ORIGIN_PROBE,
                                    str(origin_port), str(other_port)], root, env)
                check(not err)
                observed['allowed' if allowed else 'absent'] = json.loads(out)
        finally:
            v6.close()
        check(origin.hits == {'manifest': 0, 'other': 0} and other.hits == {'manifest': 0, 'other': 0})
    absent = {'connect': 'denied', 'connect_v6': 'denied', 'bind': 'denied', 'other': 'denied'}
    check(observed['absent'] == absent)
    # SBPL `localhost` covers both loopback families: the allowance admits the origin port on ::1 too.
    check(observed['allowed'] == dict(absent, connect='ok', connect_v6='ok'))
    print('PASS: composed D076 boundary revalidated; origin allowance permits only outbound to its own port (IPv4 and IPv6 loopback)', flush=True)
    return observed


def boot(ctx, seed=None, origin=None, warnings=()):
    """One server boot on the shared owned root. Returns the redacted preflight record."""
    runtime, work, home, project, env, token, builtin = (ctx[k] for k in (
        'runtime', 'work', 'home', 'project', 'env', 'token', 'builtin'))
    check(not root_shape(work, token, env))
    owned = (work,)
    password = secrets.token_urlsafe(32)
    env = dict(env, OPENCODE_PASSWORD=password)
    port = fresh_port()
    policy = combined_profile(work, port, ancestor_denials(home))
    check(database_path(runtime, project, env, policy, work))
    if origin is not None:
        policy += origin_allowance(origin.server.server_address[1])
    log_path = work / 'DATA' / 'opencode' / 'log' / 'opencode.log'
    offset = len(log_path.read_text().splitlines()) if log_path.exists() else 0
    record = {}
    with owned_server(runtime, project, env, policy, port) as url:
        observer = PreflightObserver(port, password, project)
        check(observer.locations() == [])
        resources, integrations, identities = settle_view(observer, owned, resources_ready(builtin))
        documents = config_documents(runtime, project, env, policy, url, owned)
        record['before'] = (resources, integrations, identities, documents)
        if seed is not None:
            Seeder(port, password, project, origin.url if origin else None).post(seed)

            def seeded(current):
                _, listed, _ = current
                if seed == 'wellknown':
                    return origin.url in listed and resources_ready(builtin)(current)
                return bool(listed.get('opencode', ((), ()))[1]) and resources_ready(builtin)(current)
            resources, integrations, identities = settle_view(observer, owned, seeded)
            documents = config_documents(runtime, project, env, policy, url, owned)
        record['after'] = (resources, integrations, identities, documents)
        check(observer.locations() == [str(project)])
    lines = log_path.read_text().splitlines()
    check(len(lines) >= offset)
    watches, spawns, problems = log_inventory('\n'.join(lines[offset:]), work)
    check(not any(path.name == 'node_modules' for path in work.rglob('*')))
    check(not any((work / 'denied-bin').iterdir()))
    check(set(spawns) <= {('git', 'rev-parse')})  # The well-known `auth.command` is never run.
    check(not any(message == 'watcher failed' for _, _, message in watches))
    check(('MACHINE_PARENT', 'entries', 'watcher started') in watches)
    check(set(problems) == set(warnings))
    record['warnings'] = problems
    return record


def evaluate(record, expected_set, builtin):
    resources, integrations, _, documents = record
    return (preflight(integrations, resources, documents, expected_set, builtin, login=False),
            preflight(integrations, resources, documents, expected_set, builtin, login=True))


def new_case(base, runtime_source, builtin):
    work, token = create_root(base)
    runtime = work / 'opencode-cli'
    shutil.copy2(runtime_source, runtime)
    check(hashlib.sha256(runtime.read_bytes()).hexdigest() == SHA256)
    home, project, env, _ = build(work, False, False)
    static_guards(work, home, project, env)
    env.pop('OPENCODE_PASSWORD')
    check('OPENCODE_DB' not in env and not root_shape(work, token, env))
    return {'runtime': runtime, 'work': work, 'home': home, 'project': project, 'env': env, 'token': token,
            'builtin': builtin}


def integration_digest(ids):
    return hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()


def run_cases(runtime_source, builtin, literals, catalog):
    results = {}
    fresh_sets = []

    def fresh(record):
        _, integrations, identities, _ = record
        check(not identities)  # Fresh state holds no connection anywhere.
        fresh_sets.append(frozenset(integrations))
        return integrations

    # Case R: reused root, concurrent-lock refusal; also the Console control (no seed, no origin).
    with tempfile.TemporaryDirectory(prefix='ah-retained-') as directory:
        ctx = new_case(Path(directory).resolve(), runtime_source, builtin)
        held = acquire(ctx['work'])
        check(held is not None)
        try:
            check(lock_probe(ctx['work']) == 'refused')
            first = boot(ctx)
            integrations = fresh(first['before'])
            expected_set = frozenset(integrations)
            check(lock_probe(ctx['work']) == 'refused')
            second = boot(ctx)
        finally:
            os.close(held)
        check(lock_probe(ctx['work']) == 'acquired')
        # Cross-check the expected set before using it as a gate.
        # Exact: the installed binary lists the pinned snapshot's providers plus the IDs the plugins name.
        check(expected_set == frozenset(catalog) | frozenset(literals))
        check(all(ID_SHAPE.fullmatch(i) for i in expected_set))
        check(not any(m[0] == 'command' for methods, _ in integrations.values() for m in methods))
        check(first['before'] == first['after'] == second['before'] == second['after'])
        check(evaluate(first['after'], expected_set, builtin) == ([], ['openai-connection']))
        check(evaluate(second['after'], expected_set, builtin) == ([], ['openai-connection']))
        results['reused'] = {'boots': 2, 'identical': True, 'lock': ['refused', 'refused', 'acquired'],
                             'preflight': evaluate(second['after'], expected_set, builtin)}
    print(f'PASS: reused root: two boots identical; concurrent lock refused while held and acquired after release; '
          f'{len(expected_set)} integrations, no connections', flush=True)

    # Case W0/W1: retained well-known cache pair. Both boot A with the origin up and allowed; only W1 seeds.
    for seeded in (False, True):
        with tempfile.TemporaryDirectory(prefix='ah-retained-') as directory:
            ctx = new_case(Path(directory).resolve(), runtime_source, builtin)
            command = ctx['work'] / 'denied-bin' / 'ah-absent-wellknown'
            with SyntheticOrigin(fresh_port(), command) as origin:
                first = boot(ctx, 'wellknown' if seeded else None, origin,
                             warnings=(WELLKNOWN_CONFIG,) if seeded else ())
                hits = dict(origin.hits)
            fresh(first['before'])
            second = boot(ctx, warnings=(WELLKNOWN_WARNING, WELLKNOWN_CONFIG) if seeded else ())
            before = evaluate(first['before'], expected_set, builtin)
            after = evaluate(first['after'], expected_set, builtin)
            retained = evaluate(second['after'], expected_set, builtin)
            check(before == ([], ['openai-connection']))
            extra = set(second['after'][1]) - expected_set
            if seeded:
                check(hits == {'manifest': 1, 'other': 0})
                check(set(first['after'][1]) - expected_set == {origin.url} and extra == {origin.url})
                check(second['after'][1][origin.url] == ((('command', 'login'),), ()))
                check(after[0] == retained[0] == ['integration-set'])
            else:
                check(hits == {'manifest': 0, 'other': 0} and not extra)
                check(after[0] == retained[0] == [])
                check(first['after'] == second['after'])
            # Resources and config documents are unchanged by the retained source.
            check(first['before'][0] == second['after'][0] and second['after'][3] == {'CONFIG/opencode/opencode.json'})
            results['wellknown_seeded' if seeded else 'wellknown_control'] = {
                'origin_hits': hits, 'extra_integrations': len(extra), 'boot_a': after[0], 'boot_b': retained[0],
                'boot_b_warnings': second['warnings']}
        print(f'PASS: well-known {"seeded" if seeded else "control"}: '
              + ('retained origin integration survives an unreachable origin and is refused' if seeded
                 else 'origin up but unseeded; exact set passes'), flush=True)

    # Case C1: connected Console pair; R is its unseeded control.
    with tempfile.TemporaryDirectory(prefix='ah-retained-') as directory:
        ctx = new_case(Path(directory).resolve(), runtime_source, builtin)
        first = boot(ctx, 'console', warnings=(CONSOLE_WARNING,))
        fresh(first['before'])
        second = boot(ctx, warnings=(CONSOLE_WARNING,))
        after = evaluate(first['after'], expected_set, builtin)
        retained = evaluate(second['after'], expected_set, builtin)
        for record in (first['after'], second['after']):
            check(set(record[1]) == expected_set)
            check(record[1]['opencode'][1] == (('credential', 'key', ''),))
            check(sum(bool(c) for _, c in record[1].values()) == 1)
        check(first['after'][2] == second['after'][2])  # Same retained connection, compared by digest only.
        check(after[0] == retained[0] == ['console-connection'])
        check(after[1] == retained[1] == ['console-connection', 'openai-connection'])
        results['console_seeded'] = {'boot_a': after[0], 'boot_b': retained[0],
                                     'boot_a_warnings': first['warnings'], 'boot_b_warnings': second['warnings']}
    print('PASS: Console seeded: synthetic key connection retained across boots, Console fetch denied, refused', flush=True)

    # Every fresh root agreed before seeding.
    check(len(fresh_sets) == 4 and len(set(fresh_sets)) == 1)
    return results, expected_set


def static_refusals(base_dir):
    """Root-shape refusals happen before any OpenCode process starts."""
    observed = {}
    for name in ('legacy-auth-file', 'root-marker', 'database-override'):
        with tempfile.TemporaryDirectory(prefix='ah-retained-static-', dir=base_dir) as directory:
            work, token = create_root(Path(directory).resolve())
            env = {'XDG_DATA_HOME': str(work / 'DATA')}
            if name == 'legacy-auth-file':
                (work / 'DATA' / 'opencode').mkdir(parents=True)
                (work / 'DATA' / 'opencode' / 'auth.json').touch()  # Zero bytes; checked by name only.
            elif name == 'root-marker':
                (work / OWNER).write_text(secrets.token_hex(16))
            else:
                env['OPENCODE_DB'] = str(work / 'elsewhere.db')
            observed[name] = root_shape(work, token, env)
            check(observed[name] == [name])
    print('PASS: legacy auth file, marker mismatch and database override refused by name before launch', flush=True)
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode')
    parser.add_argument('--source', required=True, type=Path, help='official v2.2.5 checkout (D071 procedure)')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path(PYTHON).is_file() and Path('/usr/bin/sandbox-exec').is_file())
    packages, fingerprints = verify_source(args.source.resolve())
    for name, digest in FINGERPRINTS.items():
        check(hashlib.sha256((packages / name).read_bytes()).hexdigest() == digest)
        fingerprints[name] = digest
    builtin, files, digest = expected_plugins(packages)
    sources = plugin_files(packages)
    check(len(sources) == files)
    literals = literal_integrations(packages, sources)
    catalog = snapshot_providers(packages)
    print(f'PASS: pinned source; {len(builtin)} built-in plugins from {files} files; '
          f'{len(literals)} literal integration IDs; only the well-known plugin registers command methods', flush=True)
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-retained-bin-') as directory:
        source = Path(directory).resolve() / 'opencode-cli'
        shutil.copy2(installed, source)
        check(hashlib.sha256(source.read_bytes()).hexdigest() == SHA256)
        boundary = boundary_controls(Path(directory).resolve())
        refusals = static_refusals(Path(directory).resolve())
        results, expected_set = run_cases(source, builtin, literals, catalog)
    print('PASS: four fresh roots listed the same integration set before seeding', flush=True)
    print(json.dumps({'fingerprints': fingerprints, 'integrations': {
        'count': len(expected_set), 'sha256': integration_digest(expected_set),
        'plugin_named': sorted(literals), 'plugin_only': sorted(set(literals) - catalog),
        'snapshot_providers': len(catalog)},
        'origin_boundary': boundary, 'static_refusals': refusals, 'cases': results}, indent=1, sort_keys=True))
    print('LIMIT: no-auth retained state only; login, method, endpoint, permission and account gates remain open')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Retained-state experiment failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
