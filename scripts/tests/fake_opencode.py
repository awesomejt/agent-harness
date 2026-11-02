#!/usr/bin/env python3
"""Fake version/debug/ACP executable used only via disposable PATH in P2.2 tests."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

cwd = Path.cwd()
case = (cwd / 'case').read_text().strip()
config = json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])
assert 'ANTHROPIC_API_KEY' not in os.environ
assert os.environ['OPENCODE_DISABLE_PROJECT_CONFIG'] == 'true'
assert os.environ['HOME'] != str(cwd)
config['provider']['ah-litellm']['options']['apiKey'] = os.environ['AH_RUNTIME_API_KEY']
config.update(agent={}, mode={})
if '--version' in sys.argv:
    if case=='preflight-deadline': time.sleep(10)
    print('wrong' if case == 'version' else '1.18.30')
    sys.exit()
if 'debug' in sys.argv:
    if 'config' in sys.argv:
        if case == 'route':
            config['small_model'] = 'other/fixture'
        if case == 'widened':
            config['permission']['task'] = 'allow'
        print(json.dumps(config))
    else:
        rules = []
        for name in ['*','read','glob','grep','edit','apply_patch','bash','external_directory']:
            if name not in config['permission']: continue
            value=config['permission'][name]
            for pattern, action in (value.items() if isinstance(value, dict) else [('*', value)]):
                rules.append(dict(permission=name, pattern=pattern, action=action))
        if case == 'agent-reversed':
            rules[-2:]=reversed(rules[-2:])
        if case == 'agent-widened':
            rules.append(dict(permission='bash', pattern='*', action='allow'))
        print(json.dumps(dict(name='build', permission=rules)))
    sys.exit()
(cwd / 'launched').touch()
child = subprocess.Popen([sys.executable, '-c',
    'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(120)'],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(.05)
(cwd / 'pids.json').write_text(json.dumps([os.getpid(), child.pid]))


def send(value):
    print(json.dumps(value), flush=True)


def reply(identifier, result):
    send(dict(jsonrpc='2.0', id=identifier, result=result))


prompt_id = None
for line in sys.stdin:
    m = json.loads(line)
    method = m.get('method')
    if method == 'initialize':
        if case == 'before-prompt':
            continue
        reply(m['id'], dict(protocolVersion=1, agentCapabilities={}))
    elif method == 'session/new':
        reply(m['id'], dict(sessionId='test', configOptions=[dict(
            id='model', name='Model', type='select', currentValue='other' if case == 'session-model' else 'ah-litellm/fixture',
            options=[dict(value='ah-litellm/fixture', name='fixture')])]))
    elif method == 'session/prompt':
        prompt_id = m['id']
        (cwd / 'prompted').touch()
        if case in ['deadline', 'interrupt']:
            continue
        if case == 'deny-progress':
            for status in ['in_progress','failed']:
                send(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId='test',update=dict(sessionUpdate='tool_call_update',toolCallId='t',status=status))))
            reply(prompt_id,dict(stopReason='end_turn'))
            continue
        if case == 'eof':
            break
        if case == 'oversized':
            print('x' * 8_000_001, flush=True)
            continue
        if case in ['read','edit','execute','search','other','external','duplicate','deny','no-once','empty-id','kind-mismatch','unbound','unexpected-write','argument-mismatch']:
            kind = case if case in ['read','edit','execute','search','other'] else ('other' if case == 'external' else 'read')
            if case == 'kind-mismatch': kind='execute'
            raw = dict(filepath='/tmp/outside', parentDir='/tmp') if case == 'external' else dict(filePath='/tmp/example', command='true')
            options = [dict(optionId='once', name='ALLOW ALWAYS misleading title', kind='allow_once'),
                       dict(optionId='always', name='Once misleading title', kind='allow_always'),
                       dict(optionId='reject', name='Deny', kind='reject_once')]
            if case == 'duplicate':
                options.append(options[0])
            if case == 'no-once':
                options = options[1:]
            if case != 'unbound':
                send(dict(jsonrpc='2.0', method='session/update', params=dict(sessionId='test', update=dict(
                    sessionUpdate='tool_call',toolCallId='tool-1',title='Tool',kind='read' if kind=='other' or case=='kind-mismatch' else kind,rawInput=dict(filePath='/tmp/outside') if case=='external' else raw,status='pending'))))
            if case=='argument-mismatch': raw={**raw,'filePath':'/tmp/different'}
            send(dict(jsonrpc='2.0', id=100, method='session/request_permission', params=dict(
                sessionId='test', toolCall=dict(toolCallId='' if case == 'empty-id' else 'tool-1', title='Arbitrary', kind=kind, rawInput=raw), options=options)))
        else:
            send(dict(jsonrpc='2.0', method='session/update', params=dict(
                sessionId='wrong' if case == 'wrong-session' else 'test', update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='OK')))))
            reply(prompt_id, dict(stopReason='cancelled' if case == 'backend-cancelled' else 'end_turn'))
    elif m.get('id') == 100:
        (cwd / 'permission-result.json').write_text(json.dumps(m))
        if case == 'unexpected-write':
            send(dict(jsonrpc='2.0',id=200,method='fs/write_text_file',params=dict(sessionId='test',path='/tmp/ungranted-write',content='must not write')))
        else:
            reply(prompt_id, dict(stopReason='end_turn'))
