#!/usr/bin/env python3
"""Opt-in pinned macOS deny/trusted permission proof on an operator-login retained root (P7.9).

Requires a root that already passes ``chatgpt_login_preflight.py``. Network stays fully denied.
Uses ``debug agents`` only; no session, model turn or credential export.
"""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

from antigravity_feasibility import check
from chatgpt_contained import diagnostic, owned_server, validate_agents
from chatgpt_feasibility import SHA256
from chatgpt_installed_observer import static_guards, verify_source
from chatgpt_login_preflight import LoginPreflightRefusal, attach, boundary_controls
from chatgpt_method_endpoint_helper import merge_helper_config, pinned_expectations
from chatgpt_retained_state import (
    PUBLISHED_INTEGRATION_COUNT,
    PUBLISHED_INTEGRATION_DIGEST,
    PreflightObserver,
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

DENY_RULES = (
    {'action': '*', 'resource': '*', 'effect': 'deny'},
    {'action': 'external_directory', 'resource': '*', 'effect': 'deny'},
)
# Same shape as scripts/tests/agents_exec.py TRUSTED (seven rules).
TRUSTED_RULES = (
    {'action': '*', 'resource': '*', 'effect': 'deny'},
) + tuple(
    dict(action=action, resource='*', effect='ask')
    for action in ('read', 'glob', 'grep', 'edit', 'shell')
) + ({'action': 'external_directory', 'resource': '*', 'effect': 'ask'},)
TRUSTED_AGENT_ID = 'trusted-coder'


def validate_trusted_agent(agent, model, rules):
    """Require the harness trusted ask profile as a sublist; refuse any allow effect."""
    check(isinstance(agent, dict) and agent.get('id') == TRUSTED_AGENT_ID)
    resolved = {'id': model['model'], 'providerID': model['providerID']}
    check(agent.get('model') == resolved)
    check(agent['request'] == {'settings': {}, 'headers': {}, 'body': {}})
    effective = agent['permissions']
    serialized = list(rules)
    matches = [index for index in range(len(effective)) if effective[index:index + len(serialized)] == serialized]
    check(matches)
    check(all(rule['effect'] in ('deny', 'ask') for rule in effective))
    check('allow' not in {rule['effect'] for rule in effective})


def merge_permission_config(env, helper, deny_rules, trusted_rules):
    env = merge_helper_config(env, helper)
    document = json.loads(env['OPENCODE_CONFIG_CONTENT'])
    model = document['model']
    document['permissions'] = list(deny_rules)
    document['policies'] = [
        {'action': 'provider.use', 'resource': '*', 'effect': 'deny'},
        {'action': 'provider.use', 'resource': 'openai', 'effect': 'allow'},
    ]
    document.setdefault('instructions', [])
    document.setdefault('mcp', {})
    document.setdefault('plugins', [])
    document.setdefault('providers', {})
    document['agents'] = {
        'title': {'model': model},
        TRUSTED_AGENT_ID: {'model': model, 'permissions': list(trusted_rules)},
    }
    return dict(env, OPENCODE_CONFIG_CONTENT=json.dumps(document))


def permission_proof_boot(ctx, helper):
    runtime, work, home, project, env, token, builtin = (ctx[k] for k in (
        'runtime', 'work', 'home', 'project', 'env', 'token', 'builtin'))
    check(not root_shape(work, token, env))
    owned = (work,)
    env = merge_permission_config(env, helper, DENY_RULES, TRUSTED_RULES)
    password = secrets.token_urlsafe(32)
    env = dict(env, OPENCODE_PASSWORD=password)
    port = fresh_port()
    policy = combined_profile(work, port, ancestor_denials(home))
    check(database_path(runtime, project, env, policy, work))
    summary = {}
    with owned_server(runtime, project, env, policy, port) as url:
        observer = PreflightObserver(port, password, project)
        check(observer.locations() == [])
        resources, integrations, identities = settle_view(observer, owned, resources_ready(builtin))
        check(observer.locations() == [str(project)])
        check(integration_digest(integrations) == PUBLISHED_INTEGRATION_DIGEST)
        check(len(integrations) == PUBLISHED_INTEGRATION_COUNT)
        login_refusals = evaluate((resources, integrations, identities, set()), frozenset(integrations), builtin)[1]
        if login_refusals:
            raise LoginPreflightRefusal(
                f'login preflight failed: {login_refusals!r}; complete operator login first')
        raw, _ = diagnostic(runtime, project, env, policy, ('debug', 'agents'), url)
        agents = json.loads(raw)
        model = {'providerID': helper['provider_id'], 'model': helper['helper_model']}
        trusted = [agent for agent in agents if agent.get('id') == TRUSTED_AGENT_ID]
        check(len(trusted) == 1)
        validate_trusted_agent(trusted[0], model, TRUSTED_RULES)
        defaults = [agent for agent in agents if agent.get('id') != TRUSTED_AGENT_ID]
        validate_agents(defaults, model, list(DENY_RULES), False)
        default_ids = sorted(agent['id'] for agent in defaults)
        summary = {
            'agents_reported': len(agents),
            'default_agent_ids': default_ids,
            'default_permission_lengths': [len(agent['permissions']) for agent in defaults],
            'trusted_agent': TRUSTED_AGENT_ID,
            'trusted_permission_length': len(trusted[0]['permissions']),
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
    helper = {key: expected[key] for key in ('provider_id', 'helper_model')}
    with tempfile.TemporaryDirectory(prefix='ah-permission-helper-bin-') as directory:
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
            summary = permission_proof_boot(ctx, helper)
        finally:
            os.close(held)
        check(lock_probe(ctx['work']) == 'acquired')
    print('PASS: deny-default and trusted ask-only profiles reported on login root', flush=True)
    print(json.dumps({'origin_boundary': boundary, 'proof': summary}, indent=1, sort_keys=True))
    print('LIMIT: debug-agent permission metadata only; account credits-off and D034 remain open')


if __name__ == '__main__':
    try:
        main()
    except LoginPreflightRefusal as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('Permission proof failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)