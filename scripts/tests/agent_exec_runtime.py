#!/usr/bin/env python3
"""P4.3 installed OpenCode 2.2.5 named-role preflight and ACP session; no model prompt forwarded.

Real OpenCode runs the version/sources/agents/catalog checks and ACP setup
through the native_runtime.py shim, which intercepts session/prompt. Passing
runs prove the generated named entry, effective rules on every agent and the
selected session mode, not live role behavior (P4.4). A direct probe also
records why the runtime entry is always primary: a `subagent` default is
silently replaced by `build`.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SHIM = ROOT / 'scripts/tests/native_runtime.py'


def session_mode(runtime, base, mode):
    """Direct ACP initialize + session/new; no prompt and no key use."""
    project = base / ('probe-' + mode)
    home = base / ('home-' + mode)
    project.mkdir()
    home.mkdir(mode=0o700)
    model = dict(providerID='ah-litellm', model='fixture')
    rules = [dict(action='*', resource='*', effect='deny'), dict(action='external_directory', resource='*', effect='deny')]
    config = dict(model=model, default_agent='reviewer', update='disable', share='disabled', permissions=rules,
                  agents=dict(reviewer=dict(description='d', mode=mode, model=model, permissions=rules, system='s')),
                  mcp={}, plugins=[], providers={'ah-litellm': dict(package='aisdk:@ai-sdk/openai-compatible',
                  settings=dict(apiKey='unused', baseURL='http://127.0.0.1:9/v1'), models=dict(fixture=dict(name='fixture')))})
    env = dict(PATH=os.environ['PATH'], HOME=str(home), OPENCODE_CONFIG_CONTENT=json.dumps(config),
               OPENCODE_DISABLE_PROJECT_CONFIG='true', OPENCODE_DISABLE_MODELS_FETCH='true', OPENCODE_DISABLE_AUTOUPDATE='true',
               **{f'XDG_{k}_HOME': str(home / k) for k in ['CONFIG', 'DATA', 'CACHE', 'STATE']})
    p = subprocess.Popen([runtime, 'acp'], cwd=project, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True)
    try:
        def call(identifier, method, params):
            p.stdin.write(json.dumps(dict(jsonrpc='2.0', id=identifier, method=method, params=params)) + '\n')
            p.stdin.flush()
            for line in p.stdout:
                message = json.loads(line)
                if message.get('id') == identifier:
                    return message['result']
            raise AssertionError('ACP closed')
        call(1, 'initialize', dict(protocolVersion=1, clientCapabilities={}))
        session = call(2, 'session/new', dict(cwd=str(project), mcpServers=[]))
        [option] = [o for o in session['configOptions'] if o['id'] == 'mode']
        return option['currentValue']
    finally:
        p.kill()
        p.wait()


def main():
    runtime = shutil.which('opencode')
    assert runtime, 'OpenCode 2.2.5 required'
    runtime = str(Path(runtime).resolve())
    with tempfile.TemporaryDirectory(prefix='ah-agent-exec-runtime-') as d:
        base = Path(d).resolve()
        assert session_mode(runtime, base, 'primary') == 'reviewer'
        assert session_mode(runtime, base, 'subagent') == 'build'
        bin_dir = base / 'bin'
        bin_dir.mkdir()
        script = bin_dir / 'opencode'
        script.write_text('#!' + sys.executable + '\nimport os\nos.execv(' + repr(sys.executable) + ', ' +
                          repr([sys.executable, str(SHIM), '--shim', runtime]) + ' + __import__("sys").argv[1:])\n')
        script.chmod(0o755)
        env = {**os.environ, 'PATH': str(bin_dir) + ':' + os.environ['PATH'], 'LOCAL_KEY': 'unused-local-test-key',
               'NATIVE_KEY': 'unused-native-test-key', 'OPENCODE_CONFIG_CONTENT': 'poison', 'OPENCODE_API_KEY': 'poison'}
        runs = 0
        for mode in ['local-only', 'local-first']:
            project = base / mode
            (project / 'agents').mkdir(parents=True)
            for name in ['coder', 'reviewer']:
                shutil.copy(ROOT / 'agents' / (name + '.md'), project / 'agents')
            endpoint = 'http://127.0.0.1:9/v1'
            if mode == 'local-first':
                with socket.socket() as closed:
                    closed.bind(('127.0.0.1', 0))
                    endpoint = f'http://127.0.0.1:{closed.getsockname()[1]}/v1'
            (project / 'ah.json').write_text(json.dumps(dict(version=1, mode=mode, model='fixture',
                litellm=dict(api_base=endpoint, api_key_env='LOCAL_KEY'),
                native=dict(target='opencode', model='gpt-5.4', api_key_env='NATIVE_KEY'))))
            cases = [('reviewer', True), ('reviewer', False), ('coder', True)] if mode == 'local-only' else [('reviewer', True)]
            for agent, trusted in cases:
                args = [str(ROOT / 'target/debug/ah'), 'single', 'Never forwarded to provider', '--project', str(project),
                        '--timeout-secs', '30', '--agent', agent]
                if trusted:
                    args += ['--permissions', 'trusted']
                p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=60)
                assert p.returncode == 0, (mode, agent, trusted, p.returncode, p.stderr)
                assert (project / 'intercepted-native-prompt').exists(), p.stderr
                (project / 'intercepted-native-prompt').unlink()
                assert 'unused-' not in p.stdout + p.stderr
                assert f'; agent {agent} (' in p.stderr, p.stderr
                if mode == 'local-first':
                    assert 'attempt=2 local-first fallback via OpenCode 2.2.5; model opencode/gpt-5.4' in p.stderr, p.stderr
                    assert not (project / '.opencode').exists()
                else:
                    assert (project / '.opencode/agents' / (agent + '.md')).exists()
                runs += 1
    print(f'PASS installed OpenCode 2.2.5 named roles: {runs} preflight+session runs (local reviewer trusted/deny, coder, '
          'local-first native fallback); session mode is the role; subagent default falls back to build; 0 prompts forwarded')


if __name__ == '__main__':
    main()
