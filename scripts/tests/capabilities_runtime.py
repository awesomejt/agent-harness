#!/usr/bin/env python3
"""P4.8 installed OpenCode 2.2.5 inherited-capability matrix; local model stub only.

A project is planted with every tested capability source: root, parent and
nested AGENTS.md, CLAUDE.md, an `instructions` entry, skills in `.opencode/`,
`.claude/` and `.agents/`, project commands, plugins, custom tools and MCP
servers in `opencode.json`, `.opencode/opencode.json` and `.mcp.json`. Plugin,
custom-tool and MCP sources would write sentinel files if executed. Real `ah
single` runs against a loopback stub that records, in memory only, which
markers and tools each model request carries and replays scripted tool calls.

Direct ACP probes first record the runtime facts behind D040: with project
configuration disabled 2.2.5 loads no AGENTS.md unless the document names its
absolute path, and the session advertises only the built-in slash commands.
The native fallback check uses the native_runtime.py shim, which intercepts
the prompt; native request contents are not observed (no native inference).
"""
import http.server
import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
SHIM = ROOT / 'scripts/tests/native_runtime.py'
MARKERS = ['M_ROLE', 'M_AGENTS_ROOT', 'M_AGENTS_PARENT', 'M_NESTED', 'M_CLAUDE', 'M_INSTR_FILE', 'M_SKILL',
           'M_CMD']
TRUSTED = {'edit', 'glob', 'grep', 'opencode_worktree_remove', 'read', 'shell', 'skill', 'write'}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            text = json.dumps(body)
            tools = {t['function']['name'] for t in body.get('tools', [])}
            last = body['messages'][-1]
            self.server.records.append(dict(tools=tools, markers={m for m in MARKERS if m in text},
                                            result=str(last.get('content')) if last['role'] == 'tool' else None))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()

            def event(delta, finish=None):
                packet = dict(id='fixture', object='chat.completion.chunk', model='fixture',
                              choices=[dict(index=0, delta=delta, finish_reason=finish)])
                self.wfile.write(('data: ' + json.dumps(packet) + '\n\n').encode())
                self.wfile.flush()
            if tools and self.server.calls:
                name, arguments = self.server.calls.pop(0)
                event(dict(role='assistant', tool_calls=[dict(index=0, id='call-' + str(len(self.server.records)),
                      type='function', function=dict(name=name, arguments=json.dumps(arguments)))]))
                event({}, 'tool_calls')
            else:
                event(dict(role='assistant', content='done'))
                event({}, 'stop')
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError, ConnectionResetError):
            pass


