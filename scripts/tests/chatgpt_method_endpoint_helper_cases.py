#!/usr/bin/env python3
"""Offline method/endpoint/helper expectation and redaction checks; no OpenCode or network."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_method_endpoint_helper as helper


def expectations_cases():
    source = Path('/tmp/ah-opencode-source-review')
    if not source.is_dir():
        print('SKIP: v2.2.5 checkout absent for pinned expectation case', flush=True)
        return
    from chatgpt_installed_observer import verify_source
    packages, _ = verify_source(source)
    expected = helper.pinned_expectations(packages)
    assert expected['method_id'] == 'chatgpt-token-sharing'
    assert expected['resource'] == 'https://api.openai.com/v1'
    assert expected['provider_id'] == 'openai'
    assert expected['helper_model'] == 'gpt-6.1-sol'
    print('PASS: pinned chatgpt.ts constants decoded', flush=True)


def redact_cases():
    info = {'id': 'openai', 'package': helper.PACKAGE_ID, 'activation': 'auto',
            'settings': {'baseURL': 'https://api.openai.com/v1', 'encoding': 'zstd', 'secret': 'nope'}}
    redacted = helper.redact_provider(info, 'https://api.openai.com/v1')
    assert redacted['settings'] == {'baseURL': 'https://api.openai.com/v1', 'encoding': 'zstd'}
    print('PASS: provider redaction keeps only safe settings fields', flush=True)


def helper_config_cases():
    env = {'OPENCODE_CONFIG_CONTENT': json.dumps({'update': 'disable', 'share': 'disabled'})}
    merged = helper.merge_helper_config(env, {'provider_id': 'openai', 'helper_model': 'gpt-6.1-sol'})
    document = json.loads(merged['OPENCODE_CONFIG_CONTENT'])
    model = {'providerID': 'openai', 'model': 'gpt-6.1-sol'}
    assert document['model'] == model and document['agents']['title']['model'] == model
    print('PASS: helper model merged into inert config content', flush=True)


def main():
    expectations_cases()
    redact_cases()
    helper_config_cases()
    print('PASS: chatgpt_method_endpoint_helper_cases complete', flush=True)


if __name__ == '__main__':
    main()