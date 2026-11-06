#!/usr/bin/env python3
"""Fake Claude Code 2.1.314 print-mode stream-json executable, used only via a disposable PATH.

Emulates the surfaces recorded in docs/evidence/p7-2-claude-launch.md: control
responses for initialize/get_settings/mcp_status/get_context_usage before any
prompt, then system/init, rate_limit_event, assistant and result records, and an
aborted result after an interrupt. The project's `case` file selects a deviation.
Records argv and every stdin line in the project; the test wrapper records the environment.
"""
import json
import os
from pathlib import Path
import sys
import time

cwd = Path.cwd()
case = (cwd / 'case').read_text().strip()
VERSION = '2.1.314'
MODEL = 'claude-sonnet-5-5'
(cwd / 'argv.json').write_text(json.dumps(sys.argv[1:]))
log = open(cwd / 'stdin.jsonl', 'a')


def emit(record):
    sys.stdout.write(json.dumps(record) + '\n')
    sys.stdout.flush()


def control(request_id, response):
    emit({'type': 'control_response',
          'response': {'subtype': 'success', 'request_id': request_id, 'response': response}})


def respond(request_id, subtype):
    if case == 'control-error' and subtype == 'initialize':
        emit({'type': 'control_response',
              'response': {'subtype': 'error', 'request_id': request_id, 'error': 'nope'}})
        return
    if case == 'eof-before-submit' and subtype == 'get_settings':
        sys.exit(1)
    if case == 'early-record' and subtype == 'mcp_status':
        emit({'type': 'system', 'subtype': 'status'})
        return
    if subtype == 'initialize':
        control(request_id, {
            'commands': [{'name': 'review'}] if case == 'commands' else [],
            'agents': [{'name': 'Explore'}], 'output_style': 'default', 'models': [],
            'account': {'email': 'SECRET_ACCOUNT_SENTINEL'}, 'pid': os.getpid(),
            'claude_code_version': '2.1.315' if case == 'version' else VERSION,
            'current_permission_mode': 'acceptEdits' if case == 'permission-mode' else 'default'})
    elif subtype == 'get_settings':
        control(request_id, {
            'effective': {}, 'applied': {'model': MODEL, 'effort': 'medium'},
            'sources': [{'source': 'policySettings'}] if case == 'managed-settings' else []})
    elif subtype == 'mcp_status':
        control(request_id, {'mcpServers': [{'name': 'm'}] if case == 'mcp' else []})
    elif subtype == 'get_context_usage':
        categories = [{'id': 'system_prompt', 'kind': 'used', 'tokens': 1500},
                      {'id': 'messages', 'kind': 'used', 'tokens': 10},
                      {'id': 'free_space', 'kind': 'free', 'tokens': 9000}]
        if case == 'context-tools':
            categories.append({'id': 'system_tools', 'kind': 'used', 'tokens': 1000})
        control(request_id, {'model': MODEL, 'categories': categories,
                             'memoryFiles': [{'path': 'CLAUDE.md'}] if case == 'memory' else [],
                             'mcpTools': [], 'agents': []})
    elif subtype == 'interrupt':
        (cwd / 'interrupted').touch()
        if case == 'cancel-ignored':
            return
        control(request_id, {'still_queued': []})
        emit({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
              'terminal_reason': 'aborted_streaming', 'stop_reason': None,
              'total_cost_usd': 0.0, 'session_id': 'sid'})


def init():
    record = {'type': 'system', 'subtype': 'init', 'cwd': os.getcwd(), 'session_id': 'sid\u009b‮',
              'tools': ['Read'] if case == 'init-tools' else [], 'mcp_servers': [],
              'model': 'claude-opus-5-5' if case == 'init-model' else MODEL,
              'permissionMode': 'default', 'slash_commands': [],
              'apiKeySource': 'ANTHROPIC_API_KEY' if case == 'init-key' else 'none',
              'claude_code_version': VERSION, 'output_style': 'default',
              'agents': ['claude', 'Explore'], 'skills': [],
              'plugins': [{'name': 'cc-plugin-agents-md', 'path': 'builtin',
                           'source': 'cc-plugin-agents-md@builtin'}]}
    emit(record)


def turn(text):
    (cwd / 'prompted').write_text(text)
    if case == 'eof-after-submit':
        sys.exit(0)
    if case == 'before-init':
        emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'x'}]}})
        return
    init()
    emit({'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed'}})
    if case in ('cancel-deadline', 'cancel-ignored'):
        return
    if case == 'malformed':
        sys.stdout.write('{not json\n')
        sys.stdout.flush()
        return
    if case == 'tool-use':
        emit({'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {'command': 'touch pwned'}}]}})
        time.sleep(0.5)
        return
    if case == 'host-request':
        emit({'type': 'control_request', 'request_id': 'q1',
              'request': {'subtype': 'can_use_tool', 'tool_name': 'Bash', 'input': {}}})
        time.sleep(0.5)
        return
    emit({'type': 'assistant', 'message': {'model': MODEL, 'content': [
        {'type': 'thinking', 'thinking': 'SECRET_REASONING_SENTINEL'},
        {'type': 'text', 'text': 'fake response'}]}})
    if case == 'error-result':
        emit({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
              'stop_reason': None, 'result': 'SECRET_PROVIDER_ERROR', 'total_cost_usd': 0.001})
        return
    emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'stop_reason': 'end_turn',
          'result': 'fake response\nfinal line', 'total_cost_usd': 0.0123, 'session_id': 'sid',
          'num_turns': 1, 'permission_denials': []})


for line in sys.stdin:
    log.write(line)
    log.flush()
    record = json.loads(line)
    if record['type'] == 'control_request':
        respond(record['request_id'], record['request']['subtype'])
    elif record['type'] == 'user':
        turn(record['message']['content'])
