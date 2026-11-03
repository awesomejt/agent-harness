#!/usr/bin/env python3
"""P3.2 installed native preflight/ACP session check; no model prompt forwarded.

The shim executes real OpenCode for version/debug checks and forwards ACP setup.
It intercepts session/prompt and returns a synthetic terminal. This proves setup
compatibility, not native inference; P3.5 owns live native use evidence.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]


def shim(runtime):
    args = sys.argv[3:]
    if 'acp' not in args:
        os.execv(runtime, [runtime, *args])
    child = subprocess.Popen([runtime, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    lock = threading.Lock()
    def output():
        for line in child.stdout:
            with lock:
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
    threading.Thread(target=output, daemon=True).start()
    for line in sys.stdin.buffer:
        msg = json.loads(line)
        if msg.get('method') == 'session/prompt':
            Path('intercepted-native-prompt').touch()
            with lock:
                print(json.dumps(dict(jsonrpc='2.0', id=msg['id'], result=dict(stopReason='end_turn'))), flush=True)
        else:
            assert msg.get('method') != 'session/cancel'
            child.stdin.write(line)
            child.stdin.flush()


def main():
    runtime = shutil.which('opencode')
    assert runtime, 'OpenCode 1.18.30 required'
    runtime = str(Path(runtime).resolve())
    with tempfile.TemporaryDirectory(prefix='ah-native-runtime-') as d:
        base = Path(d).resolve()
        bin_dir = base/'bin'
        bin_dir.mkdir()
        script = bin_dir/'opencode'
        script.write_text('#!'+sys.executable+'\nimport os\nos.execv('+repr(sys.executable)+', '+repr([sys.executable, str(Path(__file__).resolve()), '--shim', runtime])+ ' + __import__("sys").argv[1:])\n')
        script.chmod(0o755)
        project = base/'project'
        project.mkdir()
        (project/'ah.json').write_text(json.dumps(dict(version=1, mode='cloud-only',
            native=dict(target='opencode', model='gpt-5.4', api_key_env='NATIVE_KEY'))))
        sentinel = b'{"provider":{"ah-litellm":{"options":{"baseURL":"http://127.0.0.1:9/v1"}}},"model":"ah-litellm/fixture","small_model":"ah-litellm/fixture","enabled_providers":["ah-litellm"]}'
        (project/'opencode.json').write_bytes(sentinel)
        for trusted in [False, True]:
            args = [str(ROOT/'target/debug/ah'), 'single', 'Never forwarded to provider', '--project', str(project), '--timeout-secs', '30']
            if trusted: args += ['--permissions', 'trusted', '--no-sync']
            env={**os.environ, 'PATH':str(bin_dir)+':'+os.environ['PATH'], 'NATIVE_KEY':'unused-native-test-key',
                 'OPENCODE_CONFIG_CONTENT':'poison', 'OPENCODE_AUTH_CONTENT':'poison', 'OPENCODE_API_KEY':'poison'}
            p=subprocess.run(args, env=env, capture_output=True, text=True, timeout=45)
            assert p.returncode == 0, (p.returncode, p.stderr)
            assert (project/'intercepted-native-prompt').exists(), p.stderr
            (project/'intercepted-native-prompt').unlink()
            assert (project/'opencode.json').read_bytes() == sentinel
            assert not (project/'.ah-opencode-owner.json').exists()
            assert not (project/'.ah-opencode.lock').exists()
            assert 'unused-native-test-key' not in p.stdout+p.stderr
            assert 'model opencode/gpt-5.4' in p.stderr
    print('PASS installed OpenCode 1.18.30 native preflight and ACP session; deny/trusted; 0 native prompts forwarded; managed routing preserved')


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--shim':
        shim(sys.argv[2])
    else:
        main()
