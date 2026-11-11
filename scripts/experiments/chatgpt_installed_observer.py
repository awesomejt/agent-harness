#!/usr/bin/env python3
"""Opt-in pinned macOS no-auth OpenCode resource observation on fresh owned roots (D075)."""
import argparse
import base64
import hashlib
import http.client
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
import time
import urllib.parse

from antigravity_feasibility import capture, check
from chatgpt_contained import contained_profile, diagnostic, network_controls, owned_server, PYTHON
from chatgpt_feasibility import SHA256
from chatgpt_source_boundary import MACHINE_ROOTS

PIN = '9bbb8ce18c80f099e0e448775f59d965ead40a21'
# Pinned files this helper consumes beyond the D075 table; all paths are under packages/.
FINGERPRINTS = {
    'core/src/plugin/internal.ts': 'b3bf36bd6cbc0dd849d0a55f552696c588b486e79f22963124e68a91c2769b50',
    'core/src/plugin/command.ts': 'a8efe5fb2fd28ec14d3286ed72beda982adad8ca76dddf26278475abf5ad3aa2',
    'core/src/plugin/goal.ts': '158c3721a9ad3974a0add78ee4c7cdf69a2b0fd75d7cee3dfff96b555ed8dbfc',
    'core/src/plugin/skill.ts': 'e5db6b5bf57a79f83e62510a51826c14c7822c0fdb84b7fbc4c5f7bccee75b8b',
    'plugin-browser/src/skill.ts': '5267aabb4c987609502769dcdcceea61770bc6884cbf9b7dbca73ffdedc5b256',
    'server/src/auth.ts': 'd2184b996991631490d7e82c19a7bd3310576c16fa2da2678819cac0a50f55c2',
    'core/src/config/discovery.ts': '48118dafc1ba0ec03112e98cdd616f339262a08a42b4ae75e9014575d863434d',
    'core/src/config/normalize.ts': '7ceeac61d778d447211bf6dd9fa6de4b0a46c4933d391573fc612ef3a98008c5',
    'core/src/v1/config/mcp.ts': '3d24c839c441bea5894c84b9f26d71e8ae2e223191c6724bb3e13c5a0df2eeee',
    'util/src/fs-util.ts': '9b0d2c0ec98338baa4fac2be0818496f501c3a07b6c22cebbdfc323427ba8d96',
    'core/src/config/plugin/instruction.ts': 'b69cc3088bf6f5b70a2e3b1ee8d796ee81edc05a62036d4f5a6d62f5ef90a8f9',
    'schema/src/plugin.ts': 'b453a0749f0213f141c29500e4033e2a0008e72d758ac97711310f053fd23d6a',
    'schema/src/command.ts': '6091f667ccf353e2ec7ac93902cd2c58b951236823f9411fb88174f9494932ab',
    'schema/src/location.ts': 'cc899b5b9430c1edf62f353c8f49611a382511a544c09889e2da24f9ab2ddec4',
    'schema/src/skill.ts': 'da003f8a6fd607569adb11e789c08eede92b044faa87648c422e69b47e281b4c',
    'schema/src/mcp.ts': '4fc2c6cd480552130a016ccb11160043e4c58e4833480ec9e208fcf4c4f3c8d7',
    'schema/src/config/mcp.ts': '72c8335c68fa0d72ad41bf784dea478325a769e7a39743dc242d760fdb9d951e',
}
BUILTIN_COMMANDS = {'init', 'review', 'goal'}            # core/src/plugin/{command,goal}.ts
BUILTIN_SKILLS = {'opencode', 'report', 'browser'}       # core/src/plugin/skill.ts, plugin-browser/src/skill.ts
ALLOWED = {'/api/debug/location': False, '/api/command': True, '/api/skill': True,
           '/api/plugin': True, '/api/mcp': True}
BODY_LIMIT = 256 * 1024
REQUEST_TIMEOUT = 5
WINDOW = 30
POLL = .25
SETTLE = .5
SECRET_ENV = ('OPENCODE_PASSWORD',)


# --- Pinned-source derivation -------------------------------------------------

