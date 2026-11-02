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
sid = 'test\u009b\u202e\n\x1b' if case=='session-controls' else 'test'
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
    stdin=subprocess.DEVNULL, stdout=None if case=='held-pipes' else subprocess.DEVNULL, stderr=None if case=='held-pipes' else subprocess.DEVNULL)
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
        reply(m['id'], dict(sessionId=sid, configOptions=[dict(
            id='model', name='Model', type='select', currentValue='other' if case == 'session-model' else 'ah-litellm/fixture',
            options=[dict(value='ah-litellm/fixture', name='fixture')])]))
    elif method == 'session/prompt':
        prompt_id = m['id']
        (cwd / 'prompted').touch()
        if case in ['deadline', 'interrupt','cancel-ack','cancel-success','cancel-ack-only','cancel-deadline','cancel-permission']:
            continue
        if case == 'deny-progress':
            for status in ['in_progress','failed']:
                send(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=sid,update=dict(sessionUpdate='tool_call_update',toolCallId='t',status=status))))
            reply(prompt_id,dict(stopReason='end_turn'))
            continue
        if case in ['usage','usage-invalid-cost']:
            send(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=sid,update=dict(sessionUpdate='usage_update',used=123,size=32000,cost=dict(amount=0.25,currency='USD' if case=='usage' else 'SECRET_SENTINEL')))))
        if case == 'stderr-noise':
            os.write(2, b'SECRET_SENTINEL\xff' * 150000)
        if case == 'truncated-json':
            os.write(1, b'{"jsonrpc":')
            break
        if case == 'invalid-utf8':
            os.write(1, b'\xff\n')
            break
        if case == 'rpc-error':
            send(dict(jsonrpc='2.0',id=prompt_id,error=dict(code=-32603,message='SECRET_SENTINEL')))
            continue
        if case == 'known-failure':
            reply(prompt_id,dict(stopReason='max_tokens'))
            continue
        if case in ['blocked-stdout','blocked-stderr','progress']:
            for i in range(30000 if case == 'blocked-stderr' else 1):
                send(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=sid,update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='x' * (900000 if case=='blocked-stdout' else 1))))))
            if case == 'progress':
                (cwd/'streamed').touch()
                time.sleep(1)
            (cwd/'terminal').touch()
            reply(prompt_id,dict(stopReason='end_turn'))
            continue
        if case in ['eof','held-pipes']:
            break
        if case == 'oversized':
            print('x' * 8_000_001, flush=True)
            continue
        if case in ['read','edit','execute','search','other','external','duplicate','deny','no-once','empty-id','kind-mismatch','unbound','unexpected-write','argument-mismatch','empty-metadata','omitted-metadata']:
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
                send(dict(jsonrpc='2.0', method='session/update', params=dict(sessionId=sid, update=dict(
                    sessionUpdate='tool_call',toolCallId='tool-1',title='Tool',kind='read' if kind=='other' or case=='kind-mismatch' else kind,rawInput=dict(filePath='/tmp/outside') if case=='external' else raw,status='pending'))))
            if case=='argument-mismatch': raw={**raw,'filePath':'/tmp/different'}
            params=dict(sessionId=sid,toolCall=dict(toolCallId='' if case=='empty-id' else 'tool-1',title='Arbitrary',kind=kind,rawInput=raw),options=options)
            if case=='empty-metadata': params['toolCall']['rawInput']={}
            if case=='omitted-metadata': params['toolCall'].pop('rawInput')
            send(dict(jsonrpc='2.0',id=100,method='session/request_permission',params=params))
        else:
            send(dict(jsonrpc='2.0', method='session/update', params=dict(
                sessionId='wrong' if case == 'wrong-session' else sid, update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='OK')))))
            reply(prompt_id, dict(stopReason='cancelled' if case == 'backend-cancelled' else 'end_turn'))
    elif method == 'session/cancel':
        (cwd / 'cancelled').touch()
        if case in ['cancel-ack','cancel-deadline','cancel-success']:
            reply(prompt_id,dict(stopReason='end_turn' if case=='cancel-success' else 'cancelled'))
        elif case == 'cancel-permission':
            send(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=sid,update=dict(sessionUpdate='tool_call',toolCallId='tool-1',title='Tool',kind='read',rawInput=dict(filePath='/tmp/example'),status='pending'))))
            send(dict(jsonrpc='2.0',id=100,method='session/request_permission',params=dict(sessionId=sid,toolCall=dict(toolCallId='tool-1',title='Tool',kind='read',rawInput=dict(filePath='/tmp/example')),options=[dict(optionId='once',name='Once',kind='allow_once'),dict(optionId='reject',name='Deny',kind='reject_once')])) )
        elif case == 'cancel-ack-only':
            # A notification/ACK is not a trustworthy terminal response.
            send(dict(jsonrpc='2.0',method='session/update',params=dict(sessionId=sid,update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='cancel acknowledged')))))
    elif m.get('id') == 100:
        (cwd / 'permission-result.json').write_text(json.dumps(m))
        if case == 'unexpected-write':
            send(dict(jsonrpc='2.0',id=200,method='fs/write_text_file',params=dict(sessionId=sid,path='/tmp/ungranted-write',content='must not write')))
        else:
            reply(prompt_id, dict(stopReason='cancelled' if case=='cancel-permission' else 'end_turn'))
