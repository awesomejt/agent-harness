#!/usr/bin/env python3
"""Opt-in pinned macOS ChatGPT post-limit credits-off assertion on a retained login root (P7.9).

Requires operator attestation JSON and a root that already passes ``chatgpt_login_preflight.py``.
Network stays fully denied. Reads ``experimental.usage.limits`` only; no session, model turn or
credential export.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from antigravity_feasibility import check
from chatgpt_contained import owned_server
from chatgpt_feasibility import SHA256
from chatgpt_installed_observer import BODY_LIMIT, REQUEST_TIMEOUT, static_guards, verify_source
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

POST_LIMIT_SETTING = 'Allow other apps to use credits after reaching your usage limit'
USAGE_LIMITS_ROUTE = '/api/experimental/usage/limits'
LABEL_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$')
SOURCE_FINGERPRINTS = {
    'core/src/usage-limits.ts': '6891419fe21a037f5ed42fd282533db1692cb8797b01b6398c1dd758e6280145',
    'server/src/handlers/usage.ts': 'd82a1d7495e58d236c47a2b747df11b0b6dec5ffe0d3d20ac8d2c1b5df9762b6',
    'protocol/src/groups/usage.ts': '14bc0fe11fdd5fef9fa4a5a68b56da5a0717b0ef679e184817d9660b4b433e2d',
}
CONSOLE_ACTIVE = 'integrations.connection.active(Integration.ID.make("opencode")'
MAX_ATTESTATION_AGE = timedelta(hours=1)


class CreditsOffObserver(PreflightObserver):
    """Preflight observer plus ``experimental.usage.limits`` (expects null on ChatGPT-only login)."""

    allowed = dict(PreflightObserver.allowed, **{USAGE_LIMITS_ROUTE: 'object'})

    def get(self, path):
        if path != USAGE_LIMITS_ROUTE:
            return super().get(path)
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
        check(isinstance(value, dict) and set(value) == {'location', 'data'})
        check(value['location'] == {'directory': str(self.location)})
        return value['data']


def verify_usage_pins(packages):
    recorded = {}
    for name, expected in SOURCE_FINGERPRINTS.items():
        digest = hashlib.sha256((packages / name).read_bytes()).hexdigest()
        check(digest == expected)
        recorded[name] = digest
    return recorded


def inventory_from_source(packages):
    """Record that pinned usage APIs cover Console/Go only, not ChatGPT post-limit credits."""
    limits = (packages / 'core/src/usage-limits.ts').read_text()
    check(CONSOLE_ACTIVE in limits)
    handler = (packages / 'server/src/handlers/usage.ts').read_text()
    check('usage.limits' in handler and 'UsageLimits.Service' in handler)
    group = (packages / 'protocol/src/groups/usage.ts').read_text()
    check('OpenCode Go allowance and Console budgets' in group)
    check('post-limit' not in group.lower() and 'credits after' not in group.lower())
    return {
        'usage_limits_route': USAGE_LIMITS_ROUTE,
        'console_only_inventory': True,
        'post_limit_setting_name': POST_LIMIT_SETTING,
    }


def validate_attestation(record):
    check(isinstance(record, dict))
    required = frozenset(('workspace_label', 'asserted_at', 'post_limit_app_credits_off', 'setting_name'))
    check(required <= set(record) <= required)
    label = record['workspace_label']
    check(isinstance(label, str) and LABEL_PATTERN.fullmatch(label))
    asserted = record['asserted_at']
    check(isinstance(asserted, str))
    parsed = datetime.fromisoformat(asserted.replace('Z', '+00:00'))
    check(parsed.tzinfo is not None)
    now = datetime.now(timezone.utc)
    stamp = parsed.astimezone(timezone.utc)
    check(timedelta(0) <= now - stamp <= MAX_ATTESTATION_AGE)
    check(record['post_limit_app_credits_off'] is True)
    check(record['setting_name'] == POST_LIMIT_SETTING)


def load_attestation(path):
    text = path.read_text()
    check(len(text) <= 4096)
    return json.loads(text)


def print_checklist():
    template = {
        'workspace_label': '<short label, e.g. personal>',
        'asserted_at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
        'post_limit_app_credits_off': True,
        'setting_name': POST_LIMIT_SETTING,
    }
    print('Operator checklist (D067): verify ChatGPT Settings → Usage before each live gate.')
    print(f'1. Confirm "{POST_LIMIT_SETTING}" is OFF for the workspace you will authorize.')
    print('2. Record only workspace label and timestamp; never tokens or account screenshots.')
    print('3. Write attestation JSON and pass --attestation to this helper:')
    print(json.dumps(template, indent=2, sort_keys=True))


def credits_off_boot(ctx, helper, attestation):
    runtime, work, home, project, env, token, builtin = (ctx[k] for k in (
        'runtime', 'work', 'home', 'project', 'env', 'token', 'builtin'))
    check(not root_shape(work, token, env))
    owned = (work,)
    env = merge_helper_config(env, helper)
    password = secrets.token_urlsafe(32)
    env = dict(env, OPENCODE_PASSWORD=password)
    port = fresh_port()
    policy = combined_profile(work, port, ancestor_denials(home))
    check(database_path(runtime, project, env, policy, work))
    summary = {}
    with owned_server(runtime, project, env, policy, port):
        observer = CreditsOffObserver(port, password, project)
        check(observer.locations() == [])
        resources, integrations, identities = settle_view(observer, owned, resources_ready(builtin))
        check(observer.locations() == [str(project)])
        check(integration_digest(integrations) == PUBLISHED_INTEGRATION_DIGEST)
        check(len(integrations) == PUBLISHED_INTEGRATION_COUNT)
        login_refusals = evaluate((resources, integrations, identities, set()), frozenset(integrations), builtin)[1]
        if login_refusals:
            raise LoginPreflightRefusal(
                f'login preflight failed: {login_refusals!r}; complete operator login first')
        limits = observer.get(USAGE_LIMITS_ROUTE)
        check(limits is None)
        summary = {
            'usage_limits_null': True,
            'attestation': {
                'workspace_label': attestation['workspace_label'],
                'asserted_at': attestation['asserted_at'],
                'post_limit_app_credits_off': attestation['post_limit_app_credits_off'],
                'setting_name': attestation['setting_name'],
            },
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--print-checklist', action='store_true',
                        help='print operator attestation steps and exit')
    parser.add_argument('--opencode', default='opencode', help='installed executable on PATH')
    parser.add_argument('--source', type=Path, help='official v2.2.5 checkout (D071 procedure)')
    parser.add_argument('--root', type=Path, help='owned root after operator login')
    parser.add_argument('--attestation', type=Path, help='operator JSON attestation file')
    args = parser.parse_args()
    if args.print_checklist:
        print_checklist()
        return
    check(args.source is not None and args.root is not None and args.attestation is not None)
    attestation = load_attestation(args.attestation.resolve())
    validate_attestation(attestation)
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    installed = shutil.which(args.opencode)
    check(installed is not None)
    packages, _ = verify_source(args.source.resolve())
    pins = verify_usage_pins(packages)
    inventory = inventory_from_source(packages)
    expected = pinned_expectations(packages)
    from chatgpt_installed_observer import expected_plugins
    builtin, _, _ = expected_plugins(packages)
    helper = {key: expected[key] for key in ('provider_id', 'helper_model')}
    with tempfile.TemporaryDirectory(prefix='ah-credits-off-bin-') as directory:
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
            proof = credits_off_boot(ctx, helper, attestation)
        finally:
            os.close(held)
        check(lock_probe(ctx['work']) == 'acquired')
    print('PASS: operator attestation recorded and usage.limits is null on ChatGPT-only login', flush=True)
    print(json.dumps({
        'origin_boundary': boundary,
        'source_pins': pins,
        'source_inventory': inventory,
        'proof': proof,
    }, indent=1, sort_keys=True))
    print('LIMIT: point-in-time operator attestation; no programmatic post-limit credits read; D034 remains open')


if __name__ == '__main__':
    try:
        main()
    except LoginPreflightRefusal as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        print('Credits-off assertion failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)