#!/usr/bin/env python3
"""Offline catalog guard and metadata substitution cases; no runtime/database/network calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_catalog_control as helper
from chatgpt_installed_observer import build
from chatgpt_retained_state import create_root


def rejects(action):
    try:
        action()
    except (RuntimeError, OSError, ValueError, KeyError):
        return
    raise AssertionError('unsafe input accepted')


def guards():
    with tempfile.TemporaryDirectory(prefix='ah-catalog-offline-') as directory:
        work, token = create_root(Path(directory).resolve())
        home, project, env, _ = build(work, False, False)
        ctx = dict(work=work, token=token, home=home, project=project, env=env)
        body = helper.encoded({helper.PROBE_PROVIDER: {'name': 'synthetic'}})
        helper.install_catalog(ctx, body)
        assert helper.static_cases(ctx, body) == [
            'missing', 'malformed', 'same-ID-metadata', 'changed-bytes', 'symlink', 'hardlink']
        path = work / helper.CATALOG
        # Even a hash-approved malformed payload is refused.
        path.write_bytes(b'{')
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(b'{')))
        path.write_bytes(b'[]')
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(b'[]')))
        path.write_bytes(body)
        env['OPENCODE_DB'] = str(work / 'elsewhere.db')
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(body)))
        env.pop('OPENCODE_DB')
        env['OPENCODE_MODELS_PATH'] = str(work / 'other.catalog')
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(body)))
        env['OPENCODE_MODELS_PATH'] = str(path)
        env['OPENCODE_UNKNOWN'] = 'true'
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(body)))
        env.pop('OPENCODE_UNKNOWN')
        env['OPENCODE_DISABLE_MODELS_FETCH'] = 'false'
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(body)))
        env['OPENCODE_DISABLE_MODELS_FETCH'] = 'true'
        (work / '.ah-owner').write_text('wrong')
        rejects(lambda: helper.catalog_guard(ctx, helper.digest(body)))
    print('PASS: catalog file, root and environment refusals')


class Observer:
    def __init__(self, provider, model):
        self.provider, self.model = provider, model
    def get(self, path):
        assert path in ('/api/provider/abacus', '/api/model/default')
        return self.provider if path.endswith('abacus') else self.model


def metadata():
    provider = {'id': helper.PROBE_PROVIDER, 'name': 'AH explicit provider',
                'package': '@opencode/ai/providers/openai-compatible',
                'settings': {'baseURL': 'https://explicit.invalid/v1'}}
    model = {'providerID': helper.PROBE_PROVIDER, 'id': helper.PROBE_MODEL,
             'name': 'AH explicit model', 'limit': {'context': 4096},
             'settings': {'baseURL': 'https://explicit.invalid/v1'}}
    helper.probe(Observer(provider, model), 'explicit')
    for field, value in [('name', 'bundled provider'), ('settings', {'baseURL': 'https://cached.invalid/v1'}),
                         ('package', 'other')]:
        changed = copy.deepcopy(provider)
        changed[field] = value
        rejects(lambda: helper.probe(Observer(changed, model), 'explicit'))
    for field, value in [('id', 'bundled-model'), ('name', 'AH cached model'),
                         ('settings', {'baseURL': 'https://cached.invalid/v1'}), ('limit', {'context': 1})]:
        changed = copy.deepcopy(model)
        changed[field] = value
        rejects(lambda: helper.probe(Observer(provider, changed), 'explicit'))
    assert '/api/session' not in helper.CatalogObserver.allowed
    assert not any('connect' in route or 'kv' in route for route in helper.CatalogObserver.allowed)
    print('PASS: same-ID metadata and bundled/cache fallback cannot satisfy explicit probe')


if __name__ == '__main__':
    guards()
    metadata()
