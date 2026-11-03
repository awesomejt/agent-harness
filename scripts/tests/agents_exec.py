#!/usr/bin/env python3
"""P4.3 named-role execution against fake OpenCode 2.2.5; no model traffic. Build target/debug/ah first.

Checks the generated runtime document (default agent, effective global/agent
rules, primary entry, exact system text), harness-side grants and completion
checks per role, preflight/session refusal of a widened or substituted role,
effort refusal before launch, and the local-first fallback carrying the role.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'


def rule(action, effect):
    return dict(action=action, resource='*', effect=effect)


DENY = [rule('*', 'deny'), rule('external_directory', 'deny')]
READ_ONLY = [rule('*', 'deny'), rule('read', 'ask'), rule('glob', 'ask'), rule('grep', 'ask'),
             rule('external_directory', 'deny')]
TRUSTED = [rule('*', 'deny')] + [rule(a, 'ask') for a in ['read', 'glob', 'grep', 'edit', 'shell']] + \
          [rule('external_directory', 'ask')]


def run(case, agent='reviewer', trusted=True, effort=None, mode='local-only'):
    with tempfile.TemporaryDirectory(prefix='ah-agent-exec-') as d:
        base = Path(d).resolve()
        (base / 'opencode').symlink_to(FAKE)
        (base / 'case').write_text(case)
        (base / 'track-config').touch()
        (base / 'agents').mkdir()
        for name in ['coder', 'reviewer']:
            text = (ROOT / 'agents' / (name + '.md')).read_text()
            if effort and name == agent:
                text = text.replace('\ntools:', '\neffort: ' + effort + '\ntools:', 1)
            (base / 'agents' / (name + '.md')).write_text(text)
        endpoint = 'http://127.0.0.1:9/v1'
        if mode == 'local-first':
            with socket.socket() as closed:
                closed.bind(('127.0.0.1', 0))
                endpoint = f'http://127.0.0.1:{closed.getsockname()[1]}/v1'
        config = dict(version=1, mode=mode, model='fixture',
                      litellm=dict(api_base=endpoint, api_key_env='TEST_KEY'))
        if mode == 'local-first':
            config['native'] = dict(target='opencode', model='fixture', api_key_env='TEST_KEY')
        (base / 'ah.json').write_text(json.dumps(config))
        args = [str(BINARY), 'single', 'Task', '--project', str(base), '--timeout-secs', '15', '--agent', agent]
        if trusted:
            args += ['--permissions', 'trusted']
        env = {**os.environ, 'PATH': str(base) + ':' + os.environ['PATH'], 'TEST_KEY': 'SECRET_SENTINEL',
               'OPENCODE_CONFIG_CONTENT': 'poison'}
        p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
        assert 'SECRET_SENTINEL' not in p.stdout + p.stderr, case
        records = [json.loads(line) for line in (base / 'runtime-config.jsonl').read_text().splitlines()] \
            if (base / 'runtime-config.jsonl').exists() else []
        result = base / 'permission-result.json'
        selected = json.loads(result.read_text())['result']['outcome'].get('optionId') if result.exists() else None
        return dict(code=p.returncode, stderr=p.stderr, configs=[r['config'] for r in records],
                    launched=(base / 'launched').exists(), prompted=(base / 'prompted').exists(),
                    selected=selected, emitted=(base / '.opencode/agents' / (agent + '.md')).exists(),
                    routes=(base / 'launch-routes').read_text().split() if (base / 'launch-routes').exists() else [])


def expect(case, code, **kwargs):
    r = run(case, **kwargs)
    assert r['code'] == code, (case, kwargs, r['code'], r['stderr'])
    return r


# Runtime document: the role is the primary default agent; global and agent rules are equal.
body = (ROOT / 'agents/reviewer.md').read_text().split('\n---\n', 1)[1]
r = expect('read', 0)
config = r['configs'][-1]
assert config['default_agent'] == 'reviewer'
assert config['permissions'] == READ_ONLY
named = config['agents']['reviewer']
assert named == dict(description=named['description'], mode='primary', permissions=READ_ONLY, system=body,
                     model=dict(providerID='ah-litellm', model='fixture')), named
assert r['selected'] == 'once' and r['emitted']
assert 'agent reviewer (specialized role; tools [Read, Search]; enforced kinds ["read", "search"])' in r['stderr']
assert expect('search', 0)['selected'] == 'once'

# Read-only role refuses edit/execute grants even under trusted invocation.
for case in ['edit', 'execute']:
    assert expect(case, 3)['selected'] == 'reject', case
# Completed calls must belong to the role's kinds; unknown kinds fail closed.
expect('named-completed-read', 0)
expect('named-completed-edit', 4)
expect('named-completed-unknown', 4)

# A trusted coder receives the full trusted profile; deny invocation narrows any role.
r = expect('edit', 0, agent='coder')
assert r['configs'][-1]['permissions'] == TRUSTED and r['selected'] == 'once'
r = expect('edit', 3, agent='coder', trusted=False)
assert r['configs'][-1]['permissions'] == DENY and r['configs'][-1]['agents']['coder']['permissions'] == DENY
assert r['selected'] == 'reject'
expect('named-completed-read', 4, agent='coder', trusted=False)

# Preflight refuses a widened, hidden or altered role before launch.
for case in ['named-widened', 'named-hidden', 'named-system', 'subagent-widened']:
    r = expect(case, 2)
    assert not r['launched'] and not r['prompted'], case
# A session that silently substitutes `build` stops before the prompt.
r = expect('named-mode-fallback', 1)
assert r['launched'] and not r['prompted']

# Unsupported effort refuses before any runtime, check or project write.
for effort in ['low', 'medium', 'high', 'max']:
    r = expect('read', 2, effort=effort)
    assert not r['configs'] and not r['launched'] and not r['emitted'], effort
    assert 'agent effort is unsupported by OpenCode 2.2.5' in r['stderr']
assert expect('read', 0, effort='default')['selected'] == 'once'

# Local-first fallback carries the same role and effective rules natively.
r = expect('read', 0, mode='local-first')
assert r['routes'] == ['native'] and not r['emitted']
native = r['configs'][-1]
assert native['model']['providerID'] == 'opencode' and native['default_agent'] == 'reviewer'
assert native['permissions'] == READ_ONLY and native['agents']['reviewer']['permissions'] == READ_ONLY
assert native['agents']['reviewer']['model'] == dict(providerID='opencode', model='fixture')

print('PASS P4.3 named roles: runtime document, per-role grants/completions, deny narrowing, '
      'preflight/session refusal, effort refusal and local-first fallback; 0 model prompts')