def plant(base, port):
    """Repository root `repo` with project `repo/proj`; returns (project, sentinels)."""
    sentinels = base / 'sentinels'
    sentinels.mkdir()
    repo = base / 'repo'
    project = repo / 'proj'
    (project / 'sub').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    (repo / 'AGENTS.md').write_text('Parent rule M_AGENTS_PARENT\n')
    (project / 'AGENTS.md').write_text('Project rule M_AGENTS_ROOT\n')
    (project / 'CLAUDE.md').write_text('Claude rule M_CLAUDE\n')
    (project / 'sub/AGENTS.md').write_text('Nested rule M_NESTED\n')
    (project / 'sub/file.txt').write_text('plain\n')
    (project / 'extra.md').write_text('Configured rule M_INSTR_FILE\n')
    for directory in ['.opencode/skills/oc', '.opencode/skill/oc2', '.claude/skills/cl', '.agents/skills/ag']:
        skill = project / directory
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text(f'---\nname: {skill.name}\ndescription: probe M_SKILL\n---\nM_SKILL\n')
    for kind, body in [('plugin', 'export const Probe = async () => ({});'),
                       ('tool', 'export default { description: "probe", args: {}, async execute() { return "x"; } };')]:
        for directory in ['.opencode/' + kind, '.opencode/' + kind + 's']:
            (project / directory).mkdir(parents=True)
            target = json.dumps(str(sentinels / directory.replace('/', '_')))
            (project / directory / 'probe.js').write_text(f'import fs from "fs";\nfs.writeFileSync({target}, "1");\n{body}\n')
    for directory in ['.opencode/command', '.opencode/commands']:
        (project / directory).mkdir(parents=True)
        (project / directory / 'probecmd.md').write_text('---\ndescription: probe M_CMD\n---\nM_CMD\n')

    def local(name):
        return dict(type='local', command=['/usr/bin/touch', str(sentinels / name)])
    (project / '.opencode/opencode.json').write_text(json.dumps(dict(mcp=dict(dot=local('mcp_dot')), instructions=['extra.md'])))
    (project / '.mcp.json').write_text(json.dumps(dict(mcpServers=dict(probe=dict(command='/usr/bin/touch',
                                                                                   args=[str(sentinels / 'mcp_json')])))))
    # Unmanaged keys survive managed sync but are never loaded by the isolated runtime.
    (project / 'opencode.json').write_text(json.dumps(dict(mcp=dict(root=local('mcp_root')), instructions=['extra.md'],
                                                          plugin=[str(project / '.opencode/plugins/probe.js')])))
    (project / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only', model='fixture',
                                                    litellm=dict(api_base=f'http://127.0.0.1:{port}/v1', api_key_env='CAP_KEY'))))
    return project, sentinels


def ah(project, prompt, *extra, env=None):
    args = [str(ROOT / 'target/debug/ah'), 'single', prompt, '--project', str(project), '--timeout-secs', '60', *extra]
    return subprocess.run(args, env=env or {**os.environ, 'CAP_KEY': 'unused-cap-key'}, capture_output=True, text=True,
                          timeout=120)


def direct(runtime, base, name, instructions, prompt_port):
    """ACP initialize/session/new (and a prompt when a stub port is given) with
    the harness isolation flags; returns (advertised commands, records)."""
    project = base / ('direct-' + name)
    home = base / ('home-' + name)
    project.mkdir()
    home.mkdir(mode=0o700)
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    (project / 'AGENTS.md').write_text('Project rule M_AGENTS_ROOT\n')
    model = dict(providerID='ah-litellm', model='fixture')
    config = dict(model=model, update='disable', share='disabled',
                  permissions=[dict(action='*', resource='*', effect='deny')], agents=dict(title=dict(model=model)),
                  instructions=[str(project / 'AGENTS.md')] if instructions else [], mcp={}, plugins=[],
                  providers={'ah-litellm': dict(package='aisdk:@ai-sdk/openai-compatible',
                             settings=dict(apiKey='unused', baseURL=f'http://127.0.0.1:{prompt_port}/v1'),
                             models=dict(fixture=dict(name='fixture')))})
    env = dict(PATH=os.environ['PATH'], HOME=str(home), OPENCODE_CONFIG_CONTENT=json.dumps(config),
               OPENCODE_DISABLE_PROJECT_CONFIG='true', OPENCODE_DISABLE_MODELS_FETCH='true',
               OPENCODE_DISABLE_AUTOUPDATE='true', **{f'XDG_{k}_HOME': str(home / k) for k in ['CONFIG', 'DATA', 'CACHE', 'STATE']})
    p = subprocess.Popen([runtime, 'acp'], cwd=project, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True)
    commands = None
    try:
        def call(identifier, method, params):
            nonlocal commands
            p.stdin.write(json.dumps(dict(jsonrpc='2.0', id=identifier, method=method, params=params)) + '\n')
            p.stdin.flush()
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if not select.select([p.stdout], [], [], 1)[0]:
                    continue
                message = json.loads(p.stdout.readline())
                update = message.get('params', {}).get('update', {})
                if update.get('sessionUpdate') == 'available_commands_update':
                    commands = [c['name'] for c in update['availableCommands']]
                if message.get('id') == identifier:
                    return message['result']
            raise AssertionError('ACP response missing')
        call(1, 'initialize', dict(protocolVersion=1, clientCapabilities={}))
        session = call(2, 'session/new', dict(cwd=str(project), mcpServers=[]))
        result = call(3, 'session/prompt', dict(sessionId=session['sessionId'], prompt=[dict(type='text', text='hi')]))
        assert result['stopReason'] == 'end_turn', result
        return commands
    finally:
        p.kill()
        p.wait()


