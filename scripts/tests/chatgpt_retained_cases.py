#!/usr/bin/env python3
"""Offline D077 preflight, seeder, root, lock and cross-check refusals; no OpenCode or external network."""
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_retained_state as probe


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
            calls.append(('connect', host, port))

        def request(self, method, path, body=None, headers=None):
            calls.append(('request', method, path, body, headers['Connection']))

        def getresponse(self):
            return response

        def close(self):
            calls.append(('close',))
    return Connection


def route_cases(location):
    good = json.dumps({'location': {'directory': str(location)}, 'data': []}).encode()
    calls = []
    observer = probe.PreflightObserver(4242, 'synthetic', location, fake(Response(200, good), calls))
    for path in ('/api/credential', '/api/integration/opencode', '/api/experimental/integration/wellknown',
                 '/api/integration/opencode/connect/key', '/api/session', '/api/usage'):
        refuses(lambda: observer.get(path))
    assert not calls, 'refused routes must not connect'
    assert observer.get(probe.INTEGRATION) == []
    assert calls[1][1] == 'GET' and calls[1][2].startswith(probe.INTEGRATION + '?location%5Bdirectory%5D=')
    assert '/api/integration' not in probe.ALLOWED, 'the D076 observer must stay without integration.list'

    calls = []
    seeder = probe.Seeder(4242, 'synthetic', location, None, fake(Response(204, b''), calls))
    refuses(lambda: seeder.post('wellknown'))  # No owned origin given.
    refuses(lambda: seeder.post('credential'))
    assert not calls
    seeder.post('console')
    method, path, body = calls[1][1:4]
    assert method == 'POST' and path.startswith(probe.SEED_ROUTES['console'] + '?')
    assert json.loads(body) == {'key': probe.MARKER, 'label': 'ah-synthetic'}
    for origin in ('https://example.com', 'http://localhost:1', 'http://127.0.0.1:1/path', 'http://10.0.0.1:80'):
        refuses(lambda: probe.Seeder(4242, 'synthetic', location, origin))
    calls = []
    probe.Seeder(4242, 'synthetic', location, 'http://127.0.0.1:4243',
                 fake(Response(204, b''), calls)).post('wellknown')
    assert json.loads(calls[1][3]) == {'url': 'http://127.0.0.1:4243'}
    for response in (Response(200, b''), Response(204, b'x'), Response(302, b'')):
        refuses(lambda: probe.Seeder(4242, 'synthetic', location, None, fake(response, [])).post('console'))
    print('PASS: integration.list is the only added read; seeder has two exact routes and loopback origins')


def integration(identifier, methods=({'type': 'key'},), connections=()):
    return {'id': identifier, 'name': identifier, 'methods': list(methods), 'connections': list(connections)}


OAUTH = {'type': 'credential', 'id': 'cred_synthetic', 'label': 'person@example.invalid', 'method': 'oauth'}


def redact_cases():
    record, identities = probe.redact_integrations([
        integration('openai', ({'type': 'oauth', 'id': 'chatgpt-token-sharing', 'label': 'ChatGPT'},
                               {'type': 'env', 'names': ['OPENAI_API_KEY']}), (OAUTH,)),
        integration('x', ({'type': 'key', 'label': 'k', 'form': []},))])
    assert record['openai'] == ((('env', ''), ('oauth', 'chatgpt-token-sharing')), (('credential', 'oauth', ''),))
    assert 'person@example.invalid' not in json.dumps(record) and 'cred_synthetic' not in json.dumps(record)
    assert set(identities) == {'openai'} and all(len(d) == 64 for d in identities['openai'])
    assert 'person@example.invalid' not in json.dumps(sorted(identities['openai']))
    for bad in (
            [dict(integration('a'), secret='x')],
            [integration('a'), integration('a')],
            [integration('a', ({'type': 'password'},))],
            [integration('a', ({'type': 'key', 'value': 'x'},))],
            [integration('a', ({'type': 'command', 'id': 'login', 'label': 'l'},))],
            [integration('a', connections=(dict(OAUTH, key='secret'),))],
            [integration('a', connections=(dict(OAUTH, method='password'),))],
            [integration('a', connections=(dict(OAUTH, status={'status': 'broken', 'message': 'm'}),))],
            [integration('a', connections=({'type': 'credential', 'id': 'c', 'method': 'oauth'},))],
            [integration('a', connections=({'type': 'other'},))],
            {'not': 'a list'}):
        refuses(lambda: probe.redact_integrations(bad))
    print('PASS: strict integration schema; labels and connection IDs never recorded')


