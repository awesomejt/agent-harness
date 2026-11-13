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
launches = cwd / 'launches.jsonl'
index = len(launches.read_text().splitlines()) if launches.exists() else 0
with open(launches, 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\n')
if (cwd / 'cases').exists():
    picked = json.loads((cwd / 'cases').read_text())
    case = picked[min(index, len(picked) - 1)]
FINAL = 'done\nAH-RALPH-COMPLETE' if case == 'claim' else 'fake response\nfinal line'
(cwd / 'argv.json').write_text(json.dumps(sys.argv[1:]))
def _flag_value(long, short=None):
    for i, a in enumerate(sys.argv):
        if a == long and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if short and a == short and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(long + '='):
            return a.split('=', 1)[1]
    return None


MODEL = _flag_value('--model') or 'fixture'
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
    if '--no-tools' in sys.argv or '-nt' in sys.argv:
        return []
    spec = _flag_value('--tools', '-t') or ''
    return sorted(spec.split(',')) if spec else []


def state():
    tools = active_tool_names()
    data = {
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
    if case in ('trusted-state-no-inventories', 'state-omit-deny'):
        for key in ('activeTools', 'tools', 'mcpServers'):
            data.pop(key, None)
    return data


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
        if case == 'models-key' and key != '${AH_PI_LITELLM_API_KEY}':
            emit({'type': 'response', 'id': ident, 'command': command, 'success': False, 'error': 'apiKey'})
            return
    if command == 'prompt':
        (cwd / 'prompted').write_text(request.get('message', ''))
        disposition = 'handled' if case == 'prompt-handled' else 'started'
        emit({'type': 'response', 'id': ident, 'command': 'prompt', 'success': True,
              'data': {'disposition': disposition}})
        if case == 'prompt-handled':
            return
        if case == 'eof-after-submit':
            sys.exit(0)
        if case == 'empty-settled':
            emit({'type': 'agent_settled', 'aborted': False})
            return
        if case == 'session-text':
            emit({
                'type': 'agent_end',
                'messages': [{
                    'role': 'assistant',
                    'content': [{'type': 'text', 'text': 'session event response\n'}],
                }],
            })
            emit({'type': 'agent_settled', 'aborted': False})
            return
        if case == 'trusted-state-no-inventories':
            emit({
                'type': 'agent_end',
                'messages': [{
                    'role': 'assistant',
                    'content': [{'type': 'text', 'text': 'fake response\nfinal line\n'}],
                }],
            })
            emit({'type': 'agent_settled', 'aborted': False})
            return
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
        if case == 'assistant-stop-error':
            emit({
                'type': 'agent_end',
                'messages': [{
                    'role': 'assistant',
                    'stopReason': 'error',
                    'errorMessage': 'secret provider text',
                    'content': [{'type': 'text', 'text': 'partial answer\n'}],
                }],
            })
            emit({'type': 'agent_settled', 'assistantText': 'partial answer\n'})
            return
        if case == 'assistant-stop-length':
            emit({
                'type': 'agent_end',
                'messages': [{
                    'role': 'assistant',
                    'stopReason': 'length',
                    'content': [{'type': 'text', 'text': 'trimmed answer\n'}],
                }],
            })
            emit({'type': 'agent_settled', 'assistantText': 'trimmed answer\n'})
            return
        if case == 'settled-aborted':
            emit({'type': 'agent_settled', 'aborted': True, 'assistantText': 'should not succeed\n'})
            return
        if case in ('cancel-deadline', 'cancel-stall'):
            time.sleep(30)
            return
        if case.startswith('trusted'):
            ui_id = 'ui-1'
            title = 'ah-permission'
            method = 'confirm'
            message = json.dumps({'toolName': 'read', 'toolCallId': 'tc-1', 'input': {'path': 'x.txt'}})
            if case == 'trusted-bad-title':
                title = 'other'
            elif case == 'trusted-bad-method':
                method = 'pick'
            elif case == 'trusted-unknown-tool':
                message = json.dumps({'toolName': 'mystery', 'toolCallId': 'tc-1', 'input': {}})
            elif case == 'trusted-malformed-ui':
                message = 'not-json'
            elif case == 'trusted-duplicate-ui':
                payload = message
                emit({'type': 'extension_ui_request', 'id': ui_id, 'method': method,
                      'title': title, 'message': payload})
                read()
                emit({'type': 'extension_ui_request', 'id': ui_id, 'method': method,
                      'title': title, 'message': payload})
                time.sleep(0.2)
                return
            if case in ('trusted-success', 'agent-reviewer', 'trusted-write'):
                emit({'type': 'extension_ui_request', 'id': ui_id, 'method': method,
                      'title': title, 'message': message})
                resp = read()
                if case == 'trusted-success':
                    (cwd / 'ui_response.json').write_text(json.dumps(resp))
                if not resp.get('confirmed'):
                    emit({'type': 'agent_settled', 'error': True})
                    return
                if case == 'trusted-write':
                    (cwd / 'made.txt').write_text('made by fake')
            elif case.startswith('trusted-'):
                emit({'type': 'extension_ui_request', 'id': ui_id, 'method': method,
                      'title': title, 'message': message})
                time.sleep(0.5)
                return
        emit({'type': 'message', 'role': 'assistant', 'content': FINAL})
        emit({'type': 'agent_settled', 'assistantText': FINAL})
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
