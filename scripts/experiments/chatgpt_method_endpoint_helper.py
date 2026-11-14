#!/usr/bin/env python3
"""Opt-in pinned macOS method/endpoint/helper proof on an operator-login retained root (P7.9).

Requires a root that already passes ``chatgpt_login_preflight.py``. Network stays fully denied.
No session, model turn or credential export.
"""
import argparse
import hashlib
import http.client
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import urllib.parse
from pathlib import Path

from antigravity_feasibility import check
from chatgpt_contained import owned_server
from chatgpt_feasibility import SHA256
from chatgpt_installed_observer import BODY_LIMIT, REQUEST_TIMEOUT, static_guards, verify_source
from chatgpt_login_preflight import LoginPreflightRefusal, attach, boundary_controls
from chatgpt_retained_state import (
    PreflightObserver,
    PUBLISHED_INTEGRATION_COUNT,
    PUBLISHED_INTEGRATION_DIGEST,
    acquire,
    ancestor_denials,
    combined_profile,
    database_path,
    evaluate,
    fresh_port,
    integration_digest,
    lock_probe,
    resources_ready,
    root_shape,
    settle_view,
)

CHATGPT_SOURCE = 'core/src/plugin/provider/chatgpt.ts'
CHATGPT_SHA256 = 'cbb119fa3f231f5b79b588916ad23afc1f6fa71529332bcae8f7fadaa98e8bd2'
PACKAGE_ID = 'opencode.provider.chatgpt'
SAFE_PROVIDER_SETTINGS = frozenset({'baseURL', 'encoding', 'transport'})


class MethodProofObserver(PreflightObserver):
    """Preflight observer plus redacted method, endpoint and helper routes."""

    allowed = dict(PreflightObserver.allowed, **{
        '/api/integration/openai': 'object',
        '/api/provider/openai': 'object',
        '/api/model/default': 'object',
    })

    def get(self, path):
        check(path in self.allowed)
        kind = self.allowed[path]
        query = ''
        if kind in (True, 'object'):
            query = '?' + urllib.parse.urlencode({'location[directory]': str(self.location)})
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
        if kind is False:
            return value
        check(isinstance(value, dict) and set(value) == {'location', 'data'})
        check(value['location'] == {'directory': str(self.location)})
        data = value['data']
        if kind is True:
            check(isinstance(data, list))
        return data


def expectations_from_source(text):
    method = re.search(r'const methodID = Integration\.MethodID\.make\("([^"]+)"\)', text)
    resource = re.search(r'const resource = "([^"]+)"', text)
    provider = re.search(r'const providerID = Provider\.ID\.(\w+)', text)
    check(method and resource and provider)
    fallback = re.search(r'const fallbackModels = new Set\(\[((?:\s*"[^"]+",?)+)\s*\]\)', text, re.S)
    check(fallback)
    models = re.findall(r'"([^"]+)"', fallback.group(1))
    check('gpt-6.1-sol' in models)
    return {'method_id': method.group(1), 'resource': resource.group(1),
            'provider_id': provider.group(1), 'helper_model': 'gpt-6.1-sol', 'package_id': PACKAGE_ID}


def pinned_expectations(packages):
    path = packages / CHATGPT_SOURCE
    check(hashlib.sha256(path.read_bytes()).hexdigest() == CHATGPT_SHA256)
    return expectations_from_source(path.read_text())


def merge_helper_config(env, helper):
    document = json.loads(env['OPENCODE_CONFIG_CONTENT'])
    model = {'providerID': helper['provider_id'], 'model': helper['helper_model']}
    document['model'] = model
    document['agents'] = {'title': {'model': model}}
    return dict(env, OPENCODE_CONFIG_CONTENT=json.dumps(document))


def redact_provider(info, expected_resource):
    check(isinstance(info, dict) and info.get('id') == 'openai')
    settings = info.get('settings') or {}
    check(isinstance(settings, dict))
    cleaned = {key: settings[key] for key in settings if key in SAFE_PROVIDER_SETTINGS}
    check(cleaned.get('baseURL') == expected_resource)
    package = info.get('package')
    check(package == PACKAGE_ID)
    return {'id': 'openai', 'package': package, 'activation': info.get('activation'), 'settings': cleaned}


