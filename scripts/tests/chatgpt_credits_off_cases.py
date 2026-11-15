#!/usr/bin/env python3
"""Offline ChatGPT credits-off attestation and usage-source inventory checks; no OpenCode or network."""
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_credits_off as credits


def rejects(action):
    try:
        action()
    except (RuntimeError, ValueError, TypeError, AttributeError, AssertionError):
        return
    raise AssertionError('unsafe input was accepted')


def attestation_cases():
    good = {
        'workspace_label': 'personal',
        'asserted_at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
        'post_limit_app_credits_off': True,
        'setting_name': credits.POST_LIMIT_SETTING,
    }
    credits.validate_attestation(good)
    rejects(lambda: credits.validate_attestation({**good, 'post_limit_app_credits_off': False}))
    rejects(lambda: credits.validate_attestation({**good, 'setting_name': 'other'}))
    rejects(lambda: credits.validate_attestation({**good, 'workspace_label': ''}))
    rejects(lambda: credits.validate_attestation({**good, 'workspace_label': 'bad@host'}))
    rejects(lambda: credits.validate_attestation({**good, 'asserted_at': 'not-a-time'}))
    rejects(lambda: credits.validate_attestation({**good, 'extra': 'field'}))
    stale = {**good, 'asserted_at': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()}
    rejects(lambda: credits.validate_attestation(stale))
    future = {**good, 'asserted_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    rejects(lambda: credits.validate_attestation(future))
    print('PASS: attestation schema requires post-limit credits off and bounded label', flush=True)


def inventory_cases():
    snippet_limits = f'''
    export const layer = Layer.effect(
      Service,
      Effect.gen(function* () {{
        const connection = yield* integrations.connection.active(Integration.ID.make("opencode"))
      }}),
    )
    '''
    snippet_group = '''
    description:
      "Return the OpenCode Go allowance and Console budgets of the OpenCode Console workspace the location is signed in to, or null when it isn't signed in.",
    '''
    source = Path('/tmp/ah-opencode-source-review')
    if source.is_dir():
        from chatgpt_installed_observer import verify_source
        packages, _ = verify_source(source)
        credits.verify_usage_pins(packages)
        credits.inventory_from_source(packages)
        print('PASS: pinned checkout usage inventory verified', flush=True)
    with tempfile.TemporaryDirectory() as directory:
        pkg = Path(directory) / 'packages'
        for rel, text in (
            ('core/src/usage-limits.ts', snippet_limits),
            ('server/src/handlers/usage.ts', 'usage.limits UsageLimits.Service'),
            ('protocol/src/groups/usage.ts', snippet_group),
        ):
            path = pkg / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        inventory = credits.inventory_from_source(pkg)
        assert inventory['console_only_inventory'] is True
        assert inventory['post_limit_setting_name'] == credits.POST_LIMIT_SETTING

        def write_pkg(files):
            for rel, text in files.items():
                path = pkg / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

        base = {
            'core/src/usage-limits.ts': snippet_limits,
            'server/src/handlers/usage.ts': 'usage.limits UsageLimits.Service',
            'protocol/src/groups/usage.ts': snippet_group,
        }

        def inventory_with(**overrides):
            merged = {**base, **overrides}
            write_pkg(merged)
            credits.inventory_from_source(pkg)

        rejects(lambda: inventory_with(**{'protocol/src/groups/usage.ts': 'post-limit credits after'}))
        rejects(lambda: inventory_with(**{'protocol/src/groups/usage.ts': 'unrelated description'}))
        rejects(lambda: inventory_with(**{'core/src/usage-limits.ts': 'integrations.connection.active("other")'}))
    print('PASS: usage inventory refuses missing Console scope and post-limit wording', flush=True)


def main():
    attestation_cases()
    inventory_cases()
    print('PASS: chatgpt_credits_off_cases complete', flush=True)


if __name__ == '__main__':
    main()