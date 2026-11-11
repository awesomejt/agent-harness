#!/usr/bin/env python3
"""Opt-in macOS Pi 1.5.0 resource inventory, HTTP trap and adversarial deny; no production proof."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import time

_feasibility = importlib.util.spec_from_file_location(
    'pi_feasibility', Path(__file__).resolve().parent / 'pi_feasibility.py')
_feasibility_module = importlib.util.module_from_spec(_feasibility)
_feasibility.loader.exec_module(_feasibility_module)
check = _feasibility_module.check
containment_checks = _feasibility_module.containment_checks
profile = _feasibility_module.profile
signal_group = _feasibility_module.signal_group
tree_hash = _feasibility_module.tree_hash
CLI_HASH = _feasibility_module.CLI_HASH
NODE_HASH = _feasibility_module.NODE_HASH
TREE_HASH = _feasibility_module.TREE_HASH

LIMIT = 2 * 1024 * 1024
TIMEOUT = 10
FAILURE = 'Pi resource route probe failed; raw diagnostics withheld'
INVENTORY = [('disable-compaction', 'set_auto_compaction'), ('disable-retry', 'set_auto_retry'),
             ('inventory-state', 'get_state')]
ADVERSARIAL = [('deny-prompt', 'prompt'), ('deny-bash', 'bash'), ('post-adversarial', 'get_state')]


def bound_capture(command, cwd, env, data=None):
    """Bound both pipes; always reap the child group."""
    child = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True,
                             stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    output = {'out': bytearray(), 'err': bytearray()}
    deadline = time.monotonic() + TIMEOUT
    count = 0
    try:
        selector.register(child.stdout, selectors.EVENT_READ, 'out')
        selector.register(child.stderr, selectors.EVENT_READ, 'err')
        if data is not None:
            child.stdin.write(data)
            child.stdin.close()
        while selector.get_map():
            remaining = deadline - time.monotonic()
            check(remaining > 0)
            for key, _ in selector.select(min(.1, remaining)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                count += len(chunk)
                check(count <= LIMIT)
                output[key.data].extend(chunk)
        check(child.wait(timeout=max(.01, deadline - time.monotonic())) == 0)
        return bytes(output['out']), bytes(output['err'])
    finally:
        try:
            try:
                if child.stdin is not None and not child.stdin.closed:
                    child.stdin.close()
                signal_group(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    pass
            finally:
                signal_group(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
        finally:
            selector.close()
            child.stdout.close()
            child.stderr.close()


def contained_profile(root, operator_home, port):
    check(type(port) is int and 1 <= port <= 65535)
    return (profile(root, operator_home)
            + f'(allow network-bind network-inbound (local tcp "localhost:{port}"))'
            + f'(allow network-outbound (remote tcp "localhost:{port}"))')


def inventory_requests():
    lines = []
    for ident, command in INVENTORY:
        payload = {'id': ident, 'type': command,
                   **({'enabled': False} if command != 'get_state' else {})}
        lines.append(json.dumps(payload))
    return '\n'.join(lines).encode() + b'\n'


def adversarial_requests(marker):
    return b''.join(json.dumps(record).encode() + b'\n' for record in (
        {'id': 'deny-prompt', 'type': 'prompt', 'message': 'AH_ADVERSARIAL_PROMPT'},
        {'id': 'deny-bash', 'type': 'bash',
         'command': f'touch {marker} # AH_ADVERSARIAL_MARKER'},
        {'id': 'post-adversarial', 'type': 'get_state'},
    ))


def validate_permissive_adversarial(stdout, stderr, marker):
    """Same hostile RPCs without blocking hooks; marker must appear without harness errors."""
    text = ((stdout.decode() if isinstance(stdout, (bytes, bytearray)) else stdout)
            + (stderr.decode() if isinstance(stderr, (bytes, bytearray)) else stderr))
    check('Harness blocked user bash' not in text)
    check('Harness blocked agent start' not in text)
    check('Harness blocked provider request' not in text)
    check(marker.is_file())


def validate_inventory(stdout, stderr):
    inventory = [json.loads(line, object_pairs_hook=unique_object) for line in stderr.splitlines() if line.strip()]
    check(len(inventory) == 1 and inventory[0].get('type') == 'ah_resource_route')
    report = inventory[0]
    check(isinstance(report.get('providers'), list))
    configured = report.get('configured')
    check(isinstance(configured, list) and 'ah-feasibility' in configured)
    registry = report.get('registry')
    check(isinstance(registry, dict))
    for key in ('all', 'available', 'chat', 'image', 'classifier'):
        check(type(registry.get(key)) is int and registry[key] >= 0)
    check(registry['all'] >= registry['available'])
    tools = report.get('tools')
    check(isinstance(tools, list))
    for tool in tools:
        check(isinstance(tool, dict) and isinstance(tool.get('name'), str))
        check(isinstance(tool.get('sourceInfo'), dict))
        check('path' not in tool['sourceInfo'] or tool['sourceInfo']['path'] in ('present', 'absent'))
    check(isinstance(report.get('mcp'), list) and report.get('active') == [])
    messages = [json.loads(line, object_pairs_hook=unique_object) for line in stdout.splitlines() if line.strip()]
    check(len(messages) == len(INVENTORY))
    for message, (ident, command) in zip(messages, INVENTORY):
        check(message.get('type') == 'response' and message.get('id') == ident
              and message.get('command') == command and message.get('success') is True)
    state = messages[-1].get('data')
    check(isinstance(state, dict) and state.get('messageCount') == 0
          and state.get('model', {}).get('provider') == 'ah-feasibility')
    return report


def parse_responses(stdout):
    responses = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        message = json.loads(line, object_pairs_hook=unique_object)
        if message.get('type') == 'response' and message.get('id'):
            responses[message['id']] = message
    return responses


def validate_adversarial(stdout, stderr, marker):
    text = ((stdout.decode() if isinstance(stdout, (bytes, bytearray)) else stdout)
            + (stderr.decode() if isinstance(stderr, (bytes, bytearray)) else stderr))
    responses = parse_responses(text)
    check(set(responses) == {ident for ident, _ in ADVERSARIAL})
    bash = responses['deny-bash']
    check(bash.get('success') is False and isinstance(bash.get('error'), str) and bash['error'])
    state = responses['post-adversarial']
    check(state.get('success') is True)
    data = state.get('data')
    check(isinstance(data, dict) and data.get('messageCount') == 0
          and data.get('pendingMessageCount') == 0)
    check('Harness blocked user bash' in text)
    check('Harness blocked agent start' in text or 'Harness blocked provider request' in text)
    check('"stopReason":"stop"' not in text and '"stopReason":"toolUse"' not in text)
    check(not marker.exists())


def validate_trap(stdout):
    lines = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    check(len(lines) == 1 and lines[0].get('type') == 'ah_http_trap')
    hits = lines[0].get('requests')
    check(isinstance(hits, list) and hits)
    for hit in hits:
        check(isinstance(hit, dict) and hit.get('method') == 'GET'
              and hit.get('path') in ('/v1/models', '/models'))
        headers = hit.get('headers')
        check(isinstance(headers, list) and 'authorization' in headers)
        check(hit.get('authorizationSynthetic') is True)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result)
        result[key] = value
    return result


def refresh_probe_source(port, runtime, agent_dir):
    return textwrap.dedent(f"""
        import {{createServer}} from 'node:http';
        import {{join}} from 'node:path';
        import {{ModelRuntime}} from {json.dumps(runtime.as_uri())};
        const port = {port};
        const agentDir = {json.dumps(str(agent_dir))};
        const requests = [];
        const server = createServer((req, res) => {{
          const pathOnly = (req.url ?? '').split('?')[0];
          const authorization = req.headers.authorization;
          requests.push({{
            method: req.method,
            path: pathOnly,
            headers: Object.keys(req.headers).sort(),
            authorizationSynthetic: authorization === 'Bearer synthetic',
          }});
          res.writeHead(200, {{'content-type': 'application/json'}});
          res.end(JSON.stringify({{object: 'list', data: [{{id: 'ah-trap-discovered', object: 'model'}}]}}));
        }});
        await new Promise((resolve) => server.listen(port, '127.0.0.1', resolve));
        const runtime = await ModelRuntime.create({{
          modelsPath: join(agentDir, 'models.json'),
          authPath: join(agentDir, 'auth.json'),
          allowModelNetwork: true,
          refreshOnCreate: false,
        }});
        const models = [
          {{type: 'chat', id: 'ah-trap-discovered', name: 'ah-trap-discovered', api: 'openai-completions',
            provider: 'ah-feasibility', baseUrl: `http://127.0.0.1:${{port}}/v1`, reasoning: false,
            input: ['text'], cost: {{input: 0, output: 0, cacheRead: 0, cacheWrite: 0}},
            contextWindow: 4096, maxTokens: 1024}},
        ];
        runtime.registerProvider('ah-feasibility', {{
          api: 'openai-completions',
          apiKey: '${{AH_FAKE_KEY}}',
          baseUrl: `http://127.0.0.1:${{port}}/v1`,
          models,
          async refreshModels(context) {{
            if (!context.allowNetwork || context.signal.aborted) return models;
            const response = await fetch(`http://127.0.0.1:${{port}}/v1/models`, {{
              signal: context.signal,
              headers: {{Authorization: 'Bearer synthetic'}},
            }});
            const payload = await response.json();
            return (payload.data ?? []).map((entry) => ({{
              type: 'chat', id: entry.id, name: entry.id, api: 'openai-completions',
              provider: 'ah-feasibility', baseUrl: `http://127.0.0.1:${{port}}/v1`,
              reasoning: false, input: ['text'],
              cost: {{input: 0, output: 0, cacheRead: 0, cacheWrite: 0}},
              contextWindow: 4096, maxTokens: 1024,
            }}));
          }},
        }});
        await runtime.refresh({{allowNetwork: true, providers: ['ah-feasibility']}});
        console.log(JSON.stringify({{type: 'ah_http_trap', requests}}));
        server.close();
    """).strip() + '\n'


def extension_source(blocking=True):
    guards = """
  pi.on('tool_call', () => ({block: true, reason: 'Harness adversarial deny'}));"""
    if blocking:
        guards += """
  pi.on('before_agent_start', () => { throw new Error('Harness blocked agent start'); });
  pi.on('before_provider_request', () => { throw new Error('Harness blocked provider request'); });
  pi.on('user_bash', () => { throw new Error('Harness blocked user bash'); });"""
    witness = """
    const marker = process.env.AH_MARKER_PATH;
    if (marker) fs.writeFileSync(marker, 'witness');"""
    imports = "import fs from 'node:fs';\n" if not blocking else ''
    suppressed = '' if blocking else witness
    return imports + """export default function(pi) {""" + guards + """
  pi.on('session_start', async (_event, ctx) => {
    const registry = ctx.modelRegistry;
    const redact = (info) => info ? {source: info.source ?? null,
      path: info.path ? 'present' : 'absent'} : {source: null, path: 'absent'};
  const tools = pi.getAllTools().map((tool) => ({
      name: tool.name,
      sourceInfo: redact(tool.sourceInfo),
    })).sort((a,b)=>a.name.localeCompare(b.name));
    const report = {
      type: 'ah_resource_route',
      providers: [...registry.getRegisteredProviderIds()].sort(),
      configured: [...new Set(registry.getAll().map((model) => model.provider))].sort(),
      registry: {
        all: registry.getAll().length,
        available: registry.getAvailable().length,
        chat: registry.getModelsOfType('chat').length,
        image: registry.getModelsOfType('image').length,
        classifier: registry.getModelsOfType('classifier').length,
      },
      tools,
      active: pi.getActiveTools().map((tool) => tool.name).sort(),
      mcp: pi.getMcpServers().map((server) => server.name).sort(),
    };
    process.stderr.write(JSON.stringify(report) + '\\n');""" + suppressed + """
  });
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, type=Path, help='managed 1.5.0 release directory')
    parser.add_argument('--node', required=True, type=Path, help='tested Node 24.14.0 executable')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    package = args.release / 'node_modules/@earendil-works/pi-coding-agent'
    manifest = json.loads((package / 'package.json').read_text())
    check(manifest.get('name') == '@earendil-works/pi-coding-agent' and manifest.get('version') == '1.5.0')
    check(hashlib.sha256((package / 'dist/bundle/cli.js').read_bytes()).hexdigest() == CLI_HASH)
    check(hashlib.sha256(args.node.read_bytes()).hexdigest() == NODE_HASH)
    with tempfile.TemporaryDirectory(prefix='ah-pi-resource-route-') as directory:
        root = Path(directory).resolve()
        shutil.copytree(args.release / 'node_modules', root / 'node_modules', symlinks=True)
        node = root / 'node'
        shutil.copy2(args.node, node)
        check(tree_hash(root / 'node_modules') == TREE_HASH)
        check(hashlib.sha256(node.read_bytes()).hexdigest() == NODE_HASH)
        cli = root / 'node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
        home, project, state = root / 'home', root / 'repo/project', root / 'state'
        for path in (home, project, state, root / 'repo/.git'):
            path.mkdir(parents=True, exist_ok=True)
        marker = root / 'ah-adversarial-marker'
        env = {'HOME': str(home), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin',
               'PI_CODING_AGENT_DIR': str(state), 'PI_SKIP_VERSION_CHECK': '1',
               'NO_COLOR': '1', 'TERM': 'dumb', 'LANG': 'C',
               'AH_FAKE_KEY': 'synthetic-not-a-credential', 'AH_MARKER_PATH': str(marker)}
        sandbox_base = ['/usr/bin/sandbox-exec', '-p', profile(root, Path.home())]
        with tempfile.TemporaryDirectory(prefix='.ah-pi-read-', dir=Path.home()) as protected:
            read_target = Path(protected) / 'sentinel'
            read_target.write_text('AH_READ_DENIAL_SENTINEL')
            with tempfile.TemporaryDirectory(prefix='ah-pi-fence-') as fence:
                bound_capture([*sandbox_base, '/Library/Developer/CommandLineTools/usr/bin/python3', '-B', '-c',
                               containment_checks(read_target, Path(fence) / 'write')], project, env)
        print('PASS: network bind, operator-home data read and outside write denied', flush=True)
        reservation = socket.socket()
        reservation.bind(('127.0.0.1', 0))
        trap_port = reservation.getsockname()[1]
        reservation.close()
        policy = contained_profile(root, Path.home(), trap_port)

        def run(flags, data=None, network=False):
            box = ['/usr/bin/sandbox-exec', '-p', policy if network else profile(root, Path.home())]
            return bound_capture([*box, str(node), str(cli), *flags], project, env, data)

        (state / 'settings.json').write_text(json.dumps({
            'compaction': {'enabled': False},
            'retry': {'enabled': False, 'provider': {'maxRetries': 0}},
            'cacheWarming': 'off'}))
        (state / 'models.json').write_text(json.dumps({'providers': {'ah-feasibility': {
            'baseUrl': f'http://127.0.0.1:{trap_port}/v1', 'api': 'openai-completions',
            'apiKey': '${AH_FAKE_KEY}', 'models': [{'id': 'ah-no-inference'}]}}}))
        extension = root / 'resource-route.mjs'
        extension.write_text(extension_source())
        flags = ['--offline', '--mode', 'rpc', '--no-session', '--no-tools',
                 '--no-extensions', '--no-mcp', '--no-skills', '--no-prompt-templates',
                 '--no-themes', '--no-context-files', '--provider', 'ah-feasibility',
                 '--model', 'ah-no-inference', '-e', str(extension)]
        inventory = inventory_requests()
        out, err = run(flags, inventory)
        validate_inventory(out, err)
        print('PASS: provider registry inventory and idle synthetic model state', flush=True)
        if marker.exists():
            marker.unlink()
        hostile = adversarial_requests(marker)
        out, err = run(flags, hostile)
        validate_adversarial(out, err, marker)
        positive = root / 'resource-route-positive.mjs'
        positive.write_text(extension_source(blocking=False))
        positive_flags = [flag if flag != str(extension) else str(positive) for flag in flags]
        marker.unlink(missing_ok=True)
        control_out, control_err = run(positive_flags, inventory_requests() + hostile)
        validate_permissive_adversarial(control_out, control_err, marker)
        print('PASS: prompt and bash refused before provider/bash side effects', flush=True)
        probe = root / 'refresh_probe.mjs'
        copied_runtime = root / 'node_modules/@earendil-works/pi-coding-agent/dist/core/model-runtime.js'
        probe.write_text(refresh_probe_source(trap_port, copied_runtime, state))
        trap_out, trap_err = bound_capture([*['/usr/bin/sandbox-exec', '-p', policy], str(node), str(probe)],
                                           project, env)
        check(not trap_err)
        validate_trap(trap_out)
        print('PASS: refresh-hook listing trap; header names and synthetic-auth flag only', flush=True)
        print('GATE OPEN: adapter/production and lifecycle proofs remain', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if os.environ.get('AH_PROBE_DEBUG'):
            raise
        _ = error
        print(FAILURE, file=sys.stderr)
        sys.exit(1)