def verify_source(source):
    head = subprocess.run(['/usr/bin/git', '-C', str(source), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, timeout=10)
    dirty = subprocess.run(['/usr/bin/git', '-C', str(source), 'status', '--porcelain'],
                           capture_output=True, text=True, timeout=10)
    check(head.returncode == 0 and head.stdout.strip() == PIN)
    check(dirty.returncode == 0 and dirty.stdout == '')
    packages = source / 'packages'
    recorded = {}
    for name, expected in FINGERPRINTS.items():
        digest = hashlib.sha256((packages / name).read_bytes()).hexdigest()
        check(digest == expected)
        recorded[name] = digest
    return packages, recorded


def module_file(packages, current, specifier):
    if specifier.startswith('.'):
        target = (current.parent / specifier).resolve()
        check(target.suffix == '.js')
        target = target.with_suffix('.ts')
    else:
        match = re.fullmatch(r'@opencode/([a-z0-9-]+)', specifier)
        check(match is not None)
        package = packages / match.group(1)
        exports = json.loads((package / 'package.json').read_text())['exports']['.']
        target = (package / exports).resolve()
    check(target.is_file() and packages in target.parents)
    return target


def imports(packages, path):
    text = path.read_text()
    table = {}
    for names, specifier in re.findall(r'import\s+\{([^}]*)\}\s+from\s+"([^"]+)"', text):
        for name in names.split(','):
            original, _, alias = name.strip().partition(' as ')
            original = original.strip()
            local = (alias or original).strip()
            if local and not original.startswith('type '):
                table[local] = (specifier, original)
    for name, specifier in re.findall(r'import\s+([A-Za-z_]\w*)\s+from\s+"([^"]+)"', text):
        table[name] = (specifier, 'default')
    return text, table


def definition_id(text, name):
    anchor = 'export default' if name == 'default' else f'export const {name} ='
    start = text.find(anchor)
    check(start >= 0 and text.count(anchor) == 1)
    end = text.find('\nexport ', start + 1)
    statement = text[start:end if end >= 0 else len(text)]
    literal = re.compile(r'(?:\bid:\s*|\bmake\(\s*)"(opencode\.[a-z0-9.\-]+)"')
    found = literal.findall(statement)
    for constant in re.findall(r'\bid:\s*([A-Z]\w*)\s*,', statement):  # `id: ID` naming a file constant.
        found += re.findall(r'\nexport const ' + constant + r'\s*=\s*"(opencode\.[a-z0-9.\-]+)"\n', text)
    if not found:  # `export const X = factory(...)`: the ID is inside the local factory.
        factory = re.match(re.escape(anchor) + r'\s*(\w+)\(', statement)
        check(factory is not None and factory.group(1) != name)
        body = re.search(r'\nexport function ' + factory.group(1) + r'\(.*?\n}\n', text, re.S)
        found = literal.findall(body.group(0)) if body else [definition_id(text, factory.group(1))]
    check(len(set(found)) == 1)
    return found[0]


def array_entries(text, name):
    match = re.search(r'(?:export )?const ' + re.escape(name) + r'\b[^=]*=\s*\[(.*?)\]\s*(?:as const)?', text, re.S)
    check(match is not None)
    body = re.sub(r'//[^\n]*', '', match.group(1))
    return [item.strip() for item in body.split(',') if item.strip()]


def resolve_entries(packages, path, entries, seen):
    text, table = imports(packages, path)
    ids = []
    for entry in entries:
        spread = entry.startswith('...')
        entry = entry[3:] if spread else entry
        head, _, member = entry.partition('.')
        if head in table:
            target = module_file(packages, path, table[head][0])
            exported = table[head][1]
            if member:  # Namespace module re-exported with `export * as X`.
                check(re.search(r'export \* as ' + re.escape(head) + r'\b', target.read_text()) is not None)
                exported = member
        else:
            check(not member and re.search(r'const ' + re.escape(head) + r'\b', text) is not None)
            target, exported = path, head
        seen.add(target)
        if spread:
            ids += resolve_entries(packages, target, array_entries(target.read_text(), exported), seen)
        else:
            ids.append(definition_id(target.read_text(), exported))
    return ids


def expected_plugins(packages):
    internal = packages / 'core/src/plugin/internal.ts'
    seen = {internal}
    text = internal.read_text()
    ids = []
    for group in ('pre', 'post'):
        ids += resolve_entries(packages, internal, array_entries(text, group), seen)
    check(len(ids) == len(set(ids)))
    digest = hashlib.sha256(b''.join(path.read_bytes() for path in sorted(seen))).hexdigest()
    return frozenset(ids), len(seen), digest


# --- Observer -----------------------------------------------------------------

class Observer:
    """Authenticated bounded GET observer for one owned server and location."""

    allowed = ALLOWED  # Subclasses may add exact routes; every other route is refused.

    def __init__(self, port, password, location, connect=http.client.HTTPConnection):
        check(type(port) is int and 1 <= port <= 65535 and isinstance(password, str) and password)
        check(isinstance(location, Path) and location.is_absolute())
        self.port, self.location, self.connect = port, location, connect
        self.authorization = 'Basic ' + base64.b64encode(f'opencode:{password}'.encode()).decode()

    def get(self, path):
        check(path in self.allowed)  # Every other route is refused before any connection.
        query = '?' + urllib.parse.urlencode({'location[directory]': str(self.location)}) if self.allowed[path] else ''
        connection = self.connect('127.0.0.1', self.port, timeout=REQUEST_TIMEOUT)
        try:
            connection.request('GET', path + query, headers={
                'Authorization': self.authorization, 'Connection': 'close', 'Accept': 'application/json'})
            response = connection.getresponse()
            body = response.read(BODY_LIMIT + 1)
            check(response.status == 200 and len(body) <= BODY_LIMIT)
            check((response.getheader('content-type') or '').split(';')[0].strip() == 'application/json')
        finally:
            connection.close()
        value = json.loads(body)
        if not self.allowed[path]:
            return value
        check(isinstance(value, dict) and set(value) == {'location', 'data'})
        check(value['location'] == {'directory': str(self.location)} and isinstance(value['data'], list))
        return value['data']

    def locations(self):
        value = self.get('/api/debug/location')
        check(isinstance(value, list) and all(isinstance(item, dict) and set(item) == {'directory'} for item in value))
        return sorted(item['directory'] for item in value)


def owned_relative(path, owned):
    check(isinstance(path, str) and os.path.isabs(path) and os.path.normpath(path) == path)
    for root in owned:
        if path == str(root) or path.startswith(str(root) + os.sep):
            return os.path.relpath(path, root)
    raise RuntimeError('observation changed; reassess control gate')


def redact(kind, items, owned):
    """Strict schema check; keep only the D075 recorded fields."""
    check(kind in ('command', 'skill', 'plugin', 'mcp') and isinstance(items, list))
    record = []
    for item in items:
        check(isinstance(item, dict))
        if kind == 'command':
            check(set(item) <= {'name', 'description'} and 'name' in item)
            record.append((item['name'], item.get('description')))
        elif kind == 'skill':
            check(set(item) <= {'id', 'name', 'description', 'autoinvoke', 'path', 'content'})
            check({'id', 'name', 'path', 'content'} <= set(item) and isinstance(item['content'], str))
            if item['id'] in BUILTIN_SKILLS and item['path'] == f'/builtin/{item["id"]}.md':
                path = item['path']  # Virtual built-in path from pinned source, not a file.
            else:
                path = owned_relative(item['path'], owned)
            content = item['content'].encode()
            record.append((item['id'], item['name'], path, hashlib.sha256(content).hexdigest(), len(content)))
        elif kind == 'plugin':
            check(set(item) <= {'id', 'source', 'features', 'state'} and 'id' in item)
            source = item['source']
            check(isinstance(source, dict) and source.get('type') in ('builtin', 'package', 'local', 'sdk'))
            local = owned_relative(source['path'], owned) if source['type'] == 'local' else None
            record.append((item['id'], source['type'], local, item['state'].get('status')))
        elif kind == 'mcp':
            check(set(item) <= {'name', 'status', 'title', 'integrationID'} and 'name' in item)
            record.append((item['name'], item['status'].get('status')))
        else:
            raise RuntimeError('observation changed; reassess control gate')
    return sorted(record, key=lambda value: tuple('' if part is None else str(part) for part in value))


KINDS = {'command': '/api/command', 'skill': '/api/skill', 'plugin': '/api/plugin', 'mcp': '/api/mcp'}


def snapshot(observer, owned):
    return {kind: redact(kind, observer.get(path), owned) for kind, path in KINDS.items()}


def settle(observer, owned, ready, clock=time.monotonic, sleep=time.sleep):
    """Poll until `ready` holds, then require two identical reads >= SETTLE apart."""
    deadline = clock() + WINDOW
    previous = None
    while clock() < deadline:
        current = snapshot(observer, owned)
        if ready(current):
            if previous == current:
                return current
            previous = current
            sleep(SETTLE)
        else:
            previous = None
            sleep(POLL)
    raise RuntimeError('observation changed; reassess control gate')


# --- Fixtures and static guards -----------------------------------------------

def command_file(path, description):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\ndescription: {description}\n---\nAH_INERT_TEMPLATE\n')


def skill_file(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: inert {name}\n---\nAH_INERT_SKILL {name}\n')


def disabled_mcp(root, name):
    return {'type': 'local', 'command': [str(root / 'denied-bin' / ('ah-absent-' + name))], 'disabled': True}


def build(root, project_on, claude_on):
    home, config, data = root / 'home', root / 'CONFIG' / 'opencode', root / 'DATA'
    parent = home / 'repo'
    project = parent / 'project'
    for path in (project, parent / '.git', config):
        path.mkdir(parents=True)
    data.mkdir()  # Exclusive create: a fresh data root, never reused.
    (root / 'denied-bin').mkdir(mode=0o555)
    command_file(config / 'commands' / 'ah-global-command.md', 'inert global sentinel')
    skill_file(config / 'skills' / 'ah-global-skill', 'ah-global-skill')
    skill_file(home / '.agents' / 'skills' / 'ah-home-agents-skill', 'ah-home-agents-skill')
    skill_file(home / '.claude' / 'skills' / 'ah-home-claude-skill', 'ah-home-claude-skill')
    (config / 'opencode.json').write_text(json.dumps({
        'agents': {'ah-global-agent': {'description': 'inert', 'system': 'AH_GLOBAL_AGENT'}},
        'mcp': {'servers': {'ah-global-mcp': disabled_mcp(root, 'global')}}}))
    command_file(project / '.opencode' / 'commands' / 'ah-project-command.md', 'inert project marker')
    skill_file(project / '.opencode' / 'skills' / 'ah-project-skill', 'ah-project-skill')
    skill_file(project / '.agents' / 'skills' / 'ah-project-agents-skill', 'ah-project-agents-skill')
    skill_file(project / '.claude' / 'skills' / 'ah-project-claude-skill', 'ah-project-claude-skill')
    (project / 'opencode.json').write_text(json.dumps({
        'agents': {'ah-project-agent': {'description': 'inert', 'system': 'AH_PROJECT_AGENT'}},
        'mcp': {'servers': {'ah-project-mcp': disabled_mcp(root, 'project')}}}))
    (parent / 'opencode.json').write_text(json.dumps({
        'agents': {'ah-parent-agent': {'description': 'inert', 'system': 'AH_PARENT_AGENT'}}}))
    password = secrets.token_urlsafe(32)
    env = {'HOME': str(home), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
           'NO_COLOR': '1', 'TERM': 'dumb', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
           'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_PASSWORD': password,
           'OPENCODE_CONFIG_CONTENT': json.dumps({'update': 'disable', 'share': 'disabled'})}
    for kind in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
        env['XDG_' + kind + '_HOME'] = str(root / kind)
    if not project_on:
        env['OPENCODE_DISABLE_PROJECT_CONFIG'] = 'true'
    if not claude_on:
        env['OPENCODE_DISABLE_CLAUDE_CODE_SKILLS'] = 'true'
    return home, project, env, password


DISCOVERY_NAMES = ('.claude', '.agents', '.opencode', 'opencode.json', 'opencode.jsonc', 'AGENTS.md', 'CLAUDE.md')


def guard_document(document):
    check(isinstance(document, dict) and not {'instructions', 'plugins', 'plugin', 'skills'} & set(document))
    # Native shape only: pinned normalize.ts migrates direct legacy entries through
    # the v1 schema, which drops `disabled`, so a legacy entry would start.
    if 'mcp' in document:
        check(set(document['mcp']) == {'servers'})
        check(all(set(server) == {'type', 'command', 'disabled'} and server['disabled'] is True
                  and server['type'] == 'local' for server in document['mcp']['servers'].values()))


def static_guards(root, home, project, env):
    """D075 pre-launch refusals for instructions and plugins, plus the unowned ancestor walk."""
    check(root.resolve() == root and project.resolve() == project and home in project.parents)
    config = Path(env['XDG_CONFIG_HOME']) / 'opencode'
    # Instruction walk: location up to and including the owned HOME, plus the global file.
    walk = [project, *[p for p in project.parents if home == p or home in p.parents]]
    for directory in [config, *walk]:
        check(not os.path.lexists(directory / 'AGENTS.md'))
    # Config/compatibility walk continues to `/`; no unowned ancestor may hold a source.
    for ancestor in root.parents:
        for name in DISCOVERY_NAMES:
            check(not os.path.lexists(ancestor / name))
    for path in root.rglob('*'):
        if path.name == 'opencode-cli' or root / 'denied-bin' in path.parents:
            continue
        check(not path.is_symlink())
        check(path.name not in ('plugin', 'plugins', 'AGENTS.md', 'CLAUDE.md'))
        if path.suffix in ('.json', '.jsonc'):
            guard_document(json.loads(path.read_text()))
    content = json.loads(env['OPENCODE_CONFIG_CONTENT'])
    check(not {'instructions', 'plugins', 'plugin', 'skills', 'mcp'} & set(content))
    check(not any(key.startswith('OPENCODE_') and key not in {
        'OPENCODE_DISABLE_MODELS_FETCH', 'OPENCODE_DISABLE_AUTOUPDATE', 'OPENCODE_PASSWORD',
        'OPENCODE_CONFIG_CONTENT', 'OPENCODE_DISABLE_PROJECT_CONFIG', 'OPENCODE_DISABLE_CLAUDE_CODE_SKILLS'}
        for key in env))


def expected(project_on, claude_on):
    commands = BUILTIN_COMMANDS | {'ah-global-command'} | ({'ah-project-command'} if project_on else set())
    skills = BUILTIN_SKILLS | {'ah-global-skill', 'ah-home-agents-skill'}
    if project_on:
        skills |= {'ah-project-skill', 'ah-project-agents-skill'}
    if claude_on:
        skills |= {'ah-home-claude-skill'}
    if project_on and claude_on:
        skills |= {'ah-project-claude-skill'}
    mcp = {('ah-global-mcp', 'disabled')} | ({('ah-project-mcp', 'disabled')} if project_on else set())
    return commands, skills, mcp


def plugins_ready(plugins, builtin):
    return {item[0] for item in plugins} == builtin and all(
        item[1:] == ('builtin', None, 'active') for item in plugins) and len(plugins) == len(builtin)


# --- Server log inventory -----------------------------------------------------

FIELD = re.compile(r'(\w[\w.]*)=("(?:[^"\\]|\\.)*"|\S*)')


def watch_label(path, work):
    if path == '/Library/Application Support':
        return 'MACHINE_PARENT'  # D073: the absent system root's parent entries watch.
    if path == str(work.parent):
        return 'OWNED_ANCESTOR'
    if path in {str(p) for p in work.parent.parents}:
        return 'UNOWNED_ANCESTOR'
    return 'work/' + owned_relative(path, (work,))


def log_inventory(log, work):
    """Record only static messages, labelled watcher targets and spawned executables."""
    watches, spawns, problems = set(), set(), set()
    for line in log.splitlines():
        fields = {k: json.loads(v) if v.startswith('"') else v for k, v in FIELD.findall(line)}
        message = fields.get('message', '')
        if message in ('watcher subscribe', 'watcher started', 'watcher failed'):
            watches.add((watch_label(fields['path'], work), fields.get('type'), message))
        elif message == 'spawning process':
            spawns.add((os.path.basename(fields['command']), json.loads(fields['args'])[0]))
        if fields.get('level') in ('WARN', 'ERROR'):
            problems.add((fields['level'], message))
    return sorted(watches), sorted(spawns), sorted(problems)


# --- Bun filesystem equivalents -----------------------------------------------

BUN_FS = r"""
const fs=require('node:fs'), path=require('node:path');
const [root, mode]=process.argv.slice(2);
const system=path.join(root,'machine support'), mdm=path.join(root,'managed'), parent=path.join(root,'parent');
const out={};
const probe=(name,f)=>{try{f();out[name]='ok'}catch(e){out[name]=e.code||'error'}};
probe('read',()=>fs.readFileSync(path.join(system,'opencode.json')));
probe('stat',()=>fs.statSync(path.join(system,'opencode.json')));
probe('list',()=>fs.readdirSync(system));
probe('mdm',()=>fs.readFileSync(path.join(mdm,'user','ai.opencode.managed.plist')));
probe('alias',()=>fs.readFileSync(path.join(root,'alias-in','opencode.json')));
probe('realpath',()=>fs.realpathSync(path.join(system,'opencode.json')));
probe('watch',()=>fs.watch(system).close());
out.exists=fs.existsSync(path.join(system,'opencode.json'));
const events=[];
const watcher=fs.watch(parent,(type,file)=>events.push(String(file)));
fs.mkdirSync(path.join(parent,'opencode'));
fs.writeFileSync(path.join(parent,'opencode','opencode.json'),'AH_LATE_ROOT');
fs.writeFileSync(path.join(system,'replacement'),'AH_REPLACED');
fs.renameSync(path.join(system,'replacement'),path.join(system,'opencode.json'));
setTimeout(()=>{
 watcher.close();
 out.parentEvent=events.includes('opencode');
 probe('late',()=>fs.readFileSync(path.join(parent,'opencode','opencode.json')));
 probe('replaced',()=>fs.readFileSync(path.join(system,'opencode.json')));
 probe('allowed',()=>fs.readFileSync(path.join(root,'allowed','canary')));
 console.log(JSON.stringify(out));
},400);
"""


def bun_controls(executable, port):
    observed = {}
    for deny in (False, True):
        with tempfile.TemporaryDirectory(prefix='ah-bun-boundary-') as directory:
            root = Path(directory).resolve()
            for path in (root / 'machine support', root / 'managed' / 'user', root / 'allowed', root / 'parent'):
                path.mkdir(parents=True)
            (root / 'machine support' / 'opencode.json').write_text('AH_SYSTEM')
            (root / 'managed' / 'user' / 'ai.opencode.managed.plist').write_text('AH_USER_MDM')
            (root / 'allowed' / 'canary').write_text('AH_ALLOWED')
            (root / 'alias-in').symlink_to(root / 'machine support', target_is_directory=True)
            fixture = root / 'bun-fs.js'
            fixture.write_text(BUN_FS)
            check(not (root / 'parent' / 'opencode').exists())
            denied = (root / 'machine support', root / 'managed', root / 'parent' / 'opencode') if deny else ()
            policy = combined_profile(root, port, denied)
            env = {'HOME': str(root / 'home'), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin', 'BUN_BE_BUN': '1'}
            out, err = capture(['/usr/bin/sandbox-exec', '-p', policy, str(executable), str(fixture),
                                str(root), 'deny' if deny else 'allow'], root, env)
            check(not err)
            result = json.loads(out)
            blocked = {'read', 'stat', 'list', 'mdm', 'alias', 'realpath', 'watch', 'late', 'replaced'}
            for name in blocked:
                check(result[name] == ('EPERM' if deny else 'ok'))
            # Observed, not relied on: access()-based existence still reports a
            # denied file, and the allowed parent watch omits a denied late root.
            check(result['allowed'] == 'ok' and result['exists'] is True and result['parentEvent'] is (not deny))
            observed['deny' if deny else 'allow'] = result
    print('PASS: Bun read/stat/list/realpath/watch, symlink, late-root and replacement denials; '
          'existsSync still true when denied; allowed parent watch omits the denied late root', flush=True)
    return observed


def combined_profile(root, port, synthetic=()):
    """D070 transport plus the D073 machine-root denials (and synthetic equivalents)."""
    value = contained_profile(root, Path.home(), port)
    for path in (*(Path(p) for p in MACHINE_ROOTS), *synthetic):
        check(isinstance(path, Path) and path.is_absolute() and str(path) != '/')
        value += '(deny file-read* (subpath ' + json.dumps(str(path)) + '))'
    return value


def fresh_port():
    reservation = socket.socket()
    try:
        reservation.bind(('127.0.0.1', 0))
        return reservation.getsockname()[1]
    finally:
        reservation.close()


# --- Installed cases ----------------------------------------------------------

def ancestor_denials(home, keep=()):
    """Deny every discovery name in each ancestor above the owned HOME (project walk reaches `/`)."""
    return tuple(ancestor / name for ancestor in home.parents if ancestor not in keep for name in DISCOVERY_NAMES)


def late_changes(root, home, project):
    """Late create/replace in included roots, with excluded-root markers alongside."""
    config = root / 'CONFIG' / 'opencode'
    command_file(project / '.opencode' / 'commands' / 'ah-late-project-command.md', 'late excluded marker')
    skill_file(project / '.opencode' / 'skills' / 'ah-late-project-skill', 'ah-late-project-skill')
    skill_file(home / '.claude' / 'skills' / 'ah-late-claude-skill', 'ah-late-claude-skill')
    command_file(config / 'commands' / 'ah-late-command.md', 'late included sentinel')
    skill_file(config / 'skills' / 'ah-late-skill', 'ah-late-skill')
    skill_file(home / '.agents' / 'skills' / 'ah-late-agents-skill', 'ah-late-agents-skill')
    replacement = config / 'commands' / '.ah-replacement'
    replacement.write_text('---\ndescription: replaced global sentinel\n---\nAH_INERT_TEMPLATE\n')
    os.replace(replacement, config / 'commands' / 'ah-global-command.md')
    document = json.loads((config / 'opencode.json').read_text())
    document['mcp']['servers']['ah-late-mcp'] = disabled_mcp(root, 'late')
    guard_document(document)
    staged = config / '.ah-document'
    staged.write_text(json.dumps(document))
    os.replace(staged, config / 'opencode.json')
    # Ancestor-equivalent source above `root`: owned, so seeding it never touches host paths.
    ancestor = {'mcp': {'servers': {'ah-ancestor-mcp': disabled_mcp(root, 'ancestor')}}}
    guard_document(ancestor)
    staged = root.parent / '.ah-ancestor'
    staged.write_text(json.dumps(ancestor))
    os.replace(staged, root.parent / 'opencode.json')


def run_case(executable, builtin, project_on, claude_on, reload, ancestor_denied=True):
    with tempfile.TemporaryDirectory(prefix='ah-chatgpt-observer-') as directory:
        root = Path(directory).resolve()
        work = root / 'work'
        work.mkdir()
        runtime = work / 'opencode-cli'
        shutil.copy2(executable, runtime)
        check(hashlib.sha256(runtime.read_bytes()).hexdigest() == SHA256)
        home, project, env, password = build(work, project_on, claude_on)
        static_guards(work, home, project, env)
        port = fresh_port()
        policy = combined_profile(work, port, ancestor_denials(home, () if ancestor_denied else (root,)))
        owned = (work,)
        commands, skills, mcp = expected(project_on, claude_on)
        with owned_server(runtime, project, env, policy, port) as url:
            observer = Observer(port, password, project)
            check(observer.locations() == [])
            sentinels = {'ah-global-command', 'ah-global-skill', 'ah-home-agents-skill', 'ah-global-mcp'}

            def ready(view):
                present = {i[0] for i in view['command'] + view['skill'] + view['mcp']}
                return sentinels <= present and plugins_ready(view['plugin'], builtin)
            view = settle(observer, owned, ready)
            check({c[0] for c in view['command']} == commands)
            check({s[0] for s in view['skill']} == skills and all(s[0] == s[1] for s in view['skill'] if s[0] not in BUILTIN_SKILLS))
            check(set(view['mcp']) == mcp)
            check(observer.locations() == [str(project)])
            raw, _ = diagnostic(runtime, project, env, policy, ('debug', 'config'), url)
            documents = {owned_relative(s['path'], owned) for s in json.loads(raw)
                         if s.get('type') == 'document' and 'path' in s}
            check(documents == {'CONFIG/opencode/opencode.json'} | (
                {'home/repo/opencode.json', 'home/repo/project/opencode.json'} if project_on else set()))
            raw, _ = diagnostic(runtime, project, env, policy, ('debug', 'agents'), url)
            agents = {a['id'] for a in json.loads(raw)} & {'ah-global-agent', 'ah-project-agent', 'ah-parent-agent'}
            check(agents == {'ah-global-agent'} | ({'ah-project-agent', 'ah-parent-agent'} if project_on else set()))
            late = None
            if reload:
                late_changes(work, home, project)
                late_sentinels = {'ah-late-command', 'ah-late-skill', 'ah-late-agents-skill', 'ah-late-mcp'}

                def reloaded(view):
                    present = {i[0] for i in view['command'] + view['skill'] + view['mcp']}
                    replaced = ('ah-global-command', 'replaced global sentinel') in view['command']
                    return late_sentinels <= present and replaced and plugins_ready(view['plugin'], builtin)
                late = settle(observer, owned, reloaded)
                late_commands = commands | {'ah-late-command'} | ({'ah-late-project-command'} if project_on else set())
                late_skills = skills | {'ah-late-skill', 'ah-late-agents-skill'} | (
                    {'ah-late-project-skill'} if project_on else set()) | (
                    {'ah-late-claude-skill'} if claude_on else set())
                check({i[0] for i in late['command']} == late_commands and {i[0] for i in late['skill']} == late_skills)
                ancestor = project_on and not ancestor_denied
                check(set(late['mcp']) == mcp | {('ah-late-mcp', 'disabled')} | (
                    {('ah-ancestor-mcp', 'disabled')} if ancestor else set()))
                check(observer.locations() == [str(project)])
        log_path = work / 'DATA' / 'opencode' / 'log' / 'opencode.log'
        watches, spawns, problems = log_inventory(log_path.read_text(), work)
        check(not any(path.name == 'node_modules' for path in work.rglob('*')))
        check(not any((work / 'denied-bin').iterdir()))
        check({spawn for spawn in spawns} <= {('git', 'rev-parse')})
        # Gates, not observations: no WARN/ERROR, no failed watcher, machine parent watched.
        check(not problems)
        check(not any(message == 'watcher failed' for _, _, message in watches))
        check(('MACHINE_PARENT', 'entries', 'watcher started') in watches)
        created = sorted({str(p.relative_to(work)).split(os.sep)[0] for p in work.iterdir()})
        return {'project': project_on, 'claude': claude_on, 'reload': reload, 'ancestor_denied': ancestor_denied,
                'commands': sorted(commands), 'skills': sorted(skills), 'mcp': sorted(mcp),
                'sentinel_skill_hashes': {s[0]: s[3][:16] for s in view['skill'] if s[0].startswith('ah-')},
                'watches': watches, 'spawns': spawns, 'warnings': problems, 'top_level': created}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode')
    parser.add_argument('--source', required=True, type=Path, help='official v2.2.5 checkout (D071 procedure)')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path(PYTHON).is_file() and Path('/usr/bin/sandbox-exec').is_file())
    packages, fingerprints = verify_source(args.source.resolve())
    builtin, files, digest = expected_plugins(packages)
    print(f'PASS: pinned source {PIN[:12]}; {len(builtin)} built-in plugin IDs derived from {files} files '
          f'(sha256 {digest[:16]})', flush=True)
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-chatgpt-observer-bin-') as directory:
        root = Path(directory).resolve()
        executable = root / 'opencode-cli'
        shutil.copy2(installed, executable)
        check(hashlib.sha256(executable.read_bytes()).hexdigest() == SHA256)
        port = fresh_port()
        with tempfile.TemporaryDirectory(prefix='.ah-observer-read-', dir=Path.home()) as protected:
            target = Path(protected) / 'sentinel'
            target.write_text('AH_READ_DENIAL_SENTINEL')
            with tempfile.TemporaryDirectory(prefix='ah-observer-write-') as fence:
                network_controls(root, combined_profile(root, port), {'HOME': str(root), 'TMPDIR': str(root),
                                 'PATH': '/usr/bin:/bin'}, port, target, Path(fence) / 'write')
        bun_controls(executable, fresh_port())
        results = []
        for case in ((False, False, True, True), (True, False, False, True), (False, True, False, True),
                     (True, True, True, True), (True, False, True, False)):
            results.append(run_case(executable, builtin, *case))
            print('PASS: project={} claude={} reload={} ancestor_denied={}: settled sentinel-anchored lists, '
                  'exact built-ins, disabled MCP, pinned location'.format(*case), flush=True)
    print(json.dumps({'fingerprints': fingerprints, 'plugins': {'count': len(builtin), 'files': files,
                      'digest': digest}, 'cases': results}, indent=1, sort_keys=True))
    print('LIMIT: fresh-state no-auth resources only; retained state, login, endpoint and permission gates remain open')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Installed observer probe failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
