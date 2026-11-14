#!/usr/bin/env python3
"""Offline deny/trusted permission expectation checks; no OpenCode or network."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_permission_proof as permission


def rejects(action):
    try:
        action()
    except (RuntimeError, ValueError, TypeError, AttributeError, AssertionError):
        return
    raise AssertionError('unsafe input was accepted')


def trusted_cases():
    model = {'providerID': 'openai', 'model': 'gpt-6.1-sol'}
    resolved = {'id': model['model'], 'providerID': model['providerID']}
    agent = {'id': permission.TRUSTED_AGENT_ID, 'model': resolved,
             'request': {'settings': {}, 'headers': {}, 'body': {}},
             'permissions': list(permission.TRUSTED_RULES)}
    permission.validate_trusted_agent(agent, model, permission.TRUSTED_RULES)
    prefixed_deny = list(permission.DENY_RULES) + list(permission.TRUSTED_RULES)
    permission.validate_trusted_agent({**agent, 'permissions': prefixed_deny}, model, permission.TRUSTED_RULES)
    prefixed_allow = [{'action': 'builtin', 'resource': '*', 'effect': 'allow'}] + list(permission.TRUSTED_RULES)
    permission.validate_trusted_agent({**agent, 'permissions': prefixed_allow}, model, permission.TRUSTED_RULES)
    rejects(lambda: permission.validate_trusted_agent(
        {**agent, 'permissions': list(permission.TRUSTED_RULES) + list(permission.DENY_RULES)},
        model, permission.TRUSTED_RULES))
    for mutation in (
            {'id': 'other'},
            {'model': None},
            {'model': {'id': 'other', 'providerID': 'openai'}},
            {'request': {'settings': {'secret': 1}, 'headers': {}, 'body': {}}},
            {'permissions': list(permission.DENY_RULES)},
            {'permissions': prefixed_deny + [{'action': 'shell', 'resource': '*', 'effect': 'allow'}]},
    ):
        rejects(lambda: permission.validate_trusted_agent({**agent, **mutation}, model, permission.TRUSTED_RULES))
    print('PASS: trusted agent validation requires harness ask tail', flush=True)


def merge_cases():
    env = {'OPENCODE_CONFIG_CONTENT': json.dumps({'update': 'disable', 'share': 'disabled'})}
    helper = {'provider_id': 'openai', 'helper_model': 'gpt-6.1-sol'}
    merged = permission.merge_permission_config(env, helper, permission.DENY_RULES, permission.TRUSTED_RULES)
    document = json.loads(merged['OPENCODE_CONFIG_CONTENT'])
    assert document['permissions'] == list(permission.DENY_RULES)
    assert document['agents']['title']['model']['model'] == 'gpt-6.1-sol'
    trusted = document['agents'][permission.TRUSTED_AGENT_ID]
    assert trusted['permissions'] == list(permission.TRUSTED_RULES)
    print('PASS: deny and trusted rules merged into inert config content', flush=True)


def main():
    trusted_cases()
    merge_cases()
    print('PASS: chatgpt_permission_proof_cases complete', flush=True)


if __name__ == '__main__':
    main()