def main():
    runtime = shutil.which('opencode')
    assert runtime, 'OpenCode 2.2.5 required'
    runtime = str(Path(runtime).resolve())
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_port
    checks = []

    def run(project, prompt, calls, *extra):
        server.records, server.calls = [], list(calls)
        p = ah(project, prompt, *extra)
        primary = [r for r in server.records if r['tools']]
        return p, primary, [r for r in server.records if not r['tools']]

    try:
        with tempfile.TemporaryDirectory(prefix='ah-capabilities-runtime-') as d:
            base = Path(d).resolve()
            # Direct runtime facts (D040).
            for named in [False, True]:
                server.records, server.calls = [], []
                commands = direct(runtime, base, str(named), named, port)
                markers = set().union(*(r['markers'] for r in server.records))
                assert markers == ({'M_AGENTS_ROOT'} if named else set()), (named, markers)
            assert commands == ['init', 'review', 'goal', 'compact'], commands
            checks.append('direct: AGENTS.md loads only when named; built-in commands init/review/goal/compact')

            project, sentinels = plant(base, port)
            abs_sub = str(project / 'sub/file.txt')
            # Trusted unnamed: denied/unavailable tool paths, then a granted nested read.
            p, primary, helpers = run(project, 'Probe capabilities', [
                ('skill', dict(id='oc')), ('task', dict(description='d', prompt='p', subagent_type='general')),
                ('webfetch', dict(url='http://127.0.0.1:9/')), ('read', dict(path=abs_sub))],
                '--permissions', 'trusted')
            assert p.returncode == 0, (p.returncode, p.stderr)
            assert 'permission requests: 1; grants: 1;' in p.stderr, p.stderr
            assert len(primary) == 5 and all(r['tools'] == TRUSTED for r in primary), primary
            assert all('M_AGENTS_ROOT' in r['markers'] for r in primary)
            assert all(not r['markers'] & {'M_AGENTS_PARENT', 'M_CLAUDE', 'M_INSTR_FILE', 'M_SKILL', 'M_CMD'}
                       for r in primary), primary
            assert 'Unable to load skill oc' in primary[1]['result'], primary[1]
            assert 'No tool named \\"task\\"' in primary[2]['result'], primary[2]
            assert 'No tool named \\"webfetch\\"' in primary[3]['result'], primary[3]
            assert 'M_NESTED' not in set().union(*(r['markers'] for r in primary[:4]))
            assert 'M_NESTED' in primary[4]['markers'], primary[4]
            assert helpers and all(not r['markers'] for r in helpers), helpers
            checks.append('trusted: root AGENTS.md only; skill load fails; task/webfetch absent; nested AGENTS.md after granted read')

            # Deny: only the gated skill tool is offered and cannot load.
            p, primary, _ = run(project, 'Probe capabilities', [('skill', dict(id='cl'))])
            assert p.returncode == 0 and 'permission requests: 0; grants: 0;' in p.stderr, p.stderr
            assert all(r['tools'] == {'skill'} and r['markers'] == {'M_AGENTS_ROOT'} for r in primary), primary
            assert 'Unable to load skill cl' in primary[1]['result'], primary
            checks.append('deny: tools [skill]; skill load fails; root AGENTS.md')

            # Named reviewer: role system text and project instructions together.
            (project / 'agents').mkdir()
            (project / 'agents/reviewer.md').write_text((ROOT / 'agents/reviewer.md').read_text() + 'M_ROLE\n')
            p, primary, _ = run(project, 'Probe capabilities', [('skill', dict(id='ag'))], '--permissions', 'trusted',
                                '--agent', 'reviewer')
            assert p.returncode == 0, (p.returncode, p.stderr)
            assert all(r['tools'] == {'glob', 'grep', 'read', 'skill'} for r in primary), primary
            assert all(r['markers'] == {'M_ROLE', 'M_AGENTS_ROOT'} for r in primary), primary
            assert 'Unable to load skill ag' in primary[1]['result'], primary
            checks.append('reviewer: role system + AGENTS.md; tools [glob, grep, read, skill]')

            # Slash-command prompts refuse before any runtime or model request.
            for prompt in ['/review', ' /init', '/compact now', '/goal x', '/probecmd']:
                p, primary, helpers = run(project, prompt, [], '--permissions', 'trusted')
                assert p.returncode == 2 and not primary and not helpers, (prompt, p.returncode, p.stderr)
                assert 'runtime slash command' in p.stderr, p.stderr
            p, primary, _ = run(project, '/sub/file.txt looks wrong', [])
            assert p.returncode == 0 and primary and primary[0]['markers'] == {'M_AGENTS_ROOT'}, p.stderr
            checks.append('slash-command prompts exit 2 with no request; a leading path is text')

            # Without a project AGENTS.md: CLAUDE.md and parent AGENTS.md are still not loaded.
            (project / 'AGENTS.md').unlink()
            p, primary, _ = run(project, 'Probe capabilities', [])
            assert p.returncode == 0 and primary and all(not r['markers'] for r in primary), primary
            checks.append('no project AGENTS.md: no instructions (CLAUDE.md, parent unused)')

            assert not any(sentinels.iterdir()), sorted(s.name for s in sentinels.iterdir())
            checks.append('no plugin, custom tool or MCP server executed')

            # Local-first native fallback carries the same instructions entry through
            # real preflight; the shim intercepts the prompt.
            (project / 'AGENTS.md').write_text('Project rule M_AGENTS_ROOT\n')
            bin_dir = base / 'bin'
            bin_dir.mkdir()
            script = bin_dir / 'opencode'
            script.write_text('#!' + sys.executable + '\nimport os\nos.execv(' + repr(sys.executable) + ', ' +
                              repr([sys.executable, str(SHIM), '--shim', runtime]) + ' + __import__("sys").argv[1:])\n')
            script.chmod(0o755)
            with socket.socket() as closed:
                closed.bind(('127.0.0.1', 0))
                endpoint = f'http://127.0.0.1:{closed.getsockname()[1]}/v1'
            (project / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-first', model='fixture',
                litellm=dict(api_base=endpoint, api_key_env='CAP_KEY'),
                native=dict(target='opencode', model='gpt-5.4', api_key_env='NATIVE_KEY'))))
            env = {**os.environ, 'PATH': str(bin_dir) + ':' + os.environ['PATH'], 'CAP_KEY': 'unused-cap-key',
                   'NATIVE_KEY': 'unused-native-key'}
            p = ah(project, 'Never forwarded to provider', '--agent', 'reviewer', '--permissions', 'trusted', env=env)
            assert p.returncode == 0, (p.returncode, p.stderr)
            assert 'attempt=2 local-first fallback via OpenCode 2.2.5; model opencode/gpt-5.4' in p.stderr, p.stderr
            assert (project / 'intercepted-native-prompt').exists()
            assert not any(sentinels.iterdir())
            checks.append('local-first native fallback: preflight with instructions entry passes; prompt intercepted')
    finally:
        server.shutdown()
        server.server_close()
    for check in checks:
        print('PASS', check)
    print(f'PASS installed OpenCode 2.2.5 inherited capabilities: {len(checks)} checks; local model stub only')


if __name__ == '__main__':
    main()
