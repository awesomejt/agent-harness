#!/usr/bin/env python3
"""Fake Claude Code 2.1.314 print-mode stream-json executable, used only via a disposable PATH.

Emulates the surfaces recorded in docs/evidence/p7-2-claude-launch.md: control
responses for initialize/get_settings/mcp_status/get_context_usage before any
prompt, then system/init, rate_limit_event, assistant and result records, and an
aborted result after an interrupt. With `--permission-prompts=host` (trusted) it
announces tool calls, sends `can_use_tool` prompts, waits for the harness's
answer and records it in `permissions.jsonl`, writing a file only on a grant.
`get_settings` echoes `--effort` (else the model default, `medium`).
The project's `case` file selects a deviation. A workflow run launches once per
step or iteration: each launch appends its argv to `launches.jsonl`, and an
optional `cases` file (a JSON list) selects that launch's case by index, the
last entry repeating. Case `claim` ends the response with the Ralph marker.
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
launches = cwd / 'launches.jsonl'
index = len(launches.read_text().splitlines()) if launches.exists() else 0
with open(launches, 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\n')
if (cwd / 'cases').exists():
    cases = json.loads((cwd / 'cases').read_text())
    case = cases[min(index, len(cases) - 1)]
FINAL = 'done\nAH-RALPH-COMPLETE' if case == 'claim' else 'fake response\nfinal line'
log = open(cwd / 'stdin.jsonl', 'a')
TRUSTED = '--permission-prompts=host' in sys.argv
TOOLS = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--tools=')), '')
TOOLS = [t for t in TOOLS.split(',') if t]
EFFORT = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--effort=')), 'medium')


def read():
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    log.write(line)
    log.flush()
    return json.loads(line)


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
            'effective': {},
            'applied': {'model': MODEL, 'effort': 'medium' if case == 'agent-effort-mismatch' else EFFORT},
            'sources': [{'source': 'policySettings'}] if case == 'managed-settings' else []})
    elif subtype == 'mcp_status':
        control(request_id, {'mcpServers': [{'name': 'm'}] if case == 'mcp' else []})
    elif subtype == 'get_context_usage':
        categories = [{'id': 'system_prompt', 'kind': 'used', 'tokens': 1500},
                      {'id': 'messages', 'kind': 'used', 'tokens': 10},
                      {'id': 'free_space', 'kind': 'free', 'tokens': 9000}]
        if case == 'context-tools' or TRUSTED:
            categories.append({'id': 'system_tools', 'kind': 'used', 'tokens': 1000})
        control(request_id, {'model': MODEL, 'categories': categories,
                             'memoryFiles': [{'path': 'CLAUDE.md'}] if case == 'memory' else [],
                             'mcpTools': [], 'agents': []})
    elif subtype == 'interrupt':
        (cwd / 'interrupted').touch()
        if case == 'cancel-ignored':
            return
        control(request_id, {'still_queued': []})
        if case == 'trusted-cancel':
            # A prompt raised after the interrupt must be denied.
            ask('q-late', 'Write', 't-late', {'file_path': str(cwd / 'late.txt'), 'content': 'x'})
        emit({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
              'terminal_reason': 'aborted_streaming', 'stop_reason': None,
              'total_cost_usd': 0.0, 'session_id': 'sid'})


def init():
    record = {'type': 'system', 'subtype': 'init', 'cwd': os.getcwd(), 'session_id': 'sid\u009b‮',
              'tools': (['Read'] if case == 'init-tools' else
                        TOOLS + ['Agent'] if case == 'trusted-init-tools' else TOOLS),
              'mcp_servers': [],
              'model': 'claude-opus-5-5' if case == 'init-model' else MODEL,
              'permissionMode': 'default', 'slash_commands': [],
              'apiKeySource': 'ANTHROPIC_API_KEY' if case == 'init-key' else 'none',
              'claude_code_version': VERSION, 'output_style': 'default',
              'agents': ['claude', 'Explore'], 'skills': [],
              'plugins': [{'name': 'cc-plugin-agents-md', 'path': 'builtin',
                           'source': 'cc-plugin-agents-md@builtin'}]}
    emit(record)


def use(tool_id, name, tool_input, parent=None):
    emit({'type': 'assistant', 'parent_tool_use_id': parent, 'message': {'content': [
        {'type': 'tool_use', 'id': tool_id, 'name': name, 'input': tool_input}]}})


def result(tool_id, content, error=False):
    emit({'type': 'user', 'parent_tool_use_id': None, 'message': {'role': 'user', 'content': [
        {'type': 'tool_result', 'tool_use_id': tool_id, 'content': content, 'is_error': error}]}})


def ask(request_id, name, tool_use_id, tool_input):
    """Send one host prompt and return whether the harness allowed it."""
    emit({'type': 'control_request', 'request_id': request_id, 'request': {
        'subtype': 'can_use_tool', 'tool_name': name, 'display_name': name, 'input': tool_input,
        'tool_use_id': tool_use_id, 'description': 'd',
        'permission_suggestions': [{'type': 'setMode', 'mode': 'acceptEdits', 'destination': 'session'}]}})
    while True:
        record = read()
        if record['type'] == 'control_response' and record['response']['request_id'] == request_id:
            answer = record['response']['response']
            with open(cwd / 'permissions.jsonl', 'a') as f:
                f.write(json.dumps({'request_id': request_id, **answer}) + '\n')
            return answer.get('behavior') == 'allow' and answer.get('updatedInput') == tool_input
        if record['type'] == 'control_request':
            respond(record['request_id'], record['request']['subtype'])


def write(tool_id, tool_input, request_id='q1', prompted_input=None):
    """An edit the runtime must prompt for; it runs only on a grant."""
    use(tool_id, 'Write', tool_input)
    if ask(request_id, 'Write', tool_id, prompted_input or tool_input):
        Path(tool_input['file_path']).write_text(tool_input['content'])
        result(tool_id, 'written')
    else:
        result(tool_id, 'denied', True)


def trusted_turn():
    made = {'file_path': str(cwd / 'made.txt'), 'content': 'made by fake'}
    if case == 'trusted-outside-tool':
        use('t1', 'Agent', {'prompt': 'x'})
        time.sleep(0.5)
        return
    if case == 'trusted-background':
        use('t1', 'Bash', {'command': 'sleep 60', 'run_in_background': True})
        time.sleep(0.5)
        return
    if case == 'trusted-repeat-id':
        use('t1', 'Read', {'file_path': str(cwd / 'user.txt')})
        use('t1', 'Read', {'file_path': str(cwd / 'user.txt')})
        time.sleep(0.5)
        return
    if case == 'trusted-subagent':
        use('t1', 'Read', {'file_path': str(cwd / 'user.txt')}, parent='t0')
        time.sleep(0.5)
        return
    if case == 'trusted-orphan-result':
        result('t9', 'x')
        time.sleep(0.5)
        return
    if case == 'trusted-hook':
        emit({'type': 'control_request', 'request_id': 'h1', 'request': {'subtype': 'hook_callback'}})
        time.sleep(0.5)
        return
    if case == 'trusted-cancel':
        use('t1', 'Bash', {'command': 'sleep 60'})
        return
    if case == 'agent-reviewer-write':
        # A read-only role is offered no Write; calling it is a violation.
        use('t1', 'Write', {'file_path': str(cwd / 'made.txt'), 'content': 'x'})
        time.sleep(0.5)
        return
    # The runtime allows a project read by itself: no prompt.
    use('t0', 'Read', {'file_path': str(cwd / 'user.txt')})
    result('t0', 'preserve dirty user content')
    if case == 'agent-reviewer':
        # A read outside the project prompts; a read-only ceiling denies it.
        outside = {'file_path': str(cwd.parent / 'outside.txt')}
        use('t1', 'Read', outside)
        result('t1', 'outside content' if ask('q1', 'Read', 't1', outside) else 'denied',
               False)
    elif case == 'trusted-mismatch':
        write('t1', made, prompted_input={**made, 'content': 'something else'})
    elif case == 'trusted-unknown-call':
        use('t1', 'Write', made)
        ask('q1', 'Write', 't-unknown', made)
        result('t1', 'denied', True)
    elif case == 'trusted-repeat':
        # A prompt after the call's result: no longer pending.
        write('t1', made)
        ask('q2', 'Write', 't1', made)
    elif case == 'trusted-double-prompt':
        # Two exact prompts while the call is still pending: only the first is granted.
        use('t1', 'Write', made)
        first = ask('q1', 'Write', 't1', made)
        ask('q2', 'Write', 't1', made)
        if first:
            Path(made['file_path']).write_text(made['content'])
        result('t1', 'written' if first else 'denied', not first)
    else:
        write('t1', made)
    emit({'type': 'assistant', 'message': {'model': MODEL, 'content': [
        {'type': 'text', 'text': 'fake response'}]}})
    if case == 'error-result':
        emit({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
              'stop_reason': None, 'result': 'SECRET_PROVIDER_ERROR', 'total_cost_usd': 0.001})
        return
    emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'stop_reason': 'end_turn',
          'result': FINAL, 'total_cost_usd': 0.0123, 'session_id': 'sid',
          'num_turns': 3, 'permission_denials': []})


def turn(text):
    (cwd / 'prompted').write_text(text)
    if case == 'eof-after-submit':
        sys.exit(0)
    if case == 'before-init':
        emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'x'}]}})
        return
    init()
    emit({'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed'}})
    if TRUSTED:
        trusted_turn()
        return
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
              'request': {'subtype': 'can_use_tool', 'tool_name': 'Bash', 'input': {}, 'tool_use_id': 't1'}})
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
          'result': FINAL, 'total_cost_usd': 0.0123, 'session_id': 'sid',
          'num_turns': 1, 'permission_denials': []})


while True:
    record = read()
    if record['type'] == 'control_request':
        respond(record['request_id'], record['request']['subtype'])
    elif record['type'] == 'user':
        turn(record['message']['content'])