def resources_for(builtin):
    commands, skills, mcp = probe.expected(False, False)
    return {'command': [(c, None) for c in sorted(commands)], 'skill': [(s, s) for s in sorted(skills)],
            'mcp': sorted(mcp), 'plugin': [(p, 'builtin', None, 'active') for p in sorted(builtin)]}


def preflight_cases():
    builtin = frozenset({'opencode.a', 'opencode.b'})
    resources = resources_for(builtin)
    documents = {'CONFIG/opencode/opencode.json'}
    expected = frozenset({'openai', 'opencode', 'xai'})
    none = {'openai': ((), ()), 'opencode': ((), ()), 'xai': ((), ())}

    def run(integrations, login, resources=resources, documents=documents):
        return probe.preflight(integrations, resources, documents, expected, builtin, login)
    oauth = (('credential', 'oauth', ''),)
    assert run(none, False) == [] and run(none, True) == ['openai-connection']
    assert run(dict(none, openai=((), oauth)), True) == []
    assert run(dict(none, openai=((), oauth)), False) == ['openai-connection']
    for connections in ((('credential', 'oauth', 'needs_auth'),), (('credential', 'key', ''),),
                        oauth + oauth, (('env', '', ''),)):
        assert run(dict(none, openai=((), connections)), True) == ['openai-connection']
    assert run(dict(none, opencode=((), (('credential', 'key', ''),))), False) == ['console-connection']
    assert run(dict(none, xai=((), (('env', '', ''),))), False) == ['other-connection']
    assert run(dict(none, extra=((('command', 'login'),), ())), False) == ['integration-set']
    assert run({'opencode': ((), ()), 'xai': ((), ())}, True) == ['integration-set', 'openai-connection']
    assert run(none, False, dict(resources, command=resources['command'][1:])) == ['resources']
    assert run(none, False, dict(resources, plugin=resources['plugin'][1:])) == ['resources']
    assert run(none, False, documents=documents | {'home/repo/opencode.json'}) == ['config-documents']
    print('PASS: preflight invariants: exact set, one healthy openai oauth for login, no Console or other connections')


def root_cases():
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory).resolve()
        work, token = probe.create_root(base)
        assert work.stat().st_mode & 0o777 == 0o700 and (work / probe.OWNER).stat().st_mode & 0o777 == 0o600
        try:
            probe.create_root(base)
        except FileExistsError:
            pass
        else:
            raise AssertionError('root creation must be exclusive')
        env = {'XDG_DATA_HOME': str(work / 'DATA')}
        assert probe.root_shape(work, token, env) == []
        assert probe.root_shape(work, token, dict(env, OPENCODE_DB=str(work / 'x.db'))) == ['database-override']
        assert probe.root_shape(work, token, {'XDG_DATA_HOME': str(base)}) == ['database-override']
        assert probe.root_shape(work, 'other', env) == ['root-marker']
        data = work / 'DATA' / 'opencode'
        data.mkdir(parents=True)
        (data / 'auth.json').symlink_to(work / 'absent')  # Dangling: detected by name, never followed.
        assert probe.root_shape(work, token, env) == ['legacy-auth-file']
        (data / 'auth.json').unlink()
        (work / probe.OWNER).unlink()
        (work / probe.OWNER).symlink_to(work / 'elsewhere')
        (work / 'elsewhere').write_text(token)
        assert probe.root_shape(work, token, env) == ['root-marker']

        held = probe.acquire(work)
        assert held is not None
        try:
            assert probe.acquire(work) is None
            assert probe.lock_probe(work) == 'refused'
        finally:
            os.close(held)
        assert probe.lock_probe(work) == 'acquired'
    print('PASS: exclusive 0700 root and marker, name-only auth.json and override refusals, advisory lock')


