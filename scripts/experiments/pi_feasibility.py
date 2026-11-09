#!/usr/bin/env python3
"""Opt-in macOS Pi 1.5.0 no-inference discovery; not production control proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

LIMIT = 2 * 1024 * 1024
TIMEOUT = 10
FAILURE = 'Pi feasibility probe failed; raw diagnostics withheld'
CLI_HASH = 'e79626f2dd6f94aa45d30f3fa63cd84319a6eefcd150b353cfaf274366926774'
TREE_HASH = '2af836467c982ecb6dc38764d4d192585d5893e096354255c8028af19aa5b159'
NODE_HASH = '20a18709f0154d668f1bd6f6ea8c2a7ae001447b4b2c339732f22e57a8767a55'
COMMANDS = [('disable-compaction', 'set_auto_compaction'),
            ('disable-retry', 'set_auto_retry'), ('state', 'get_state')]


def check(value):
    if not value:
        raise RuntimeError('observation changed; reassess control gate')


def tree_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            value = 'link:' + str(path.readlink())
        elif path.is_file():
            value = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            continue
        digest.update((str(path.relative_to(root)) + '\0' + value + '\n').encode())
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result)
        result[key] = value
    return result


def requests():
    # Deliberately no caller-controlled method or parameters.
    return b''.join((json.dumps({'id': ident, 'type': command,
        **({'enabled': False} if command != 'get_state' else {})}) + '\n').encode()
        for ident, command in COMMANDS)


def validate(stdout, stderr):
    messages = [json.loads(line, object_pairs_hook=unique_object) for line in stdout.splitlines() if line.strip()]
    check(len(messages) == 3)
    reports = [json.loads(line, object_pairs_hook=unique_object) for line in stderr.splitlines() if line.strip()]
    check(len(reports) == 1)
    report = reports[0]
    check(isinstance(report, dict) and report.get('type') == 'ah_inventory')
    check(report.get('active') == [] and report.get('mcp') == [])
    check(report.get('all') == [])
    check(report.get('sentinelLoaded') is False)
    for message, (ident, command) in zip(messages, COMMANDS):
        check(isinstance(message, dict) and message.get('type') == 'response'
              and message.get('id') == ident and message.get('command') == command
              and message.get('success') is True and 'error' not in message)
    state = messages[-1].get('data')
    check(isinstance(state, dict))
    check(state.get('isStreaming') is False and state.get('isCompacting') is False
          and state.get('autoCompactionEnabled') is False
          and type(state.get('messageCount')) is int and state['messageCount'] == 0
          and type(state.get('pendingMessageCount')) is int and state['pendingMessageCount'] == 0
          and 'sessionFile' not in state)
    model = state.get('model')
    check(isinstance(model, dict) and model.get('provider') == 'ah-feasibility'
          and model.get('id') == 'ah-no-inference'
          and model.get('baseUrl') == 'http://127.0.0.1:9/v1'
          and model.get('api') == 'openai-completions')
    return state


def signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        # macOS can report EPERM for a just-disappeared orphan group. Ignore it
        # only after ps confirms there are no members; live groups still fail.
        result = subprocess.run(['/bin/ps', '-x', '-g', str(pid), '-o', 'stat='],
                                capture_output=True, timeout=2)
        check(result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip())


def capture(command, cwd, env, data=None):
    """Bound both pipes while reading; always reap the entire child group."""
    if data is not None:
        check(data == requests())
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


def profile(root, operator_home):
    return ('(version 1)(allow default)(deny network*)'
            '(deny file-write* (require-not (subpath ' + json.dumps(str(root)) + ')))'
            '(deny file-read-data (subpath ' + json.dumps(str(operator_home)) + '))')


def containment_checks(read_target, write_target):
    return ('import pathlib,socket; '
            + 'ops=[lambda: socket.socket().bind(("127.0.0.1",0)), '
            + 'lambda: pathlib.Path(' + repr(str(read_target)) + ').read_bytes(), '
            + 'lambda: pathlib.Path(' + repr(str(write_target)) + ').write_text("x")]; '
            + '\nfor op in ops:\n try: op()\n except PermissionError: pass'
            + '\n else: raise RuntimeError("containment failed")\n')


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
    with tempfile.TemporaryDirectory(prefix='ah-pi-feasibility-') as directory:
        root = Path(directory).resolve()
        # Copy runtime code only. Never follow the managed wrapper into real state.
        shutil.copytree(args.release / 'node_modules', root / 'node_modules', symlinks=True)
        node = root / 'node'
        shutil.copy2(args.node, node)
        check(tree_hash(root / 'node_modules') == TREE_HASH)
        check(hashlib.sha256(node.read_bytes()).hexdigest() == NODE_HASH)
        cli = root / 'node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'
        home, project, state = root / 'home', root / 'repo/project', root / 'state'
        for path in (home, project, state, root / 'repo/.git'):
            path.mkdir(parents=True, exist_ok=True)
        env = {'HOME': str(home), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin',
               'PI_CODING_AGENT_DIR': str(state), 'PI_OFFLINE': '1',
               'PI_SKIP_VERSION_CHECK': '1', 'NO_COLOR': '1', 'TERM': 'dumb', 'LANG': 'C',
               'AH_FAKE_KEY': 'synthetic-not-a-credential'}
        sandbox = ['/usr/bin/sandbox-exec', '-p', profile(root, Path.home())]
        with tempfile.TemporaryDirectory(prefix='.ah-pi-read-', dir=Path.home()) as protected:
            read_target = Path(protected) / 'sentinel'
            read_target.write_text('AH_READ_DENIAL_SENTINEL')
            with tempfile.TemporaryDirectory(prefix='ah-pi-fence-') as fence:
                capture([*sandbox, '/Library/Developer/CommandLineTools/usr/bin/python3', '-B', '-c',
                         containment_checks(read_target, Path(fence) / 'write')], project, env)
        print('PASS: network bind, operator-home data read and outside write denied', flush=True)
        def run(flags, data=None):
            return capture([*sandbox, str(node), str(cli), *flags], project, env, data)
        out, err = capture([*sandbox, str(node), '--version'], project, env)
        check(out.strip() == b'v24.14.0' and not err)
        out, err = run(['--version'])
        check(out.strip() == b'1.5.0' and not err)
        print('PASS: pinned CLI bundle and Node; installed version=1.5.0', flush=True)
        sentinels = {home / '.pi/agent/AGENTS.md': 'AH_UNPLANNED_HOME',
                     root / 'repo/AGENTS.md': 'AH_UNPLANNED_PARENT',
                     project / 'AGENTS.md': 'AH_UNPLANNED_PROJECT',
                     project / '.pi/SYSTEM.md': 'AH_UNPLANNED_SYSTEM',
                     state / 'AGENTS.md': 'AH_UNPLANNED_STATE',
                     state / 'skills/inert/SKILL.md': '---\nname: inert\ndescription: inert\n---\nAH_UNPLANNED_SKILL',
                     state / 'prompts/inert.md': 'AH_UNPLANNED_TEMPLATE'}
        for path, content in sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        # Executable discovery canaries are safe only inside verified containment.
        marker = root / 'unexpected-extension-load'
        for directory in (state, project / '.pi'):
            canary = directory / 'extensions/inert.mjs'
            canary.parent.mkdir(parents=True, exist_ok=True)
            canary.write_text('import fs from "node:fs"; fs.writeFileSync('
                              + json.dumps(str(marker)) + ', "unexpected"); '
                              + 'export default function() {}')
        (state / 'settings.json').write_text(json.dumps({
            'cacheWarming': 'off', 'compaction': {'enabled': False},
            'retry': {'enabled': False, 'provider': {'maxRetries': 0}}}))
        (state / 'models.json').write_text(json.dumps({'providers': {'ah-feasibility': {
            'baseUrl': 'http://127.0.0.1:9/v1', 'api': 'openai-completions',
            'apiKey': '${AH_FAKE_KEY}', 'models': [{'id': 'ah-no-inference'}]}}}))
        extension = root / 'inventory.mjs'
        extension.write_text("""export default function(pi) {
  pi.on('tool_call', () => ({block: true, reason: 'No inference feasibility only'}));
  pi.on('session_start', (_event, ctx) => {
    process.stdout.write(JSON.stringify({type:'ah_inventory',
      active:pi.getActiveTools(), all:pi.getAllTools().map(t=>t.name).sort(),
      mcp:pi.getMcpServers(), sentinelLoaded:ctx.getSystemPrompt().includes('AH_UNPLANNED')})+'\\n');
  });
}
""")
        flags = ['--offline', '--mode', 'rpc', '--no-session', '--no-tools',
                 '--no-extensions', '--no-mcp', '--no-skills', '--no-prompt-templates',
                 '--no-themes', '--no-context-files', '--provider', 'ah-feasibility',
                 '--model', 'ah-no-inference', '-e', str(extension)]
        out, err = run(flags, requests())
        validate(out, err)
        check(all(path.read_text() == content for path, content in sentinels.items()))
        check(not marker.exists())
        check(not list(state.glob('sessions/**/*.jsonl')))
        print('PASS: active tools=[], configured tools=[], MCP=[]; inert context absent; discovery canaries unloaded', flush=True)
        print('PASS: correlated disable retry/compaction and idle synthetic model state; no session file', flush=True)
        print('GATE OPEN: effective resource/settings/credential inventory, route capture and adversarial tool enforcement remain; no prompt sent', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(FAILURE, file=sys.stderr)
        sys.exit(1)
