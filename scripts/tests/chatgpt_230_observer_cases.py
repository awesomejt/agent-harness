#!/usr/bin/env python3
"""Offline 2.3.0 observer safety/readiness cases. No runtime, state store or network."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_230_observer as helper
from chatgpt_observer_cases import Response, fake, refuses


def main():
    with tempfile.TemporaryDirectory(prefix='ah-230-observer-cases-') as directory:
        work = Path(directory).resolve()
        calls = []
        good = json.dumps({'location': {'directory': str(work)}, 'data': []}).encode()
        observer = helper.Observer(4242, 'synthetic', work, fake(Response(200, good), calls))
        assert observer.get(helper.PROVIDER) == []
        assert observer.get(helper.INTEGRATION) == []
        before = len(calls)
        for route in ('/api/session', '/api/credential', '/api/integration/opencode/connect/key', '/api/model', '/api/event'):
            refuses(lambda: observer.get(route))
        assert len(calls) == before
        print('PASS: only bounded provider/integration GET additions; mutation/session/model routes refused')

        wanted = ({'sentinel-command'}, {'sentinel-skill'}, {('sentinel-mcp', 'disabled')})
        builtin = frozenset({'opencode.one', 'opencode.two'})
        view = {'plugin': [(name, 'builtin', None, 'active') for name in sorted(builtin)],
                'command': [('sentinel-command', None)],
                'skill': [('sentinel-skill', 'sentinel-skill', 'owned', 'digest', 1)],
                'mcp': [('sentinel-mcp', 'disabled')]}
        integrations = {'one': ((('key', ''),), ()), 'two': ((('oauth', 'method'),), ())}
        digest = helper.integration_digest(integrations)
        with patch.object(helper, 'PUBLISHED_INTEGRATION_COUNT', 2), patch.object(helper, 'PUBLISHED_INTEGRATION_DIGEST', digest):
            assert helper.validate((view, integrations), builtin, wanted)
            incomplete = dict(view, plugin=[], command=[], skill=[], mcp=[])
            assert not helper.validate((incomplete, integrations), builtin, wanted)
            for bad_view, bad_integrations in (
                (incomplete, dict(integrations, one=((), (('credential', 'key', ''),)))),
                (incomplete, dict(integrations, third=((), ()))),
                (incomplete, dict(integrations, one=((('command', 'login'),), ()))),
                (dict(incomplete, plugin=[('unexpected', 'builtin', None, 'active')]), integrations),
                (dict(incomplete, plugin=[('opencode.one', 'builtin', None, 'failed')]), integrations),
                (dict(incomplete, command=[('unexpected', None)]), integrations),
                (dict(incomplete, mcp=[('sentinel-mcp', 'pending')]), integrations),
            ):
                refuses(lambda: helper.validate((bad_view, bad_integrations), builtin, wanted))
            print('PASS: unsafe connections/inventory/methods/plugins/resources refuse despite incomplete readiness')

            now = [0.0]
            observations = [incomplete, view, incomplete, view, view]
            def sleep(delay):
                now[0] += delay
                if len(observations) > 1:
                    observations.pop(0)
            with patch.object(helper, 'observe', side_effect=lambda *_: (observations[0], integrations)) as observe:
                assert helper.settle(None, work, builtin, wanted, clock=lambda: now[0], sleep=sleep) == (view, integrations)
                assert observe.call_count == 5
            # An unsafe first observation must stop before a subsequent safe one.
            unsafe = dict(integrations, one=((), (('credential', 'key', ''),)))
            with patch.object(helper, 'observe', side_effect=[(incomplete, unsafe), (view, integrations)]) as observe:
                refuses(lambda: helper.settle(None, work, builtin, wanted))
                assert observe.call_count == 1
            with patch.object(helper, 'observe', return_value=(incomplete, integrations)):
                refuses(lambda: helper.settle(None, work, builtin, wanted, clock=lambda: now[0], sleep=sleep))
            with patch.object(helper, 'observe', side_effect=TimeoutError) as observe:
                try:
                    helper.settle(None, work, builtin, wanted)
                except TimeoutError:
                    pass
                else:
                    raise AssertionError('unknown timeout accepted')
                assert observe.call_count == 1
            with patch.object(helper, 'observe', side_effect=[helper.StartupPending(), (view, integrations), (view, integrations)]) as observe:
                assert helper.settle(None, work, builtin, wanted, clock=lambda: now[0], sleep=sleep) == (view, integrations)
                assert observe.call_count == 3
            with patch.object(helper, 'observe', side_effect=ConnectionResetError) as observe:
                try:
                    helper.settle(None, work, builtin, wanted)
                except ConnectionResetError:
                    pass
                else:
                    raise AssertionError('post-barrier reset retried')
                assert observe.call_count == 1
            print('PASS: stable ready reads/reset/deadline; only initial barrier failures retry')

        class Raw:
            def __init__(self, providers, integrations, skills=()):
                self.calls, self.providers, self.integrations, self.skills = [], providers, integrations, skills
            def get(self, route):
                self.calls.append(route)
                if route == helper.PROVIDER:
                    return self.providers
                if route == helper.INTEGRATION:
                    return self.integrations
                return list(self.skills) if route == '/api/skill' else []
        provider = {'id': 'synthetic', 'name': 'Synthetic', 'activation': 'auto', 'package': 'synthetic',
                    'settings': {'apiKey': 'AH_SYNTHETIC_SECRET'}}
        integration = {'id': 'one', 'name': 'One', 'methods': [{'type': 'key'}], 'connections': []}
        raw = Raw([provider], [integration])
        observation = helper.observe(raw, work)
        assert raw.calls[:2] == [helper.PROVIDER, helper.INTEGRATION]
        assert 'AH_SYNTHETIC_SECRET' not in json.dumps(observation)
        for providers in ([dict(provider, unexpected='x')], [provider, provider], [dict(provider, activation='invalid')]):
            refuses(lambda: helper.observe(Raw(providers, [integration]), work))
        refuses(lambda: helper.observe(Raw([provider], [dict(integration, metadata={'source': 'remote'})]), work))
        for identifier in helper.old.BUILTIN_SKILLS:
            skill = {'id': identifier, 'name': identifier, 'path': f'skill://{identifier}/SKILL.md', 'content': 'AH_BODY'}
            result = helper.observe(Raw([provider], [integration], [skill]), work)
            assert 'AH_BODY' not in json.dumps(result)
            refuses(lambda: helper.observe(Raw([provider], [integration], [dict(skill, path='skill://other/SKILL.md')]), work))
        class LaterReset(Raw):
            barriers = 0
            def get(self, route):
                if route == helper.PROVIDER:
                    self.barriers += 1
                    if self.barriers > 1:
                        raise ConnectionResetError
                return super().get(route)
        raw = LaterReset([provider], [integration])
        with patch.object(helper, 'PUBLISHED_INTEGRATION_COUNT', 1), patch.object(
                helper, 'PUBLISHED_INTEGRATION_DIGEST', helper.integration_digest({'one'})):
            try:
                helper.settle(raw, work, frozenset(), ({'waiting'}, set(), set()), sleep=lambda _: None)
            except helper.Refusal as error:
                assert str(error) == 'barrier-reset'
            else:
                raise AssertionError('later wrapped barrier reset retried')
            assert raw.barriers == 2
        print('PASS: barrier ordering/discard/URIs; later wrapped barrier reset refuses without retry')

        home, project, env, _ = helper.old.build(work, False, False)
        helper.old.static_guards(work, home, project, env)
        refuses(lambda: helper.old.static_guards(work, home, project, dict(env, OPENCODE_API_KEY='AH_SYNTHETIC')))
        assert 'deny file-read-data (literal ' in helper.policy(work, 4242, home, listing_denied=True)
        assert helper.SHA256 != __import__('chatgpt_feasibility').SHA256
        print('PASS: inherited Console-key refusal, fallback policy and separate experimental executable pin')


if __name__ == '__main__':
    main()