PROVIDER = '''export const ID = Object.assign(schema, {
    claudeAgent: schema.make("claude-agent"),
    azure: schema.make("azure"),
})
'''
PLUGINS = {
    'schema/src/provider.ts': PROVIDER,
    'core/src/plugin/one.ts': 'import { Helper } from "./helper.js"\nyield* ctx.integration.transform((editor) => {\n'
                              '  editor.update("alpha", (i) => {})\n  editor.method.update({ integrationID: "beta" })\n'
                              '  editor.method.update({ integrationID: Provider.ID.azure })\n})\n',
    'core/src/plugin/helper.ts': 'import { ClaudeProvider } from "./provider.js"\n'
                                 'export const Helper = { integrationID: ClaudeProvider.ID }\n',
    'core/src/plugin/provider.ts': 'import { Provider } from "./p.js"\nexport const ID = Provider.ID.claudeAgent\n',
    'core/src/wellknown/plugin.ts': 'yield* ctx.integration.transform((editor) => {\n'
                                    '  editor.method.update({ integrationID: entry.integrationID, method: {\n'
                                    '    id: "login",\n    type: "command",\n  } })\n})\n',
}


def cross_check_cases():
    with tempfile.TemporaryDirectory() as directory:
        packages = Path(directory).resolve()
        for name, text in PLUGINS.items():
            (packages / name).parent.mkdir(parents=True, exist_ok=True)
            (packages / name).write_text(text)
        files = [packages / 'core/src/plugin/one.ts', packages / 'core/src/wellknown/plugin.ts']
        found = probe.literal_integrations(packages, files)
        assert set(found) == {'alpha', 'beta', 'azure', 'claude-agent'}
        assert found['claude-agent'] == {'core/src/plugin/helper.ts'}
        (packages / 'core/src/plugin/one.ts').write_text(PLUGINS['core/src/plugin/one.ts'] + 'const m = { method: {'
                                                         ' type: "command" } }\n')
        refuses(lambda: probe.literal_integrations(packages, files))
        (packages / 'core/src/plugin/one.ts').write_text(PLUGINS['core/src/plugin/one.ts'].replace('"beta"', '"Bad/ID"'))
        refuses(lambda: probe.literal_integrations(packages, files))
        (packages / 'core/src/plugin/one.ts').write_text(PLUGINS['core/src/plugin/one.ts'])
        (packages / 'core/src/plugin/provider.ts').write_text('// alias\nexport const ID = "claude-agent"\n')
        refuses(lambda: probe.literal_integrations(packages, files))
    assert probe.integration_digest({'b', 'a'}) == probe.integration_digest(['a', 'b'])
    print('PASS: integration cross-check over literals, constants and one-hop aliases; only well-known commands')


def origin_cases():
    with tempfile.TemporaryDirectory() as directory:
        command = Path(directory).resolve() / 'denied-bin' / 'absent'
        with probe.SyntheticOrigin(probe.fresh_port(), command) as origin:
            port = origin.server.server_address[1]
            for path, status in (('/.well-known/opencode', 200), ('/other', 404)):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
                connection.request('GET', path)
                response = connection.getresponse()
                body = response.read()
                connection.close()
                assert response.status == status
            assert json.loads(body or b'null') is None
            assert origin.hits == {'manifest': 1, 'other': 1}
        manifest = json.dumps({'auth': {'command': [str(command)], 'env': 'AH_SYNTHETIC_TOKEN'}})
        assert 'config' not in manifest and 'remote_config' not in manifest
    print('PASS: synthetic origin serves one auth-only manifest on loopback and counts requests')


def settle_cases():
    views = iter([(1,), (1,), (2,), (2,)])
    original = probe.view
    try:
        probe.view = lambda observer, owned: next(views)
        assert probe.settle_view(None, (), lambda v: True, sleep=lambda s: None) == (1,)
        clock = iter(range(0, 1000, 10))
        probe.view = lambda observer, owned: ('never',)
        refuses(lambda: probe.settle_view(None, (), lambda v: False, clock=lambda: next(clock),
                                          sleep=lambda s: None))
    finally:
        probe.view = original
    print('PASS: settle requires two identical ready reads and times out')


def main():
    with tempfile.TemporaryDirectory() as directory:
        route_cases(Path(directory).resolve() / 'project')
    redact_cases()
    preflight_cases()
    root_cases()
    cross_check_cases()
    origin_cases()
    settle_cases()
    assert os.path.basename(probe.__file__) == 'chatgpt_retained_state.py'


if __name__ == '__main__':
    main()
