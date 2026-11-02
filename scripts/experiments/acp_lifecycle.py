#!/usr/bin/env python3
"""P1.3 disposable Unix SDK experiment. No production CLI or proxy configuration.

Build the sibling acp_lifecycle crate with Rust 1.88.0 first. Default runs fake
child checks. --runtime exercises installed OpenCode against a local model stub.
--live requires an explicit existing LiteLLM endpoint/model and environment key.
"""
import argparse
import contextlib
import http.server
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit

BINARY = Path(__file__).with_name('acp_lifecycle') / 'target/debug/ah-acp-lifecycle-experiment'
MARKER = 'AH_ACP_LIFECYCLE_OK'
INSTRUCTION_MARKER = 'AH_PROJECT_INSTRUCTIONS_OK'


@contextlib.contextmanager
def project(alias, endpoint, key, scenario):
    with tempfile.TemporaryDirectory(prefix='ah-p1-3-') as root:
        base = Path(root).resolve()
        cwd = base / 'project'
        cwd.mkdir()
        # A Git root prevents traversal into unrelated ancestor instruction files.
        subprocess.run(['git', 'init', '-q', str(cwd)], check=True)
        permission = {'*': 'deny', 'external_directory': {
            '*': 'deny', str(base / 'data/opencode/tool-output/*'): 'deny'}}
        tools = {'*': False}
        if scenario == 'deny':
            permission['read'] = 'ask'
            tools['read'] = True
            (cwd / 'denied.txt').write_text('AH_DENIED_FILE_CONTENT_MUST_NOT_REACH_MODEL')
        if scenario == 'instruction':
            (cwd / 'AGENTS.md').write_text(
                'For this integration test, reply with exactly ' + INSTRUCTION_MARKER +
                ' and nothing else. Never use tools.\n')
        target = 'harness-preflight/' + alias
        config = {
            'autoupdate': False, 'share': 'disabled', 'plugin': [], 'mcp': {},
            'permission': permission, 'tools': tools,
            'enabled_providers': ['harness-preflight'], 'model': target, 'small_model': target,
            'provider': {'harness-preflight': {
                'npm': '@ai-sdk/openai-compatible',
                'options': {'baseURL': endpoint, 'apiKey': '{env:AH_PROBE_API_KEY}'},
                'models': {alias: {'name': alias, 'limit': {'context': 32768, 'output': 4096}}},
            }},
        }
        (cwd / 'opencode.json').write_text(json.dumps(config))
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': root,
               **{'XDG_' + kind.upper() + '_HOME': str(base / kind)
                  for kind in ['config', 'data', 'cache', 'state']},
               'OPENCODE_DISABLE_MODELS_FETCH': 'true',
               'OPENCODE_DISABLE_DEFAULT_PLUGINS': 'true',
               'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'AH_PROBE_API_KEY': key}
        yield cwd, env, target, permission, tools


def preflight(executable, cwd, env, target, permission, tools, endpoint):
    def debug(*args):
        return json.loads(subprocess.check_output(
            [executable, 'debug', *args, '--pure'], cwd=cwd, env=env,
            stderr=subprocess.PIPE, timeout=30))
    config = debug('config')
    expected = {'permission': permission, 'tools': tools, 'model': target, 'small_model': target,
                'enabled_providers': ['harness-preflight'], 'autoupdate': False, 'share': 'disabled'}
    if any(config.get(k) != v for k, v in expected.items()) or config.get('plugin') or config.get('mcp'):
        raise RuntimeError('effective config widened')
    provider = config['provider']['harness-preflight']
    if provider['options']['baseURL'] != endpoint or provider['npm'] != '@ai-sdk/openai-compatible':
        raise RuntimeError('effective provider differs')
    rules = debug('agent', 'build')['permission']
    expected_rules = [{'permission': '*', 'pattern': '*', 'action': 'deny'},
                      {'permission': 'external_directory', 'pattern': '*', 'action': 'deny'},
                      {'permission': 'external_directory', 'pattern': next(
                          x for x in permission['external_directory'] if x != '*'), 'action': 'deny'}]
    if 'read' in permission:
        expected_rules.insert(1, {'permission': 'read', 'pattern': '*', 'action': 'ask'})
    if rules[-len(expected_rules):] != expected_rules:
        raise RuntimeError('effective agent widened')


