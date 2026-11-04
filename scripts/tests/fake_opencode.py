#!/usr/bin/env python3
"""Fake OpenCode 2.2.5 version/debug/models/ACP executable, used only via a disposable PATH.

Emulates the surfaces recorded in docs/evidence/p3-7-opencode-2-baseline.md: a
sources list from `debug config`, per-agent rules from `debug agents`, `path`
tool arguments, a doubled external-directory request and a rejected permission
ending the turn with stopReason=cancelled.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

cwd = Path.cwd()
case = (cwd / 'case').read_text().strip()
sid = 'test\u009b‮\n\x1b' if case=='session-controls' else 'test'
config = json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])
if (cwd / 'track-runtime-home').exists():
    (cwd / 'runtime-home').write_text(os.environ['HOME'])
    with open(cwd / 'runtime-homes', 'a') as homes:
        homes.write(os.environ['HOME'] + '\n')
assert 'ANTHROPIC_API_KEY' not in os.environ
assert os.environ['OPENCODE_DISABLE_PROJECT_CONFIG'] == 'true'
assert os.environ['HOME'] != str(cwd)
if (cwd / 'track-config').exists():
    # P3.4 matrix: record each invocation's effective inputs for route assertions.
    with open(cwd / 'runtime-config.jsonl', 'a') as record:
        record.write(json.dumps(dict(args=sys.argv[1:], env=sorted(os.environ), config=config)) + '\n')
provider = config['model']['providerID']
native = provider == 'opencode'
assert config['policies'] == [dict(action='provider.use', resource='*', effect='deny'),
                              dict(action='provider.use', resource=provider, effect='allow')]
if native:
    assert config['providers'] == {}
    assert 'AH_RUNTIME_API_KEY' not in os.environ
    assert os.environ['OPENCODE_API_KEY'] == 'SECRET_SENTINEL'
    assert config['model'] == config['agents']['title']['model'] == dict(providerID='opencode', model='fixture')
    assert 'TEST_KEY' not in os.environ and 'LITELLM_API_KEY' not in os.environ
else:
    assert 'OPENCODE_API_KEY' not in os.environ
    assert config['providers']['ah-litellm']['settings']['apiKey'] == '{env:AH_RUNTIME_API_KEY}'
    assert os.environ['AH_RUNTIME_API_KEY']
target = provider + '/' + config['model']['model']
if sys.argv[1:] != ['acp']:
    # Inspection must never attach to the user's background service.
    assert '--standalone' in sys.argv, sys.argv
if '--version' in sys.argv:
    if case=='preflight-deadline': time.sleep(10)
    print('wrong' if case == 'version' else 'opencode v2.2.5')
    sys.exit()
if 'models' in sys.argv:
    assert native
    print('opencode/missing' if case == 'native-model-missing' else target)
    print('ah-litellm/fixture' if case == 'catalog-foreign' else 'opencode/other')
    sys.exit()
if 'debug' in sys.argv:
    if 'config' in sys.argv:
        info = json.loads(json.dumps(config))
        for item in info['providers'].values():
            item['settings']['apiKey'] = '***'
        if case == 'route':
            info['agents']['title']['model'] = dict(providerID=provider, model='other')
        if case == 'native-provider':
            info['providers']['ah-litellm'] = dict(package='aisdk:@ai-sdk/openai-compatible', settings=dict(baseURL='http://127.0.0.1:9/v1'))
        if case == 'native-enabled':
            info['policies'].append(dict(action='provider.use', resource='ah-litellm', effect='allow'))
        if case == 'native-agent':
            info['agents']['rogue'] = dict(model=dict(providerID='ah-litellm', model='fixture'))
        # Inherited helper/subagent/provider choices, identical for both routes.
        if case == 'inherit-agent':
            info['agents']['helper'] = dict(model=dict(providerID='other', model='fixture'))
        if case == 'inherit-subagent':
            info['agents']['explore'] = dict(mode='subagent', model=config['model'])
        if case == 'inherit-mode':
            info['agents']['plan'] = dict(model=dict(providerID='other', model='fixture'))
        if case == 'inherit-provider':
            info['providers']['other'] = dict(package='aisdk:@ai-sdk/openai-compatible', settings=dict(baseURL='http://127.0.0.1:9/v1'))
            info['policies'].append(dict(action='provider.use', resource='other', effect='allow'))
        if case == 'widened':
            info['permissions'].append(dict(action='subagent', resource='*', effect='allow'))
        config_dir = Path(os.environ['HOME']) / 'CONFIG' / 'opencode'
        config_dir.mkdir(parents=True, exist_ok=True)
        sources = [dict(type='directory', path=str(config_dir))]
        if case == 'project-source':
            sources.append(dict(type='document', path=str(cwd / 'opencode.json'), info=dict(model=dict(providerID='other', model='x'))))
        sources.append(dict(type='document', info=info))
        print(json.dumps(sources))
    else:
        builtin = [dict(action='*', resource='*', effect='allow'), dict(action='read', resource='*.env', effect='ask')]
        tail = [dict(action='browser', resource='*', effect='deny'), dict(action='skill', resource='browser', effect='deny')]
        profile = list(config['permissions'])
        if case == 'agent-reversed':
            profile[-2:] = reversed(profile[-2:])
        build = builtin + profile + tail
        if case == 'agent-widened':
            build.append(dict(action='shell', resource='*', effect='allow'))
        explore = builtin + [dict(action='shell', resource='*', effect='allow')] + list(config['permissions']) + tail
        if case == 'subagent-widened':
            explore.append(dict(action='edit', resource='*', effect='ask'))
        request = dict(settings={}, headers={}, body={})
        agents = [dict(id='build', name='Build', mode='primary', hidden=False, permissions=build, request=request),
                  dict(id='explore', name='Explore', mode='subagent', hidden=False, permissions=explore, request=request),
                  dict(id='title', name='Title', mode='primary', hidden=True, permissions=builtin + list(config['permissions']) + tail, request=request,
                       model=dict(id=config['model']['model'], providerID=provider))]
        if case == 'agent-model':
            agents[1]['model'] = dict(id='other', providerID=provider)
        # P4.3: configured agents append their own rules after the global ones.
        for name, item in config['agents'].items():
            if name == 'title':
                continue
            rules = builtin + profile + list(item['permissions']) + tail
            if case == 'named-widened':
                rules.append(dict(action='edit', resource='*', effect='ask'))
            agents.append(dict(id=name, name=name, description=item['description'], mode=item['mode'],
                               hidden=case == 'named-hidden', permissions=rules, request=request,
                               system=item['system'] + ('x' if case == 'named-system' else ''),
                               model=dict(id=item['model']['model'], providerID=item['model']['providerID'])))
        print(json.dumps(agents))
    sys.exit()
assert sys.argv[1:] == ['acp'], sys.argv
(cwd / 'launched').touch()
with open(cwd / 'launch-routes', 'a') as routes:
    routes.write(('native' if native else 'local') + '\n')
if case == 'home-cleanup-failure':
    (Path(os.environ['HOME']) / 'retained-state').write_text('runtime state')
    os.chmod(os.environ['HOME'], 0)
child = subprocess.Popen([sys.executable, '-c',
    'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(120)'],
    stdin=subprocess.DEVNULL, stdout=None if case=='held-pipes' else subprocess.DEVNULL, stderr=None if case=='held-pipes' else subprocess.DEVNULL)
time.sleep(.05)
(cwd / 'pids.json').write_text(json.dumps([os.getpid(), child.pid]))


def send(value):
    print(json.dumps(value), flush=True)


def reply(identifier, result):
    send(dict(jsonrpc='2.0', id=identifier, result=result))


def update(**fields):
    send(dict(jsonrpc='2.0', method='session/update', params=dict(sessionId=sid, update=fields)))


PERMISSION_CASES = ['read','edit','execute','search','other','external','triplicate','duplicate','deny','no-once','empty-id',
                    'kind-mismatch','unbound','unexpected-write','argument-mismatch','empty-metadata','omitted-metadata','worktree']
prompt_id = None
permission = None
requests = 0
for line in sys.stdin:
    m = json.loads(line)
    method = m.get('method')
    if method == 'initialize':
        if case == 'before-prompt':
            continue
        reply(m['id'], dict(protocolVersion=1, agentCapabilities={}))
    elif method == 'session/new':
        # 2.2.5 silently selects `build` when the default agent is unusable.
        default = 'build' if case == 'named-mode-fallback' else config.get('default_agent', 'build')
        reply(m['id'], dict(sessionId=sid, configOptions=[dict(
            id='model', name='Model', category='model', type='select', currentValue='other' if case == 'session-model' else target,
            options=[dict(value=target, name=target)]), dict(
            id='mode', name='Session Mode', category='mode', type='select', currentValue=default,
            options=[dict(value=default, name=default)])]))
    elif method == 'session/prompt':
        prompt_id = m['id']
        (cwd / 'prompted').touch()
        if case == 'rewrite-config':
            # P5.5: an agent edit to ah.json cannot change the pinned check.
            edited = json.loads((cwd / 'ah.json').read_text())
            edited['checks']['test']['argv'] = ['/usr/bin/false']
            (cwd / 'ah.json').write_text(json.dumps(edited))
        if case == 'remove-check':
            # P5.5: a pinned program that vanishes before the gate is an error.
            os.remove(json.loads((cwd / 'ah.json').read_text())['checks']['test']['argv'][0])
        if case in ['deadline', 'interrupt','cancel-ack','cancel-success','cancel-ack-only','cancel-deadline','cancel-permission','cancel-term']:
            continue
        if case in ['deny-progress', 'deny-completed', 'named-completed-edit', 'named-completed-read', 'named-completed-unknown']:
            # 2.2.5 reports in_progress while parsing arguments, then fails an unavailable tool.
            kind = 'edit' if case == 'named-completed-edit' else 'read'
            update(sessionUpdate='tool_call', toolCallId='t', **({} if case == 'named-completed-unknown' else dict(kind=kind)), status='pending', rawInput={})
            for status in ['in_progress', 'failed' if case == 'deny-progress' else 'completed']:
                fields = dict(sessionUpdate='tool_call_update', toolCallId='t', status=status, rawInput=dict(path='/tmp/example'))
                if case != 'named-completed-unknown':
                    fields['kind'] = kind
                update(**fields)
            reply(prompt_id,dict(stopReason='end_turn'))
            continue
        if case in ['usage','usage-invalid-cost']:
            update(sessionUpdate='usage_update',used=123,size=32000,cost=dict(amount=0.25,currency='USD' if case=='usage' else 'SECRET_SENTINEL'))
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
                update(sessionUpdate='agent_message_chunk',content=dict(type='text',text='x' * (900000 if case=='blocked-stdout' else 1)))
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
        if case in PERMISSION_CASES:
            kind = {'external': 'read', 'triplicate': 'read', 'worktree': 'other'}.get(case, case if case in ['read','edit','execute','search','other'] else 'read')
            if case == 'kind-mismatch': kind='execute'
            raw = {'read': dict(path='/tmp/example'), 'search': dict(pattern='*.py'), 'other': dict(path='/tmp/example'),
                   'edit': dict(path='/tmp/example', oldString='a', newString='b'),
                   'execute': dict(command='true', description='Run', cwd=str(cwd))}[kind if case != 'worktree' else 'other']
            if case in ['external', 'triplicate']: raw = dict(path='/tmp/outside')
            if case == 'worktree': raw = dict(directory='/tmp/worktree')
            options = [dict(optionId='once', name='ALLOW ALWAYS misleading title', kind='allow_once'),
                       dict(optionId='always', name='Once misleading title', kind='allow_always'),
                       dict(optionId='reject', name='Deny', kind='reject_once')]
            if case == 'duplicate':
                options.append(options[0])
            if case == 'no-once':
                options = options[1:]
            if case != 'unbound':
                update(sessionUpdate='tool_call', toolCallId='tool-1', title='Tool', kind=kind, status='pending', rawInput={})
                announced = 'read' if case in ['other', 'kind-mismatch'] else kind
                update(sessionUpdate='tool_call_update', toolCallId='tool-1', title='Tool', kind=announced, status='in_progress', rawInput=raw)
            if case=='argument-mismatch': raw={**raw,'path':'/tmp/different'}
            params=dict(sessionId=sid,toolCall=dict(toolCallId='' if case=='empty-id' else 'tool-1',title='Arbitrary',kind=kind,status='pending',rawInput=raw),options=options)
            if case=='empty-metadata': params['toolCall']['rawInput']={}
            if case=='omitted-metadata': params['toolCall'].pop('rawInput')
            permission = params
            requests = 1
            send(dict(jsonrpc='2.0',id=100,method='session/request_permission',params=params))
        else:
            update(sessionUpdate='agent_message_chunk',content=dict(type='text',text='OK'))
            if case == 'wrong-session':
                send(dict(jsonrpc='2.0', method='session/update', params=dict(sessionId='wrong', update=dict(sessionUpdate='agent_message_chunk',content=dict(type='text',text='OK')))))
            reply(prompt_id, dict(stopReason='cancelled' if case == 'backend-cancelled' else 'end_turn'))
    elif method == 'session/cancel':
        (cwd / 'cancelled').touch()
        if case in ['cancel-ack','cancel-deadline','cancel-success','cancel-term']:
            reply(prompt_id,dict(stopReason='end_turn' if case=='cancel-success' else 'cancelled'))
        elif case == 'cancel-permission':
            update(sessionUpdate='tool_call',toolCallId='tool-1',title='Tool',kind='read',status='pending',rawInput={})
            update(sessionUpdate='tool_call_update',toolCallId='tool-1',title='Tool',kind='read',status='in_progress',rawInput=dict(path='/tmp/example'))
            send(dict(jsonrpc='2.0',id=100,method='session/request_permission',params=dict(sessionId=sid,toolCall=dict(toolCallId='tool-1',title='Tool',kind='read',status='pending',rawInput=dict(path='/tmp/example')),options=[dict(optionId='once',name='Once',kind='allow_once'),dict(optionId='reject',name='Deny',kind='reject_once')])) )
        elif case == 'cancel-ack-only':
            # A notification/ACK is not a trustworthy terminal response.
            update(sessionUpdate='agent_message_chunk',content=dict(type='text',text='cancel acknowledged'))
    elif m.get('id') in (100, 101, 102):
        with open(cwd / 'permission-results.jsonl', 'a') as results:
            results.write(json.dumps(m) + '\n')
        (cwd / 'permission-result.json').write_text(json.dumps(m))
        selected = m.get('result', {}).get('outcome', {}).get('optionId')
        if case == 'unexpected-write':
            send(dict(jsonrpc='2.0',id=200,method='fs/write_text_file',params=dict(sessionId=sid,path='/tmp/ungranted-write',content='must not write')))
        elif selected == 'once' and ((case == 'external' and requests < 2) or (case == 'triplicate' and requests < 3)):
            # External-directory and tool checks raise byte-identical requests.
            send(dict(jsonrpc='2.0',id=100+requests,method='session/request_permission',params=permission))
            requests += 1
        else:
            # 2.2.5 ends the turn with stopReason=cancelled after a rejected permission.
            reply(prompt_id, dict(stopReason='cancelled' if case=='cancel-permission' or selected != 'once' else 'end_turn'))
