#!/usr/bin/env python3
"""Offline D075 observer, guard and source-derivation refusals; no OpenCode or network."""
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_installed_observer as probe


def refuses(action):
    try:
        action()
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return
    raise AssertionError('unsafe input was accepted')


class Response:
    def __init__(self, status, body, content_type='application/json'):
        self.status, self.body, self.content_type = status, body, content_type

    def getheader(self, name):
        return self.content_type if name == 'content-type' else None

    def read(self, limit):
        return self.body[:limit]


def fake(response, calls):
    class Connection:
        def __init__(self, host, port, timeout):
            calls.append(('connect', host, port, timeout))

        def request(self, method, path, headers):
            calls.append(('request', method, path, headers['Connection']))

        def getresponse(self):
            return response

        def close(self):
            calls.append(('close',))
    return Connection


def observer_cases(location):
    good = json.dumps({'location': {'directory': str(location)}, 'data': []}).encode()
    calls = []
    observer = probe.Observer(4242, 'synthetic', location, fake(Response(200, good), calls))
    for path in ('/api/usage', '/api/integration', '/api/credential', '/api/plugin/check', '/api/event',
                 '/api/location', '/api/session', '/api/debug/location/evict', '/api/mcp/resource'):
        refuses(lambda: observer.get(path))
    assert not calls, 'refused routes must not connect'
    assert observer.get('/api/command') == []
    assert calls[0] == ('connect', '127.0.0.1', 4242, probe.REQUEST_TIMEOUT)
    assert calls[1][1] == 'GET' and calls[1][3] == 'close' and 'location%5Bdirectory%5D=' in calls[1][2]
    assert calls[-1] == ('close',)
    other = json.dumps({'location': {'directory': '/elsewhere'}, 'data': []}).encode()
    extra = json.dumps({'location': {'directory': str(location)}, 'data': [], 'more': 1}).encode()
    for response in (Response(302, good), Response(401, good), Response(200, good, 'text/html'),
                     Response(200, b'[' + b' ' * probe.BODY_LIMIT + b']'), Response(200, other),
                     Response(200, extra)):
        closed = []
        refuses(lambda: probe.Observer(4242, 'synthetic', location, fake(response, closed)).get('/api/skill'))
        assert closed[-1] == ('close',)
    for port, password in ((0, 'x'), (True, 'x'), (4242, '')):
        refuses(lambda: probe.Observer(port, password, location))
    refuses(lambda: probe.Observer(4242, 'x', Path('relative')))
    print('PASS: observer route allowlist, status/type/size/location bounds and connection close')


def redact_cases(owned):
    root = owned[0]
    skill = {'id': 'ah', 'name': 'ah', 'path': str(root / 'skills' / 'ah' / 'SKILL.md'), 'content': 'AH_BODY'}
    record = probe.redact('skill', [skill], owned)[0]
    assert record[2] == 'skills/ah/SKILL.md' and 'AH_BODY' not in json.dumps(record) and record[4] == 7
    builtin = {'id': 'opencode', 'name': 'OpenCode', 'path': '/builtin/opencode.md', 'content': ''}
    assert probe.redact('skill', [builtin], owned)[0][2] == '/builtin/opencode.md'
    for item in (dict(skill, path='/etc/elsewhere.md'), dict(skill, path=str(root) + '-sibling/x'),
                 dict(skill, path=str(root / '..' / 'x')), dict(builtin, id='ah', name='ah'),
                 dict(skill, unexpected=1)):
        refuses(lambda: probe.redact('skill', [item], owned))
    refuses(lambda: probe.redact('command', [{'name': 'x', 'template': 'body'}], owned))
    refuses(lambda: probe.redact('plugin', [{'id': 'x', 'source': {'type': 'local', 'path': '/tmp/x'},
                                             'features': {}, 'state': {'status': 'active'}}], owned))
    refuses(lambda: probe.redact('plugin', [{'id': 'x', 'source': {'type': 'remote'}, 'features': {},
                                             'state': {'status': 'active'}}], owned))
    refuses(lambda: probe.redact('session', [], owned))
    mcp = probe.redact('mcp', [{'name': 'm', 'status': {'status': 'failed', 'error': 'AH_SECRET'}}], owned)
    assert mcp == [('m', 'failed')]
    builtin_ids = frozenset({'opencode.a', 'opencode.b'})
    plugins = [('opencode.a', 'builtin', None, 'active'), ('opencode.b', 'builtin', None, 'active')]
    assert probe.plugins_ready(plugins, builtin_ids)
    assert not probe.plugins_ready(plugins[:1], builtin_ids)
    assert not probe.plugins_ready([plugins[0], ('opencode.b', 'builtin', None, 'failed')], builtin_ids)
    assert not probe.plugins_ready(plugins + [('x', 'local', 'p', 'active')], builtin_ids)
    print('PASS: strict schema redaction, owned paths, error withholding and exact plugin readiness')


