#!/usr/bin/env python3
"""P7.2 Claude runtime fixtures through the public CLI. No provider traffic.

A fake `claude` on a disposable PATH records argv, environment names and stdin.
Cases cover the pre-submission control preflight, the submission boundary,
system/init checks, deny-profile tool refusal, trusted host-prompt grants
(exact, once, never after an interrupt) and trusted protocol violations,
named roles (intersected tools, appended body, effort, ceiling-denied prompts),
terminal mapping, interrupt cancellation, machine output, preview, and refusals
that must not launch.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_claude.py'
ENV_NAMES = {'HOME', 'PATH', 'USER', 'LOGNAME', 'TMPDIR', 'DISABLE_AUTOUPDATER',
             'CLAUDE_CODE_DISABLE_BACKGROUND_TASKS'}
EXPECTED_ARGS = ['-p', '--output-format=stream-json', '--input-format=stream-json', '--verbose',
                 '--safe-mode', '--setting-sources=', '--strict-mcp-config',
                 '--disable-slash-commands', '--no-session-persistence',
                 '--permission-prompts=none', '--tools=', '--model=sonnet']
TRUSTED_ARGS = EXPECTED_ARGS[:9] + ['--permission-prompts=host', '--permission-prompt-tool=stdio',
                                    '--tools=Bash,Edit,Glob,Grep,Read,Write', '--model=sonnet']
T = ['--permissions', 'trusted']
HOST = ['--permission-prompts=host', '--permission-prompt-tool=stdio']
EFFORTFUL = ('---\nversion: 1\nname: effortful\ndescription: d\ncapacity: both\n'
             'permissions: trusted\ntools: [edit, read]\neffort: high\n---\nThink hard.\n')
EMPTY = ('---\nversion: 1\nname: empty\ndescription: d\ncapacity: primary\n'
         'permissions: trusted\ntools: []\n---\nNo tools.\n')
BIG = EMPTY.replace('name: empty', 'name: big').replace('No tools.', 'x' * (128 * 1024 + 1))
# Agent file text per case, and the arguments the launch must end with.
AGENT_FILES = {'reviewer': (ROOT / 'agents/reviewer.md').read_text(),
               'coder': (ROOT / 'agents/coder.md').read_text(),
               'effortful': EFFORTFUL, 'empty': EMPTY, 'big': BIG}


def body(text):
    return text.split('\n---\n', 1)[1]


def append(name):
    return [f'--append-system-prompt={body(AGENT_FILES[name])}']


AGENT_CASES = {
    'agent-deny': ('reviewer', EXPECTED_ARGS + append('reviewer')),
    'agent-reviewer': ('reviewer', EXPECTED_ARGS[:9] + HOST + ['--tools=Glob,Grep,Read', '--model=sonnet']
                       + append('reviewer')),
    'agent-reviewer-write': ('reviewer', EXPECTED_ARGS[:9] + HOST + ['--tools=Glob,Grep,Read', '--model=sonnet']
                             + append('reviewer')),
    'agent-coder': ('coder', TRUSTED_ARGS + append('coder')),
    'agent-effort': ('effortful', EXPECTED_ARGS[:9] + HOST + ['--tools=Edit,Read,Write', '--model=sonnet',
                                                             '--effort=high'] + append('effortful')),
    'agent-effort-mismatch': ('effortful', EXPECTED_ARGS[:9] + HOST + ['--tools=Edit,Read,Write',
                                                                      '--model=sonnet', '--effort=high']
                              + append('effortful')),
    'agent-empty': ('empty', EXPECTED_ARGS + append('empty')),
    'agent-big': ('big', None),
    'agent-empty-preview': ('empty', None),
    'agent-preview': ('effortful', None),
}
SECRETS = ['SECRET_ACCOUNT_SENTINEL', 'SECRET_REASONING_SENTINEL', 'SECRET_PROVIDER_ERROR', 'poison']

# (case, exit, prompted, extra args)
CASES = [
    ('success', 0, True, []),
    ('agents-md', 0, True, []),
    ('jsonl', 0, True, ['--output', 'jsonl']),
    ('version', 2, False, []),
    ('permission-mode', 2, False, []),
    ('commands', 2, False, []),
    ('control-error', 2, False, []),
    ('managed-settings', 2, False, []),
    ('mcp', 2, False, []),
    ('context-tools', 2, False, []),
    ('memory', 2, False, []),
    ('early-record', 1, False, []),
    ('eof-before-submit', 1, False, []),
    ('init-tools', 4, True, []),
    ('init-model', 4, True, []),
    ('init-key', 4, True, []),
    ('before-init', 4, True, []),
    ('tool-use', 4, True, []),
    ('host-request', 4, True, []),
    ('malformed', 4, True, []),
    ('eof-after-submit', 4, True, []),
    ('error-result', 1, True, []),
    # 3 s leaves the four control round-trips and the prompt well inside the
    # deadline on a loaded runner; the fake stalls only after system/init.
    ('cancel-deadline', 3, True, ['--timeout-secs', '3']),
    ('cancel-ignored', 4, True, ['--timeout-secs', '3']),
    # Trusted: host prompts answered once each by the harness.
    ('trusted', 0, True, T),
    ('trusted-jsonl', 0, True, T + ['--output', 'jsonl']),
    ('trusted-mismatch', 0, True, T),
    ('trusted-unknown-call', 0, True, T),
    ('trusted-repeat', 0, True, T),
    ('trusted-double-prompt', 0, True, T),
    ('trusted-repeat-id', 4, True, T),
    ('trusted-outside-tool', 4, True, T),
    ('trusted-background', 4, True, T),
    ('trusted-subagent', 4, True, T),
    ('trusted-orphan-result', 4, True, T),
    ('trusted-hook', 4, True, T),
    ('trusted-init-tools', 4, True, T),
    ('trusted-cancel', 3, True, T + ['--timeout-secs', '3']),
    # Named roles: the invocation intersected with the role (D050).
    ('agent-deny', 0, True, ['--agent', 'reviewer']),
    ('agent-reviewer', 0, True, T + ['--agent', 'reviewer']),
    ('agent-reviewer-write', 4, True, T + ['--agent', 'reviewer']),
    ('agent-coder', 0, True, T + ['--agent', 'coder']),
    ('agent-effort', 0, True, T + ['--agent', 'effortful']),
    ('agent-effort-mismatch', 2, False, T + ['--agent', 'effortful']),
    ('agent-empty', 0, True, T + ['--agent', 'empty']),
    ('agent-preview', 0, False, T + ['--agent', 'effortful', '--preview']),
    ('agent-empty-preview', 0, False, T + ['--agent', 'empty', '--preview']),
    # Refused before any launch.
    ('agent-big', 2, False, T + ['--agent', 'big']),
    ('local-first', 2, False, ['--mode', 'local-first', '--model', 'local']),
    ('slash', 2, False, []),
    ('preview', 0, False, ['--preview']),
    ('missing-runtime', 2, False, []),
]

count = 0
for case, expected, prompted, extra in CASES:
    with tempfile.TemporaryDirectory(prefix='ah-claude-') as d:
        base = Path(d).resolve()
        bindir = base / 'bin'
        bindir.mkdir()
        if case != 'missing-runtime':
            # The wrapper records names before the Python shim adds its own.
            (bindir / 'claude').write_text(
                f'#!/bin/sh\n/usr/bin/env > "$PWD/env.txt"\nexec /usr/bin/python3 {FAKE} "$@"\n')
            (bindir / 'claude').chmod(0o755)
        project = base / 'project'
        project.mkdir()
        (project / 'case').write_text(case)
        (project / 'user.txt').write_text('preserve dirty user content')
        (project / 'CLAUDE.md').write_text('never loaded')
        if case == 'agents-md':
            (project / 'AGENTS.md').write_text('project instructions')
        if case in AGENT_CASES:
            name = AGENT_CASES[case][0]
            (project / 'agents').mkdir()
            (project / f'agents/{name}.md').write_text(AGENT_FILES[name])
        cfg = dict(version=1, mode='cloud-only', native=dict(target='claude', model='sonnet'),
                   litellm=dict(api_base='http://127.0.0.1:9/v1', api_key_env='LOCAL_KEY'))
        (project / 'ah.json').write_text(json.dumps(cfg))
        env = {'PATH': f'{bindir}:/usr/bin:/bin', 'HOME': str(base), 'LOCAL_KEY': 'poison',
               'ANTHROPIC_API_KEY': 'poison', 'ANTHROPIC_BASE_URL': 'http://poison',
               'CLAUDE_CODE_USE_BEDROCK': 'poison', 'CLAUDE_CONFIG_DIR': 'poison',
               'CLAUDE_CODE_DISABLE_BACKGROUND_TASKS': '0'}
        prompt = '/review now' if case == 'slash' else 'claude task'
        args = [str(BINARY), 'single', prompt, '--project', str(project)] + extra
        if '--timeout-secs' not in extra:
            args += ['--timeout-secs', '15']
        p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=40)
        out = p.stdout + p.stderr
        assert p.returncode == expected, (case, p.returncode, p.stderr)
        for secret in SECRETS:
            assert secret not in out, (case, secret)
        assert (project / 'user.txt').read_text() == 'preserve dirty user content', case
        assert (project / 'prompted').exists() == prompted, case
        launched = (project / 'argv.json').exists()
        assert launched == (case not in ('agent-big', 'agent-preview', 'agent-empty-preview', 'local-first', 'slash', 'preview',
                                         'missing-runtime')), case
        if launched:
            argv = json.loads((project / 'argv.json').read_text())
            wanted = (TRUSTED_ARGS if case.startswith('trusted') else EXPECTED_ARGS) + ([f'--append-system-prompt-file={project}/AGENTS.md'] if case == 'agents-md' else [])
            if case in AGENT_CASES:
                wanted = AGENT_CASES[case][1]
            assert argv == wanted, (case, argv)
            names = {l.split('=', 1)[0] for l in (project / 'env.txt').read_text().splitlines() if '=' in l}
            # /bin/sh itself adds PWD, SHLVL and _.
            assert names - ENV_NAMES <= {'PWD', 'SHLVL', '_', 'OLDPWD'}, (case, names)
            assert {'HOME', 'PATH', 'DISABLE_AUTOUPDATER', 'CLAUDE_CODE_DISABLE_BACKGROUND_TASKS'} <= names, (case, names)
            env_values = dict(l.split('=', 1) for l in (project / 'env.txt').read_text().splitlines() if '=' in l)
            assert env_values['CLAUDE_CODE_DISABLE_BACKGROUND_TASKS'] == '1', case
            lines = [json.loads(l) for l in (project / 'stdin.jsonl').read_text().splitlines()]
            users = [l for l in lines if l['type'] == 'user']
            # Control preflight strictly precedes the single prompt.
            subtypes = [l['request']['subtype'] for l in lines if l['type'] == 'control_request']
            if prompted:
                assert users == [{'type': 'user', 'message': {'role': 'user', 'content': 'claude task'}}], case
                assert lines.index(users[0]) == 4, (case, lines)
                assert subtypes[:4] == ['initialize', 'get_settings', 'mcp_status', 'get_context_usage'], case
            else:
                assert users == [], case
        if case in ('success', 'agents-md'):
            assert p.stdout == 'fake response\nfinal line', (case, p.stdout)
            assert 'session_cost=0.0123 USD' in p.stderr, case
            assert 'session="sid\\\\u{9b}\\\\u{202e}"' in p.stderr, (case, p.stderr)
        if case == 'jsonl':
            records = [json.loads(l) for l in p.stdout.splitlines()]
            result = records[-1]
            assert result['type'] == 'result' and result['outcome'] == 'succeeded', result
            attempt = result['attempts'][0]
            assert attempt['runtime'] == 'claude' and attempt['runtime_version'] == '2.1.314', attempt
            assert attempt['model'] == 'sonnet' and attempt['route'] == 'cloud-only', attempt
            assert attempt['backend_stop'] == 'end_turn' and attempt['prompt_submitted'] is True, attempt
            assert attempt['grants'] == 0 and attempt['tool_events'] == 0, attempt
            assert attempt['usage']['source'] == 'claude-stream-json-result', attempt
            assert attempt['usage']['session_cost'] == {'amount': 0.0123, 'currency': 'USD'}, attempt
            assert result['response'] == 'fake response\nfinal line', result
            assert [r['type'] for r in records].count('attempt.prompt_submitted') == 1, records
        if case in ('cancel-deadline', 'cancel-ignored'):
            assert (project / 'interrupted').exists(), case
            interrupts = [l for l in lines if l['type'] == 'control_request' and l['request']['subtype'] == 'interrupt']
            assert len(interrupts) == 1, case
        if case == 'tool-use':
            assert 'tool call under deny; stopping' in p.stderr, p.stderr
        if case == 'host-request':
            assert 'host request under deny; stopping' in p.stderr, p.stderr
        answers = []
        if (project / 'permissions.jsonl').exists():
            answers = [json.loads(l) for l in (project / 'permissions.jsonl').read_text().splitlines()]
        made = {'file_path': str(project / 'made.txt'), 'content': 'made by fake'}
        # A grant is exactly the prompted input, never a rule or mode change.
        for answer in answers:
            assert set(answer) <= {'request_id', 'behavior', 'updatedInput', 'message'}, answer
        if case in ('trusted', 'trusted-jsonl'):
            assert answers == [{'request_id': 'q1', 'behavior': 'allow', 'updatedInput': made}], answers
            assert (project / 'made.txt').read_text() == 'made by fake', case
        if case == 'trusted':
            assert p.stdout == 'fake response\nfinal line', p.stdout
            assert 'permissions trusted (tools Bash, Edit, Glob, Grep, Read, Write' in p.stderr, p.stderr
            assert 'permission requests: 1; grants: 1; tool events: 4' in p.stderr, p.stderr
        if case == 'trusted-jsonl':
            attempt = [json.loads(l) for l in p.stdout.splitlines()][-1]['attempts'][0]
            assert attempt['permission_requests'] == 1 and attempt['grants'] == 1, attempt
            assert attempt['tool_events'] == 4 and attempt['permissions'] == 'trusted', attempt
        if case in ('trusted-mismatch', 'trusted-unknown-call'):
            assert [a['behavior'] for a in answers] == ['deny'], (case, answers)
            assert not (project / 'made.txt').exists(), case
            assert 'grants: 0' in p.stderr, (case, p.stderr)
        if case in ('trusted-repeat', 'trusted-double-prompt'):
            assert [a['behavior'] for a in answers] == ['allow', 'deny'], (case, answers)
            assert 'permission requests: 2; grants: 1' in p.stderr, (case, p.stderr)
            assert (project / 'made.txt').read_text() == 'made by fake', case
        if case == 'trusted-repeat-id':
            assert 'repeated or unbounded tool call; stopping' in p.stderr, p.stderr
        if case == 'trusted-outside-tool':
            assert 'tool call outside the offered tool set; stopping' in p.stderr, p.stderr
        if case in ('trusted-subagent', 'trusted-hook'):
            assert 'unsupported host request or tool record; stopping' in p.stderr, p.stderr
        if case == 'trusted-background':
            assert 'background tool call; stopping' in p.stderr, p.stderr
        if case == 'trusted-orphan-result':
            assert 'tool result without an announced call; stopping' in p.stderr, p.stderr
        if case == 'trusted-cancel':
            assert [a['behavior'] for a in answers] == ['deny'], answers
            assert not (project / 'late.txt').exists()
        if case.startswith('trusted') and expected == 4:
            assert (project / 'interrupted').exists(), case
            assert not (project / 'made.txt').exists(), case
        if case in ('tool-use', 'host-request'):
            # A violation sends a best-effort interrupt and waits up to 2 s for
            # a result before group cleanup; the stalled fake answers it.
            assert (project / 'interrupted').exists(), case
        if case in ('agent-deny', 'agent-reviewer', 'agent-coder', 'agent-effort', 'agent-empty'):
            assert p.stdout == 'fake response\nfinal line', (case, p.stdout)
            assert f'; agent {AGENT_CASES[case][0]} (body appended to the system prompt)' in p.stderr, case
        if case == 'agent-deny':
            assert 'effort model default; permissions deny (no tools offered)' in p.stderr, p.stderr
        if case == 'agent-reviewer':
            # Project reads run unprompted; the outside read is denied by the ceiling.
            assert answers == [{'request_id': 'q1', 'behavior': 'deny',
                                'message': 'denied by agent-harness policy'}], answers
            assert ('permissions trusted narrowed by agent (tools Glob, Grep, Read; '
                    'host prompts denied (ceiling below trusted)') in p.stderr, p.stderr
            assert 'permission requests: 1; grants: 0; tool events: 4' in p.stderr, p.stderr
        if case == 'agent-reviewer-write':
            assert 'tool call outside the offered tool set; stopping' in p.stderr, p.stderr
            assert (project / 'interrupted').exists() and not (project / 'made.txt').exists()
        if case in ('agent-coder', 'agent-effort'):
            assert [a['behavior'] for a in answers] == ['allow'], (case, answers)
            assert (project / 'made.txt').read_text() == 'made by fake', case
            assert 'host prompts granted once each' in p.stderr, (case, p.stderr)
        if case == 'agent-effort':
            assert 'effort high; permissions trusted narrowed by agent (tools Edit, Read, Write' in p.stderr, p.stderr
        if case == 'agent-effort-mismatch':
            assert 'preflight failed' in p.stderr, p.stderr
        if case == 'agent-empty':
            assert 'permissions trusted narrowed by agent to no tools' in p.stderr, p.stderr
        if case == 'agent-big':
            assert 'agent body exceeds 128 KiB' in p.stderr, p.stderr
        if case == 'agent-preview':
            assert ('runtime: Claude Code system-prompt append with --effort high with effective '
                    'permissions tools [Edit, Read, Write]; host prompts granted once each') in p.stdout, p.stdout
            assert 'effort high' in p.stdout and 'execution refused' not in p.stdout, p.stdout
        if case == 'agent-empty-preview':
            assert 'with effective permissions tools []; host prompts denied' in p.stdout, p.stdout
        if case == 'preview':
            assert 'route: native Claude Code' in p.stdout, p.stdout
            assert 'credentials: official CLI login' in p.stdout, p.stdout
            assert 'runtime: Claude Code stream-json; discovered' in p.stdout, p.stdout
        if case == 'missing-runtime':
            assert 'Claude Code missing' in p.stderr
        count += 1

# Sequences and Ralph refuse the Claude runtime before any launch or record.
with tempfile.TemporaryDirectory(prefix='ah-claude-seq-') as d:
    base = Path(d).resolve()
    (base / 'bin').mkdir()
    (base / 'bin/claude').symlink_to(FAKE)
    (base / 'case').write_text('success')
    (base / 'steps').mkdir()
    (base / 'steps/1-a.md').write_text('step')
    (base / 'ah.json').write_text(json.dumps(dict(version=1, mode='cloud-only',
                                                  native=dict(target='claude', model='sonnet'))))
    env = {'PATH': f'{base}/bin:/usr/bin:/bin', 'HOME': str(base), 'XDG_STATE_HOME': str(base / 'state')}
    p = subprocess.run([str(BINARY), 'sequence', 'run', str(base / 'steps'), '--project', str(base)],
                       env=env, capture_output=True, text=True, timeout=30)
    assert p.returncode == 2, p.stderr
    assert 'supports ah single only' in p.stderr, p.stderr
    assert not (base / 'argv.json').exists() and not (base / 'state').exists()
    count += 1
    # Ralph run and resume refuse too, before any launch or record.
    (base / 'ah.json').write_text(json.dumps(dict(version=1, mode='cloud-only',
                                                  native=dict(target='claude', model='sonnet'),
                                                  checks=dict(test=dict(argv=['/usr/bin/true'])))))
    (base / 'task.md').write_text('loop task')
    for args in (['ralph', 'run', str(base / 'task.md'), '--project', str(base), '--verify', 'test'],
                 ['ralph', 'resume', 'r20261106T000000Z-0123abcd', '--verify', 'test']):
        p = subprocess.run([str(BINARY)] + args, env=env, capture_output=True, text=True, timeout=30, cwd=base)
        assert p.returncode == 2, (args, p.stderr)
        assert not (base / 'argv.json').exists() and not (base / 'state').exists(), args
        if args[1] == 'run':
            assert 'supports ah single only' in p.stderr, p.stderr
        count += 1

print(f'PASS {count} Claude runtime CLI cases; preflight before prompt; deny offers no tools; trusted grants each exact prompt once; roles narrow tools and map effort; no secrets echoed')