def openai_method_proof(integration, expected):
    check(integration.get('id') == 'openai')
    methods = {(item.get('type'), item.get('id', '')) for item in integration.get('methods', [])}
    check(('oauth', expected['method_id']) in methods)
    connections = integration.get('connections', [])
    check(len(connections) == 1 and connections[0].get('type') == 'credential')
    check(connections[0].get('method') == 'oauth' and 'status' not in connections[0])
    method_id = connections[0].get('methodID')
    if method_id is not None:
        check(method_id == expected['method_id'])


def model_default_proof(data, helper):
    check(data is not None and isinstance(data, dict))
    model_id = data.get('modelID') or data.get('id')
    check(data.get('providerID') == helper['provider_id'] and model_id == helper['helper_model'])


def method_proof_boot(ctx, expected):
    runtime, work, home, project, env, token, builtin = (ctx[k] for k in (
        'runtime', 'work', 'home', 'project', 'env', 'token', 'builtin'))
    check(not root_shape(work, token, env))
    owned = (work,)
    env = merge_helper_config(env, expected)
    password = secrets.token_urlsafe(32)
    env = dict(env, OPENCODE_PASSWORD=password)
    port = fresh_port()
    policy = combined_profile(work, port, ancestor_denials(home))
    check(database_path(runtime, project, env, policy, work))
    summary = {}
    with owned_server(runtime, project, env, policy, port):
        observer = MethodProofObserver(port, password, project)
        check(observer.locations() == [])
        resources, integrations, identities = settle_view(observer, owned, resources_ready(builtin))
        check(observer.locations() == [str(project)])
        check(integration_digest(integrations) == PUBLISHED_INTEGRATION_DIGEST)
        check(len(integrations) == PUBLISHED_INTEGRATION_COUNT)
        login_refusals = evaluate((resources, integrations, identities, set()), frozenset(integrations), builtin)[1]
        if login_refusals:
            raise LoginPreflightRefusal(
                f'login preflight failed: {login_refusals!r}; complete operator login first')
        openai = observer.get('/api/integration/openai')
        openai_method_proof(openai, expected)
        provider = observer.get('/api/provider/openai')
        redacted = redact_provider(provider, expected['resource'])
        model_default = observer.get('/api/model/default')
        model_default_proof(model_default, expected)
        summary = {
            'method': expected['method_id'],
            'resource': redacted['settings']['baseURL'],
            'package': redacted['package'],
            'helper_model': model_default.get('modelID') or model_default.get('id'),
            'provider_id': model_default.get('providerID'),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode', help='installed executable on PATH')
    parser.add_argument('--source', type=Path, required=True, help='official v2.2.5 checkout (D071 procedure)')
    parser.add_argument('--root', type=Path, required=True, help='owned root after operator login')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    installed = shutil.which(args.opencode)
    check(installed is not None)
    packages, _ = verify_source(args.source.resolve())
    expected = pinned_expectations(packages)
    from chatgpt_installed_observer import expected_plugins
    builtin, _, _ = expected_plugins(packages)
    with tempfile.TemporaryDirectory(prefix='ah-method-helper-bin-') as directory:
        runtime = Path(directory).resolve() / 'opencode-cli'
        shutil.copy2(installed, runtime)
        check(hashlib.sha256(runtime.read_bytes()).hexdigest() == SHA256)
        boundary = boundary_controls(args.root.resolve())
        ctx = attach(args.root, runtime, builtin)
        static_guards(ctx['work'], ctx['home'], ctx['project'], ctx['env'], login_state=True)
        held = acquire(ctx['work'])
        check(held is not None)
        try:
            check(lock_probe(ctx['work']) == 'refused')
            summary = method_proof_boot(ctx, expected)
        finally:
            os.close(held)
        check(lock_probe(ctx['work']) == 'acquired')
    print('PASS: method, endpoint and helper selection match pinned ChatGPT plugin constants', flush=True)
    print(json.dumps({'origin_boundary': boundary, 'proof': summary}, indent=1, sort_keys=True))
    print('LIMIT: retained-login metadata only; deny/trusted, account credits-off and D034 remain open')


if __name__ == '__main__':
    try:
        main()
    except LoginPreflightRefusal as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('Method/endpoint/helper proof failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)