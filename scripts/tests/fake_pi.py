#!/usr/bin/env python3
"""Fake Pi 1.5.0 RPC executable for deny-profile harness tests."""
import json
import os
from pathlib import Path
import sys
import time

VERSION = '1.5.0'
PROVIDER = 'ah-litellm'

cwd = Path.cwd()
case = (cwd / 'case').read_text().strip()
(cwd / 'argv.json').write_text(json.dumps(sys.argv[1:]))
MODEL = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--model=')), 'fixture')
log = open(cwd / 'stdin.jsonl', 'a')


def models_api_key():
    root = os.environ.get('PI_CODING_AGENT_DIR')
    if not root:
        return None
    path = Path(root) / 'models.json'
    if not path.is_file():
        return None
    payload = json.loads(path.read_text())
    key = payload.get('providers', {}).get(PROVIDER, {}).get('apiKey')
    if case == 'models-key' and key:
        (cwd / 'models_key.txt').write_text(str(key))
    return key


def emit(record):
    if isinstance(record, str):
        sys.stdout.write(record + '\n')
    else:
        sys.stdout.write(json.dumps(record) + '\n')
    sys.stdout.flush()


def read():
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    log.write(line)
    log.flush()
    return json.loads(line)


def active_tool_names():
    if '--no-tools' in sys.argv:
        return []
    spec = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--tools=')), '')
    return sorted(spec.split(',')) if spec else []


def state():
    tools = active_tool_names()
    return {
        'isStreaming': False,
        'isCompacting': case == 'streaming',
        'autoCompactionEnabled': case == 'project-settings',
        'autoRetryEnabled': False,
        'messageCount': 0,
        'pendingMessageCount': 0,
        'piVersion': '1.6.0' if case == 'version' else VERSION,
        'model': {
            'provider': 'wrong' if case == 'init-model' else PROVIDER,
            'id': 'other' if case == 'init-model' else MODEL,
            'baseUrl': 'http://poison/v1' if case == 'init-model' else 'http://127.0.0.1:9/v1',
            'api': 'openai-completions',
        },
        'activeTools': (['bash'] if case in ('state-tools', 'init-tools') else tools),
        'mcpServers': ['x'] if case == 'mcp' else [],
        'tools': (['bash'] if case in ('state-tools', 'init-tools') else tools),
    }


def respond(request):
    ident = request['id']
    command = request['type']
    if case == 'eof-before-submit' and command == 'set_auto_retry':
        sys.exit(1)
    if case == 'control-error' and command == 'get_state':
        emit({'type': 'response', 'id': ident, 'command': command, 'success': False, 'error': 'nope'})
        return
    if command == 'get_state' and case != 'control-error':
        key = models_api_key()
        if case == 'models-key' and key != '${LOCAL_KEY}':
            emit({'type': 'response', 'id': ident, 'command': command, 'success': False, 'error': 'apiKey'})
            return
    if command == 'prompt':
        (cwd / 'prompted').write_text(request.get('message', ''))
        emit({'type': 'response', 'id': ident, 'command': 'prompt', 'success': True,
              'data': {'disposition': 'started'}})
        if case == 'tool-use':
            emit({'type': 'tool_call', 'name': 'bash'})
            time.sleep(0.5)
            return
        if case == 'malformed':
            emit('not-json')
            return
        if case == 'error-result':
            emit({'type': 'agent_settled', 'error': True})
            return
        if case in ('cancel-deadline', 'cancel-stall'):
            time.sleep(30)
            return
        if case == 'trusted-success':
            ui_id = 'ui-1'
            payload = json.dumps({'toolName': 'read', 'toolCallId': 'tc-1', 'input': {'path': 'x.txt'}})
            emit({'type': 'extension_ui_request', 'id': ui_id, 'method': 'confirm',
                  'title': 'ah-permission', 'message': payload})
            resp = read()
            (cwd / 'ui_response.json').write_text(json.dumps(resp))
            if not resp.get('confirmed'):
                emit({'type': 'agent_settled', 'error': True})
                return
        text = 'fake response\nfinal line'
        emit({'type': 'message', 'role': 'assistant', 'content': text})
        emit({'type': 'agent_settled', 'assistantText': text})
        return
    if command == 'abort':
        (cwd / 'aborted').touch()
        emit({'type': 'response', 'id': ident, 'command': 'abort', 'success': True})
        emit({'type': 'agent_settled', 'assistantText': '', 'error': True})
        return
    emit({'type': 'response', 'id': ident, 'command': command, 'success': True,
          **(({'data': state()}) if command == 'get_state' else {})})


while True:
    req = read()
    if req.get('type') in ('set_auto_compaction', 'set_auto_retry', 'get_state', 'prompt', 'abort'):
        respond(req)
