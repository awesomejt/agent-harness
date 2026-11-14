#!/usr/bin/env python3
"""Offline method/endpoint/helper expectation and redaction checks; no OpenCode or network."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
import chatgpt_method_endpoint_helper as helper


def rejects(action):
    try:
        action()
    except (RuntimeError, ValueError, TypeError, AttributeError, AssertionError):
        return
    raise AssertionError('unsafe input was accepted')


def expectations_cases():
    source = Path('/tmp/ah-opencode-source-review')
    if source.is_dir():
        from chatgpt_installed_observer import verify_source
        packages, _ = verify_source(source)
        expected = helper.pinned_expectations(packages)
        assert expected['method_id'] == 'chatgpt-token-sharing'
        print('PASS: pinned checkout constants decoded', flush=True)
    snippet = '''
    const resource = "https://api.openai.com/v1"
    const providerID = Provider.ID.openai
    const methodID = Integration.MethodID.make("chatgpt-token-sharing")
    const fallbackModels = new Set(["gpt-6.1-sol"])
    '''
    parsed = helper.expectations_from_source(snippet)
    assert parsed['resource'] == 'https://api.openai.com/v1'
    print('PASS: expectations_from_source parses fixture snippet', flush=True)


def redact_cases():
    info = {'id': 'openai', 'package': helper.PACKAGE_ID, 'activation': 'auto',
            'settings': {'baseURL': 'https://api.openai.com/v1', 'encoding': 'zstd', 'secret': 'nope'}}
    redacted = helper.redact_provider(info, 'https://api.openai.com/v1')
    assert redacted['settings'] == {'baseURL': 'https://api.openai.com/v1', 'encoding': 'zstd'}
    rejects(lambda: helper.redact_provider({'id': 'openai', 'package': helper.PACKAGE_ID, 'settings': {}},
                                           'https://api.openai.com/v1'))
    rejects(lambda: helper.redact_provider(
        {'id': 'openai', 'package': 'opencode.provider.openai',
         'settings': {'baseURL': 'https://api.openai.com/v1'}}, 'https://api.openai.com/v1'))
    print('PASS: provider redaction requires baseURL and ChatGPT package', flush=True)


def method_proof_cases():
    expected = {'method_id': 'chatgpt-token-sharing', 'provider_id': 'openai', 'helper_model': 'gpt-6.1-sol',
                'resource': 'https://api.openai.com/v1', 'package_id': helper.PACKAGE_ID}
    integration = {'id': 'openai', 'methods': [{'type': 'oauth', 'id': 'chatgpt-token-sharing'}],
                   'connections': [{'type': 'credential', 'method': 'oauth'}]}
    helper.openai_method_proof(integration, expected)
    rejects(lambda: helper.openai_method_proof(
        {'id': 'openai', 'methods': [{'type': 'oauth', 'id': 'other'}],
         'connections': [{'type': 'credential', 'method': 'oauth'}]}, expected))
    model = {'providerID': 'openai', 'modelID': 'gpt-6.1-sol'}
    helper.model_default_proof(model, expected)
    rejects(lambda: helper.model_default_proof({'providerID': 'openai', 'modelID': 'other'}, expected))
    print('PASS: method and default-model proof helpers refuse mismatches', flush=True)


def helper_config_cases():
    import json
    env = {'OPENCODE_CONFIG_CONTENT': json.dumps({'update': 'disable', 'share': 'disabled'})}
    merged = helper.merge_helper_config(env, {'provider_id': 'openai', 'helper_model': 'gpt-6.1-sol'})
    document = json.loads(merged['OPENCODE_CONFIG_CONTENT'])
    model = {'providerID': 'openai', 'model': 'gpt-6.1-sol'}
    assert document['model'] == model and document['agents']['title']['model'] == model
    print('PASS: helper model merged into inert config content', flush=True)


def main():
    expectations_cases()
    redact_cases()
    method_proof_cases()
    helper_config_cases()
    print('PASS: chatgpt_method_endpoint_helper_cases complete', flush=True)


if __name__ == '__main__':
    main()