def settle_cases(owned):
    views = []

    class Fake:
        def get(self, path):
            kind = {v: k for k, v in probe.KINDS.items()}[path]
            return views[0][kind]

    now = [0.0]

    def sleep(seconds):
        now[0] += seconds
        if len(views) > 1:
            views.pop(0)
    empty = {kind: [] for kind in probe.KINDS}
    ready = dict(empty, command=[{'name': 'ah'}])
    views[:] = [empty, empty, ready, dict(ready, command=[{'name': 'ah'}, {'name': 'x'}]), ready, ready]
    result = probe.settle(Fake(), owned, lambda v: ('ah', None) in v['command'], lambda: now[0], sleep)
    assert result['command'] == [('ah', None)]
    views[:] = [empty]
    now[0] = 0.0
    refuses(lambda: probe.settle(Fake(), owned, lambda v: bool(v['command']), lambda: now[0], sleep))
    assert now[0] >= probe.WINDOW
    print('PASS: sentinel settle resets on change, needs two identical reads and times out')


def guard_cases():
    native = {'mcp': {'servers': {'m': {'type': 'local', 'command': ['/absent'], 'disabled': True}}}}
    probe.guard_document(native)
    for document in ({'mcp': {'m': {'type': 'local', 'command': ['/absent'], 'disabled': True}}},
                     {'mcp': {'servers': {'m': {'type': 'local', 'command': ['/absent']}}}},
                     {'mcp': {'servers': {'m': {'type': 'remote', 'url': 'https://x', 'disabled': True}}}},
                     {'instructions': []}, {'plugins': []}, {'skills': {'urls': []}}, []):
        refuses(lambda: probe.guard_document(document))
    for case in ('agents', 'plugin', 'symlink', 'legacy', 'content', 'env'):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory).resolve() / 'work'
            work.mkdir()
            home, project, env, _ = probe.build(work, True, True)
            probe.static_guards(work, home, project, env)
            if case == 'agents':
                (home / 'repo' / 'AGENTS.md').write_text('x')
            elif case == 'plugin':
                (project / '.opencode' / 'plugins').mkdir()
            elif case == 'symlink':
                (project / 'link').symlink_to(home)
            elif case == 'legacy':
                (project / 'opencode.json').write_text(json.dumps(
                    {'mcp': {'m': {'type': 'local', 'command': ['/absent'], 'disabled': True}}}))
            elif case == 'content':
                env['OPENCODE_CONFIG_CONTENT'] = json.dumps({'instructions': ['x']})
            else:
                env['OPENCODE_CONFIG_DIR'] = str(work)
            refuses(lambda: probe.static_guards(work, home, project, env))
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory).resolve() / 'work'
        home = work / 'home'
        denials = probe.ancestor_denials(home)
        assert work / 'opencode.json' in denials and Path('/opencode.json') in denials
        assert not any(home in path.parents for path in denials)
        assert not any(Path(directory).resolve() / name in probe.ancestor_denials(
            home, (Path(directory).resolve(),)) for name in probe.DISCOVERY_NAMES)
        assert probe.watch_label('/Library/Application Support', work) == 'MACHINE_PARENT'
        assert probe.watch_label(str(work / 'home'), work) == 'work/home'
        assert probe.watch_label('/', work) == 'UNOWNED_ANCESTOR'
        refuses(lambda: probe.watch_label('/Users', work))
        refuses(lambda: probe.watch_label('/Library/Application Support/opencode', work))
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory).resolve() / 'work'
        log = ('level=INFO message="watcher started" path="/Library/Application Support" type=entries\n'
               'level=WARN message="mcp connect failed" server=x\n'
               f'level=INFO message="watcher failed" path={work / "home"} type=entries\n')
        watches, _, problems = probe.log_inventory(log, work)
        assert problems == [('WARN', 'mcp connect failed')]
        assert ('work/home', 'entries', 'watcher failed') in watches
        assert ('MACHINE_PARENT', 'entries', 'watcher started') in watches
    print('PASS: native-only MCP, instruction/plugin/symlink/env guards, ancestor denials and watch labels')


