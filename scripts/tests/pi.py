#!/usr/bin/env python3
"""P8.2 Pi runtime fixtures through the public CLI. No provider traffic."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_pi.py'
ENV_NAMES = {'HOME', 'PATH', 'USER', 'LOGNAME', 'TMPDIR', 'PI_CODING_AGENT_DIR'}
SHARED_ARGS = ['--offline', '--mode', 'rpc', '--no-session', '--no-extensions',
               '--no-mcp', '--no-skills', '--no-prompt-templates', '--no-themes', '--no-context-files',
               '--no-approve', '--provider', 'ah-litellm']
TRUSTED_TOOLS = 'bash,edit,find,grep,read,write'
REVIEWER_TOOLS = 'find,grep,read'
DENY_ARGS = SHARED_ARGS + ['--no-tools', '--model', 'fixture']
TRUSTED_ARGS = SHARED_ARGS + ['--tools', TRUSTED_TOOLS, '--model', 'fixture']
REVIEWER_ARGS = SHARED_ARGS + ['--tools', REVIEWER_TOOLS, '--model', 'fixture']
T = ['--permissions', 'trusted']


def cfg():
    return dict(version=1, mode='local-only', model='fixture',
                litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='LOCAL_KEY', runtime='pi'))


CASES = [
    ('success', 0, True, []),
    ('jsonl', 0, True, ['--output', 'jsonl']),
    ('version', 2, False, []),
    ('control-error', 2, False, []),
    ('state-tools', 2, False, []),
    ('mcp', 2, False, []),
    ('project-settings', 2, False, []),
    ('init-model', 2, False, []),
    ('eof-before-submit', 1, False, []),
    ('tool-use', 4, True, []),
    ('malformed', 4, True, []),
    ('error-result', 1, True, []),
    ('cancel-deadline', 3, True, ['--timeout-secs', '3']),
    ('cancel-stall', 3, True, ['--timeout-secs', '3']),
    ('models-key', 0, True, []),
    ('cloud-only-pi', 2, False, []),
    ('trusted-success', 0, True, T),
    ('trusted-bad-title', 4, True, T),
    ('trusted-bad-method', 4, True, T),
    ('trusted-unknown-tool', 4, True, T),
    ('trusted-malformed-ui', 4, True, T),
    ('trusted-duplicate-ui', 4, True, T),
    ('agent-reviewer', 0, True, ['--agent', 'reviewer'] + T),
    ('agent-coder-deny', 0, True, ['--agent', 'coder']),
    ('agent-effort-refuse', 2, False, ['--agent', 'coder'] + T),
    ('agents-md', 0, True, []),
    ('local-first', 2, False, ['--mode', 'local-first',
                                 '--config', 'cloud-native.json']),
    ('preview', 0, False, ['--preview']),
    ('missing-runtime', 2, False, []),
]

count = 0
for case, expected, prompted, extra in CASES:
    with tempfile.TemporaryDirectory(prefix='ah-pi-') as d:
        base = Path(d).resolve()
        bindir = base / 'bin'
        bindir.mkdir()
        if case != 'missing-runtime':
            (bindir / 'pi').write_text(
                f'#!/bin/sh\n/usr/bin/env > "$PWD/env.txt"\nexec /usr/bin/python3 {FAKE} "$@"\n')
            (bindir / 'pi').chmod(0o755)
        project = base / 'project'
        project.mkdir()
        if case == 'agents-md':
            (project / 'AGENTS.md').write_text('Project AGENTS sentinel\n')
        (project / 'case').write_text(case)
        if case == 'cloud-only-pi':
            ah = dict(version=1, mode='cloud-only', native=dict(target='opencode', model='gpt-5.4', api_key_env='K'),
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='LOCAL_KEY', runtime='pi'))
        elif case == 'local-first':
            ah = dict(version=1, mode='local-first', model='fixture',
                      litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='LOCAL_KEY', runtime='pi'),
                      native=dict(target='opencode', model='gpt-5.4', api_key_env='NATIVE_KEY'))
            (base / 'cloud-native.json').write_text(json.dumps(ah))
        else:
            ah = cfg()
        (project / 'ah.json').write_text(json.dumps(ah))
        if case.startswith('agent-'):
            (project / 'agents').mkdir(exist_ok=True)
            agent_flag = next((a for a in extra if not a.startswith('-')), 'reviewer')
            name = agent_flag if agent_flag in ('coder', 'reviewer') else 'reviewer'
            text = (ROOT / 'agents' / (name + '.md')).read_text()
            if case == 'agent-effort-refuse':
                text = text.replace('\ntools:', '\neffort: high\ntools:', 1)
            (project / 'agents' / (name + '.md')).write_text(text)
        env = {'PATH': f'{bindir}:/usr/bin:/bin', 'HOME': str(base), 'LOCAL_KEY': 'synthetic',
               'NATIVE_KEY': 'synthetic'}
        args = [str(BINARY), 'single', 'pi task', '--project', str(project)] + extra
        if '--timeout-secs' not in extra:
            args += ['--timeout-secs', '15']
        if case == 'local-first':
            args += ['--config', str(base / 'cloud-native.json')]
        p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=60)
        out = p.stdout + p.stderr
        assert p.returncode == expected, (case, p.returncode, p.stderr)
        assert (project / 'prompted').exists() == prompted, case
        launched = (project / 'argv.json').exists()
        refuse = {'agent-effort-refuse', 'local-first', 'preview', 'missing-runtime', 'cloud-only-pi'}
        if case == 'cloud-only-pi':
            assert 'litellm.runtime pi applies only to local-only' in p.stderr, p.stderr
        assert launched == (case not in refuse), case
        if launched:
            argv = json.loads((project / 'argv.json').read_text())
            if case == 'agent-reviewer':
                base = REVIEWER_ARGS
            elif case.startswith('trusted'):
                base = TRUSTED_ARGS
            else:
                base = DENY_ARGS
            assert argv[:len(base)] == base, (case, argv)
            assert argv.count('--provider') == 1 and 'ah-litellm' in argv, argv
            model_i = argv.index('--model')
            assert argv[model_i + 1] == 'fixture', argv
            ext_i = argv.index('-e')
            assert ext_i >= 0 and argv[ext_i + 1].endswith('ah-policy.mjs'), argv
            names = {l.split('=', 1)[0] for l in (project / 'env.txt').read_text().splitlines() if '=' in l}
            want = {'HOME', 'PATH', 'PI_CODING_AGENT_DIR', 'LOCAL_KEY'}
            if case.startswith('trusted') or case == 'agent-reviewer':
                want.add('AH_PI_GRANTABLE')
            assert want <= names, (case, names)
            assert 'PI_CODING_AGENT_DIR' in names, case
            lines = [json.loads(l) for l in (project / 'stdin.jsonl').read_text().splitlines()]
            types = [l['type'] for l in lines]
            if prompted:
                assert types[:3] == ['set_auto_compaction', 'set_auto_retry', 'get_state'], (case, types)
                assert types.index('prompt') == 3, (case, types)
        if case == 'models-key':
            assert (project / 'models_key.txt').read_text() == '${LOCAL_KEY}', case
        if case == 'success':
            assert p.stdout == 'fake response\nfinal line', (case, p.stdout)
        if case == 'jsonl':
            records = [json.loads(l) for l in p.stdout.splitlines()]
            result = records[-1]
            attempt = result['attempts'][0]
            assert attempt['runtime'] == 'pi' and attempt['runtime_version'] == '1.5.0', attempt
            assert attempt['model'] == 'pi/fixture', attempt
            assert attempt['backend_stop'] == 'agent_settled', attempt
        if case == 'preview':
            assert 'Pi RPC' in p.stdout and 'litellm.runtime pi' not in p.stdout, p.stdout
            assert 'route: LiteLLM only (Pi runtime)' in p.stdout, p.stdout
        if case == 'agent-reviewer':
            prompted = (project / 'prompted').read_text()
            assert 'Do not edit files' in prompted, prompted
            assert 'pi task' in prompted, prompted
            grant_line = next(l for l in (project / 'env.txt').read_text().splitlines()
                                if l.startswith('AH_PI_GRANTABLE='))
            assert grant_line == 'AH_PI_GRANTABLE=read,search', grant_line
        if case == 'agents-md':
            text = (project / 'prompted').read_text()
            assert text.startswith('Project AGENTS sentinel'), text
            assert text.endswith('pi task'), text
        if case == 'agent-coder-deny':
            assert '--no-tools' in json.dumps(json.loads((project / 'argv.json').read_text())), case
            assert 'Read project instructions' in (project / 'prompted').read_text(), case
        if case == 'agent-effort-refuse':
            assert 'agent effort is unsupported on the Pi runtime' in p.stderr, p.stderr
        if case == 'trusted-success':
            ui = json.loads((project / 'ui_response.json').read_text())
            assert ui.get('confirmed') is True, ui
            assert p.stdout == 'fake response\nfinal line', (case, p.stdout)
            env_text = (project / 'env.txt').read_text()
            grant_line = next(l for l in env_text.splitlines() if l.startswith('AH_PI_GRANTABLE='))
            assert grant_line == 'AH_PI_GRANTABLE=read,search,edit,execute', grant_line
        count += 1

print(f'PASS: {count} Pi runtime launch cases (deny + trusted + agents)')
