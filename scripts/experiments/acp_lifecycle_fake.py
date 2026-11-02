#!/usr/bin/env python3
"""Adversarial ACP child fixture; only used in a disposable fixture project."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

cwd = Path.cwd()
case = json.loads((cwd / 'fixture.json').read_text())
scenario, failure = case['scenario'], case['failure']
assert 'ANTHROPIC_API_KEY' not in os.environ
assert 'OPENCODE_CONFIG_CONTENT' not in os.environ
# This descendant deliberately survives SIGTERM and outlives its parent.
descendant = subprocess.Popen([sys.executable, '-c',
    'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.1)
(cwd / 'pids.json').write_text(json.dumps([os.getpid(), descendant.pid]))


def send(value):
    print(json.dumps(value), flush=True)


def reply(identifier, result):
    send({'jsonrpc': '2.0', 'id': identifier, 'result': result})


prompt_id = None
for line in sys.stdin:
    message = json.loads(line)
    method = message.get('method')
    if method == 'initialize':
        reply(message['id'], {'protocolVersion': 1, 'agentCapabilities': {}})
    elif method == 'session/new':
        reply(message['id'], {'sessionId': 'fixture-session', 'configOptions': [{
            'id': 'model', 'name': 'Model', 'type': 'select',
            'currentValue': 'wrong' if failure == 'wrong-model' else 'harness-preflight/fixture',
            'options': [{'value': 'harness-preflight/fixture', 'name': 'fixture'}]}]})
    elif method == 'session/prompt':
        prompt_id = message['id']
        if failure in ('deadline', 'interrupt'):
            continue
        if failure == 'unexpected-fs':
            send({'jsonrpc': '2.0', 'id': 101, 'method': 'fs/read_text_file',
                  'params': {'sessionId': 'fixture-session', 'path': str(cwd / 'denied.txt')}})
            continue
        if failure == 'eof':
            break
        if failure == 'malformed':
            print('{not-json', flush=True)
            continue
        if failure == 'oversized':
            print('x' * 2_100_000, flush=True)
            continue
        if scenario == 'deny':
            options = [{'optionId': 'reject', 'name': 'Deny', 'kind': 'reject_once'}]
            if failure == 'duplicate-options':
                options *= 2
            if failure == 'no-denial':
                options = [{'optionId': 'always', 'name': 'Allow', 'kind': 'allow_always'}]
            send({'jsonrpc': '2.0', 'id': 100, 'method': 'session/request_permission', 'params': {
                'sessionId': 'fixture-session', 'toolCall': {'toolCallId': 'read-1', 'title': 'Read',
                'rawInput': {'filePath': str(cwd / 'denied.txt')}}, 'options': options}})
            if failure == 'send-failure':
                break
        else:
            marker = 'AH_PROJECT_INSTRUCTIONS_OK' if scenario == 'instruction' else 'AH_ACP_LIFECYCLE_OK'
            send({'jsonrpc': '2.0', 'method': 'session/update', 'params': {
                'sessionId': 'wrong' if failure == 'wrong-session' else 'fixture-session',
                'update': {'sessionUpdate': 'agent_message_chunk', 'content': {'type': 'text', 'text': marker}}}})
            if scenario != 'cancel':
                reply(prompt_id, {'stopReason': 'end_turn'})
    elif method == 'session/cancel':
        reply(prompt_id, {'stopReason': 'cancelled'})
    elif message.get('id') == 100:
        expected = {'outcome': 'cancelled'} if failure == 'no-denial' else {'outcome': 'selected', 'optionId': 'reject'}
        assert message.get('result', {}).get('outcome') == expected
        reply(prompt_id, {'stopReason': 'end_turn'})