INTERNAL = '''import { A } from "./a.js"
import { B as Renamed, type Unused as Ignored } from "./b.js"
import { Group } from "./group.js"
import Browser from "@opencode/browser"
const pre = [
  A.Plugin,
  ...Group,
  // comment
] as const satisfies readonly X[]
const post = [Renamed, Browser] as const satisfies readonly X[]
'''
FILES = {
    'core/src/plugin/a.ts': 'export * as A from "./a.js"\nexport const Plugin = define({\n  id: "opencode.a",\n})\n',
    'core/src/plugin/b.ts': '// constant\nexport const ID = "opencode.b"\nexport const make = () =>\n  define({ id: ID, effect })\n'
                            'export const B = make(real)\n',
    'core/src/plugin/group.ts': 'import { C } from "./c.js"\nexport const Group = [C, Local] as const\n'
                                'export const Local = make("opencode.local", x)\n',
    'core/src/plugin/c.ts': '// factory\nexport function make(\n  x = 1,\n) {\n  return define({\n    id: "opencode.c",\n  })\n}\n'
                            'export const C = make()\n',
    'browser/package.json': json.dumps({'exports': {'.': './src/index.ts'}}),
    'browser/src/index.ts': 'export default define({\n  id: "opencode.browser",\n})\n',
}


def derivation_cases():
    with tempfile.TemporaryDirectory() as directory:
        packages = Path(directory).resolve()
        for name, text in {'core/src/plugin/internal.ts': INTERNAL, **FILES}.items():
            (packages / name).parent.mkdir(parents=True, exist_ok=True)
            (packages / name).write_text(text)
        ids, files, _ = probe.expected_plugins(packages)
        assert ids == {'opencode.a', 'opencode.c', 'opencode.local', 'opencode.b', 'opencode.browser'}
        assert files == 6
        (packages / 'core/src/plugin/c.ts').write_text(FILES['core/src/plugin/c.ts'].replace('opencode.c', 'opencode.a'))
        refuses(lambda: probe.expected_plugins(packages))
        (packages / 'core/src/plugin/c.ts').write_text('export const C = somethingElse\n')
        refuses(lambda: probe.expected_plugins(packages))
        (packages / 'core/src/plugin/c.ts').write_text(FILES['core/src/plugin/c.ts'])
        (packages / 'core/src/plugin/internal.ts').write_text(INTERNAL.replace('"./a.js"', '"../../../../outside.js"'))
        refuses(lambda: probe.expected_plugins(packages))
    print('PASS: plugin ID derivation across namespace, spread, factory, constant and package exports')


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        observer_cases(root / 'project')
        redact_cases((root,))
        settle_cases((root,))
    guard_cases()
    derivation_cases()
    refuses(lambda: probe.owned_relative('relative/path', (Path('/x'),)))
    assert os.path.basename(probe.__file__) == 'chatgpt_installed_observer.py'


if __name__ == '__main__':
    main()