class Recorder(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 2_000_000 or self.path != '/v1/chat/completions':
                self.send_error(400)
                return
            raw = self.rfile.read(size)
            body = json.loads(raw)
            if body.get('model') != self.server.alias:
                raise ValueError('wrong wire model')
            serialized = json.dumps(body)
            self.server.observed.append({
                'model': body['model'], 'instructionPresent': INSTRUCTION_MARKER in serialized,
                'deniedContentPresent': 'AH_DENIED_FILE_CONTENT_MUST_NOT_REACH_MODEL' in serialized,
                'tools': [x['function']['name'] for x in body.get('tools', [])],
            })
            if self.server.upstream:
                request = urllib.request.Request(self.server.upstream + '/chat/completions', data=raw,
                    headers={'Content-Type': 'application/json',
                             'Authorization': 'Bearer ' + self.server.key})
                with urllib.request.urlopen(request, timeout=170) as response:
                    self.send_response(response.status)
                    self.send_header('Content-Type', response.headers.get('Content-Type', 'text/event-stream'))
                    self.end_headers()
                    while chunk := response.read1(8192):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.end_headers()
            def event(delta, finish=None):
                packet = {'id': 'fixture', 'object': 'chat.completion.chunk', 'model': self.server.alias,
                          'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                self.wfile.write(('data: ' + json.dumps(packet) + '\n\n').encode())
                self.wfile.flush()
            if (self.server.scenario == 'deny' and not self.server.read_issued
                    and 'read' in self.server.observed[-1]['tools']):
                self.server.read_issued = True
                event({'role': 'assistant', 'tool_calls': [{'index': 0, 'id': 'fixture-read',
                      'type': 'function', 'function': {'name': 'read',
                      'arguments': json.dumps({'filePath': str(self.server.cwd / 'denied.txt')})}}]})
                event({}, 'tool_calls')
            else:
                marker = INSTRUCTION_MARKER if self.server.scenario == 'instruction' else MARKER
                event({'role': 'assistant', 'content': marker})
                if self.server.scenario == 'cancel':
                    # Keep the turn pending until ACP cancellation; server thread is daemonized.
                    time.sleep(4)
                event({}, 'stop')
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.server.failed = True
            # Do not expose arbitrary upstream error bodies/credentials.
            self.send_error(502, 'experiment transport failed')


@contextlib.contextmanager
def recorder(alias, upstream, key, scenario):
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Recorder)
    server.daemon_threads = True
    server.alias, server.upstream, server.key, server.scenario = alias, upstream, key, scenario
    server.observed, server.failed, server.read_issued = [], False, False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, 'http://127.0.0.1:' + str(server.server_port) + '/v1'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def runtime(args):
    executable = shutil.which(args.opencode)
    if not executable:
        raise RuntimeError('OpenCode executable missing')
    executable = str(Path(executable).resolve())
    print('OpenCode:', subprocess.check_output([executable, '--version'], timeout=15).decode().strip(), flush=True)
    upstream, key, alias = None, 'unused', 'fixture'
    if args.live:
        if not args.endpoint or not args.model:
            raise RuntimeError('--live requires explicit endpoint/model')
        parsed = urlsplit(args.endpoint)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise RuntimeError('invalid endpoint')
        upstream, alias = args.endpoint.rstrip('/'), args.model
        key = os.environ.get(args.key_env)
        if not key:
            raise RuntimeError('missing credential environment variable')
        request = urllib.request.Request(upstream + '/models', headers={'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(request, timeout=15) as response:
            if alias not in [x.get('id') for x in json.load(response).get('data', [])]:
                raise RuntimeError('alias absent from discovery')
    for scenario in args.scenarios:
        with recorder(alias, upstream, key, scenario) as (server, endpoint):
            if scenario == 'unavailable':
                endpoint = 'http://127.0.0.1:9/v1'
            with project(alias, endpoint, key, scenario) as (cwd, env, target, permission, tools):
                server.cwd = cwd
                preflight(executable, cwd, env, target, permission, tools, endpoint)
                prompts = {
                    'text': 'Reply with exactly ' + MARKER + ' and nothing else. Do not use tools.',
                    'instruction': 'Follow the project instructions for this integration test. Do not use tools.',
                    'deny': 'Use the read tool to read denied.txt. Do not try any other tool or retry if denied. Then reply DENIED.',
                    'cancel': 'Write a very long explanation of sorting algorithms, at least 3000 words. Do not use tools.',
                    'unavailable': 'Reply OK. Do not use tools.',
                }
                result = subprocess.run([str(BINARY), executable, str(cwd), target, scenario, prompts[scenario]],
                                        env=env, capture_output=True, text=True, timeout=200)
                print(scenario + ': ' + result.stdout.strip(), flush=True)
                print('Wire evidence: ' + json.dumps(server.observed), flush=True)
                summaries = [json.loads(line) for line in result.stdout.splitlines()]
                cleanup = next((x for x in summaries if x.get('directChildReaped')), None)
                if not cleanup:
                    raise RuntimeError('runtime cleanup not confirmed')
                processes = subprocess.check_output(['ps', '-axo', 'pgid=,stat='], text=True)
                if any(line.split()[0] == str(cleanup['processGroup']) and
                       not line.split()[1].startswith('Z') for line in processes.splitlines() if line.split()):
                    raise RuntimeError('runtime process group survived')
                if scenario == 'unavailable' and not any(x.get('promptError') for x in summaries):
                    raise RuntimeError('unavailable did not report a prompt error')
                if (result.returncode == 0) == (scenario == 'unavailable'):
                    raise RuntimeError('unexpected scenario outcome: ' + scenario)
                records = server.observed
                if scenario != 'unavailable' and (not records or server.failed):
                    raise RuntimeError('no successful wire observation')
                if scenario == 'instruction' and not any(x['instructionPresent'] for x in records):
                    raise RuntimeError('project instructions absent from model request')
                if any(x['deniedContentPresent'] for x in records):
                    raise RuntimeError('denied file content reached model')
                if scenario != 'deny' and any(x['tools'] for x in records):
                    raise RuntimeError('unexpected tool available')
                print('PASS ' + scenario, flush=True)


def fixtures():
    fixture = Path(__file__).with_name('acp_lifecycle_fake.py').resolve()
    for scenario, failure in [('text', None), ('instruction', None), ('deny', None), ('cancel', None),
                              ('text', 'eof'), ('text', 'malformed'), ('text', 'wrong-model'),
                              ('text', 'wrong-session'), ('deny', 'duplicate-options'),
                              ('deny', 'no-denial'), ('deny', 'send-failure'), ('text', 'oversized'),
                              ('text', 'unexpected-fs'), ('text', 'deadline'), ('text', 'interrupt'),
                              ('text', 'early-notification'), ('text', 'oversized-text')]:
        with project('fixture', 'http://127.0.0.1:9/v1', 'sentinel', scenario) as (cwd, env, target, *_):
            (cwd / 'fixture.json').write_text(json.dumps({'scenario': scenario, 'failure': failure}))
            # Environment poisoning must not survive Rust's allowlist.
            env['AH_EXPERIMENT_DEADLINE_SECS'] = '8'
            env['ANTHROPIC_API_KEY'] = 'must-not-inherit'
            env['OPENCODE_CONFIG_CONTENT'] = 'must-not-inherit'
            stdout = None
            child = subprocess.Popen([str(BINARY), str(fixture), str(cwd), target, scenario, 'fixture'],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                if failure == 'interrupt':
                    deadline = time.monotonic() + 5
                    while not (cwd / 'pids.json').exists() and time.monotonic() < deadline:
                        time.sleep(.05)
                    child.send_signal(signal.SIGINT)
                stdout, _stderr = child.communicate(timeout=25)
                result = subprocess.CompletedProcess(child.args, child.returncode, stdout)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
                # Also contain fixture failures in the test driver itself.
                if (cwd / 'pids.json').exists():
                    pids = json.loads((cwd / 'pids.json').read_text())
                    if stdout is None:
                        for pid in pids:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
            expected_success = failure in (None, 'no-denial', 'early-notification')
            if (result.returncode == 0) != expected_success:
                raise RuntimeError('fixture outcome: ' + scenario + '/' + str(failure))
            if failure in ('duplicate-options', 'unexpected-fs', 'wrong-session', 'oversized', 'oversized-text') and 'protocolViolation' not in result.stdout:
                raise RuntimeError('client did not reject the protocol violation')
            pids = json.loads((cwd / 'pids.json').read_text())
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                alive = []
                for pid in pids:
                    status = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)],
                                            capture_output=True, text=True).stdout.strip()
                    if status and not status.startswith('Z'):
                        alive.append(pid)
                if not alive:
                    break
                time.sleep(.05)
            if alive:
                for pid in alive:
                    os.kill(pid, signal.SIGKILL)
                raise RuntimeError('surviving descendant')
            if 'directChildReaped' not in result.stdout:
                raise RuntimeError('cleanup not confirmed')
            print('PASS fixture ' + scenario + '/' + str(failure) + '; child/descendant absent', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', action='store_true')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--endpoint')
    parser.add_argument('--model')
    parser.add_argument('--key-env', default='LITELLM_API_KEY')
    parser.add_argument('--opencode', default='opencode')
    parser.add_argument('--scenarios', nargs='+', choices=['text', 'instruction', 'deny', 'cancel', 'unavailable'],
                        default=['text', 'instruction', 'deny', 'cancel', 'unavailable'])
    args = parser.parse_args()
    if not BINARY.is_file():
        parser.error('build the sibling acp_lifecycle crate first')
    try:
        runtime(args) if args.runtime or args.live else fixtures()
    except Exception:
        parser.exit(1, 'Lifecycle checks failed; raw error withheld.\n')


if __name__ == '__main__':
    main()
