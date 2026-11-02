#!/usr/bin/env python3
"""P2.7 public CLI fixtures. No subprocess runtime or model traffic permitted."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

BINARY = Path(__file__).resolve().parents[2] / 'target/debug/ah'


def snapshot(base):
    return {str(p.relative_to(base)): p.read_bytes()
            for p in base.rglob('*') if p.is_file()}


with tempfile.TemporaryDirectory(prefix='ah-preview-') as directory:
    base = Path(directory).resolve()
    project = base / 'project\ncontrol'
    project.mkdir()
    home = base / 'home'
    home.mkdir()
    (home / 'global-config').write_text('UNMANAGED_SECRET')
    runtime = base / 'opencode'
    runtime.write_text('#!/bin/sh\ntouch "' + str(base / 'LAUNCHED') + '"\nexit 99\n')
    runtime.chmod(0o755)
    config = dict(version=1, mode='local-only', model='fixture',
                  litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='TEST_KEY'))
    config_path = project / 'ah.json'
    config_path.write_text(json.dumps(config))
    prompt = 'PROMPT_SENTINEL'
    (project / 'prompt.txt').write_text(prompt)
    (project / 'opencode.json').write_text('{"custom":"UNMANAGED_SECRET"}')
    env = {**os.environ, 'PATH': str(base), 'HOME': str(home), 'TEST_KEY': 'SECRET_SENTINEL'}

    def run(extra=(), expected=0, key=True, path=None, stdin=None):
        before = snapshot(base)
        args = [str(BINARY), 'single', '--project', str(project), '--preview', *extra]
        if '--prompt-file' not in extra:
            args.append(prompt)
        child_env = dict(env)
        if not key:
            child_env.pop('TEST_KEY')
        if path is not None:
            child_env['PATH'] = path
        result = subprocess.run(args, env=child_env, input=stdin, capture_output=True,
                                text=True, timeout=5)
        assert result.returncode == expected, (args, result.stdout, result.stderr)
        assert snapshot(base) == before, 'preview mutated files or launched runtime'
        output = result.stdout + result.stderr
        for secret in [prompt, 'SECRET_SENTINEL', 'UNMANAGED_SECRET', '127.0.0.1']:
            assert secret not in output, (secret, output)
        assert 'project\ncontrol' not in output, 'path control character was not escaped'
        return result.stdout, result.stderr

    out, _ = run()
    assert 'discovered' in out and 'version unverified' in out
    assert 'opencode.json: provider.ah-litellm' in out
    assert '.ah-opencode-owner.json: managed routing receipt' in out
    assert 'health checks: none' in out
    assert 'deny: no file/shell grants (default)' in out
    out, _ = run(['--permissions', 'trusted', '--model', 'override', '--timeout-secs', '9'])
    assert 'override (invocation)' in out and '9 seconds (invocation)' in out
    assert 'host privileges' in out
    out, _ = run(path='')
    assert 'missing; install OpenCode 1.18.30' in out
    out, _ = run(path='.')
    assert 'missing; install OpenCode 1.18.30' in out
    run(['--prompt-file', str(project / 'prompt.txt')])
    run(['--prompt-file', '-'], stdin=prompt)
    _, err = run(key=False, expected=2)
    assert 'set the environment variable named by litellm.api_key_env' in err
    run(['--no-sync'], expected=2)
    # Exact no-sync config needs no receipt; it still must use the same planner.
    desired = {'provider': {'ah-litellm': {'npm': '@ai-sdk/openai-compatible',
                'options': {'baseURL': config['litellm']['api_base'],
                'apiKey': '{env:TEST_KEY}'}, 'models': {'fixture': {'name': 'fixture'}}}},
               'enabled_providers': ['ah-litellm'], 'model': 'ah-litellm/fixture',
               'small_model': 'ah-litellm/fixture'}
    (project / 'opencode.json').write_text(json.dumps(desired))
    out, err = run(['--no-sync'])
    assert 'exact disk route validated' in out and 'planned changes: none' in out
    desired['model'] = 'ah-litellm/other'
    (project / 'opencode.json').write_text(json.dumps(desired))
    run(['--no-sync'], expected=2)
    config['model'] = 'bad/model'
    config_path.write_text(json.dumps(config))
    run(expected=2)

print('preview fixtures passed: no launch/writes, redaction, sources, missing prerequisites, no-sync')
