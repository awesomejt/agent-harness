#!/usr/bin/env python3
"""P2.2 public CLI fixtures; no model traffic. Build target/debug/ah first."""
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'target/debug/ah'
FAKE = ROOT / 'scripts/tests/fake_opencode.py'


def check(case, expected, trusted=False, source='inline'):
    with tempfile.TemporaryDirectory(prefix='ah-single-test-') as d:
        base = Path(d).resolve()
        (base / 'opencode').symlink_to(FAKE)
        (base / 'case').write_text(case)
        for name in ['claude','codex','grok','gemini','pi']:
            (base/name).write_text('#!/bin/sh\ntouch cloud-native-launched\nexit 99\n')
            (base/name).chmod(0o755)
        (base / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only',model='fixture',
            litellm=dict(api_base='http://127.0.0.1:9/v1',api_key_env='TEST_KEY'))))
        args = [str(BINARY),'single','--project',str(base),'--timeout-secs','4' if case in ['deadline','cancel-deadline'] else ('1' if case=='preflight-deadline' else '15')]
        if trusted:
            args += ['--permissions','trusted']
        text = 'Task' if case != 'empty' else ' '
        stdin = None
        if source == 'inline':
            args += [text]
        elif source == 'file':
            (base / 'prompt.txt').write_text(text)
            args += ['--prompt-file',str(base/'prompt.txt')]
        elif source == 'stdin':
            args += ['--prompt-file','-']
            stdin = text
        elif source == 'missing':
            args += ['--prompt-file',str(base/'missing')]
        env = {**os.environ,'PATH':str(base)+':'+os.environ['PATH'],'TEST_KEY':'SECRET_SENTINEL',
               'ANTHROPIC_API_KEY':'poison','OPENCODE_CONFIG_CONTENT':'poison'}
        if case in ['relative-path','empty-path']:
            (base/'bin').mkdir()
            (base/'opencode').rename(base/'bin/opencode')
            (base/'opencode').write_text('#!/bin/sh\ntouch rogue\nexit 1\n')
            (base/'opencode').chmod(0o755)
            env['PATH']=('.' if case=='relative-path' else '')+':'+str(base/'bin')+':'+os.environ['PATH']
        pipe_read = pipe_write = None
        if case == 'blocked-stderr':
            pipe_read,pipe_write=os.pipe()
            os.set_blocking(pipe_write,False)
            try:
                while True: os.write(pipe_write,b'F'*4096)
            except BlockingIOError:
                pass
            os.set_blocking(pipe_write,True)
        p = subprocess.Popen(args,cwd=base if case in ['relative-path','empty-path'] else None,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=pipe_write if pipe_write is not None else subprocess.PIPE,text=True)
        if pipe_write is not None:
            os.close(pipe_write)
            p.stderr=os.fdopen(pipe_read,'r')
        if case in ['interrupt','before-prompt','cancel-ack','cancel-success','cancel-ack-only','cancel-permission']:
            marker = base / ('prompted' if case != 'before-prompt' else 'pids.json')
            until = time.monotonic()+10
            while not marker.exists() and p.poll() is None and time.monotonic()<until:
                time.sleep(.02)
            assert marker.exists(), case
            p.send_signal(signal.SIGINT)
        if case == 'blocked-stdout':
            # Deliberately never read one full pipe until the process exits.
            started=time.monotonic()
            p.wait(timeout=20)
            assert time.monotonic()-started < 15,case
        if case == 'blocked-stderr':
            # The pipe is already full before launch; >64 sampled events must
            # overflow the queue. Release it only after the backend terminal.
            until=time.monotonic()+10
            while not (base/'terminal').exists() and p.poll() is None and time.monotonic()<until:
                time.sleep(.01)
            assert (base/'terminal').exists(),case
            time.sleep(.1)
        if case == 'progress':
            # A diagnostic must arrive before the backend terminal marker.
            while True:
                line=p.stderr.readline()
                assert line,(case,p.poll())
                if 'assistant activity' in line: break
            assert 'run=' in line and p.poll() is None and not (base/'terminal').exists(),line
        out,err = p.communicate(stdin, timeout=30)
        assert p.returncode == expected, (case,p.returncode,err)
        assert 'SECRET_SENTINEL' not in out+err, case
        if (base/'pids.json').exists():
            for pid in json.loads((base/'pids.json').read_text()):
                status = subprocess.run(['/bin/ps','-o','stat=','-p',str(pid)],capture_output=True,text=True).stdout.strip()
                assert not status or status.startswith('Z'), (case,pid,status)
        if (base/'permission-result.json').exists() and case not in ['duplicate','empty-id']:
            result=json.loads((base/'permission-result.json').read_text())
            if case not in ['duplicate','empty-id']:
                option = result['result']['outcome'].get('optionId')
                assert option == ('once' if trusted and case in ['read','edit','execute','search','external','unexpected-write','empty-metadata','omitted-metadata'] else 'reject'), (case,result)
        assert not (base/'rogue').exists()
        assert not (base/'cloud-native-launched').exists(),case
        if expected == 2:
            assert not (base/'launched').exists()
            assert not (base/'opencode.json').exists()
        for name in ['opencode.json','.ah-opencode-owner.json']:
            if (base/name).exists(): assert 'SECRET_SENTINEL' not in (base/name).read_text()
        if expected == 0 and case == 'text' and source == 'inline':
            snapshots={name:((base/name).read_bytes(),(base/name).stat().st_mtime_ns) for name in ['opencode.json','.ah-opencode-owner.json','.ah-opencode.lock']}
            again=subprocess.run(args+['--no-sync'],env=env,capture_output=True,text=True,timeout=30)
            assert again.returncode==0,again.stderr
            assert snapshots=={name:((base/name).read_bytes(),(base/name).stat().st_mtime_ns) for name in snapshots}
        if (base/'prompted').exists() and case != 'blocked-stderr':
            assert 'attempt=1' in err and 'usage=' in err and 'outcome=' in err, (case,err)
        if case in ['cancel-ack','cancel-success','cancel-ack-only','cancel-deadline','cancel-permission']:
            assert (base/'cancelled').exists(),case
        if case == 'session-controls':
            assert not any(c in err for c in ['\u009b','\u202e','\x1b']),repr(err)
            assert r'\\u{9b}' in err and r'\\u{202e}' in err,err
        if case == 'blocked-stderr':
            omitted=re.search(r'diagnostics_omitted=(\d+)',err)
            assert omitted and int(omitted[1]) > 0,err[-1000:]
        if case.startswith('usage'):
            assert 'source=OpenCode ACP session/update; context_used=123 tokens; context_capacity=32000 tokens; turn_tokens=unknown' in err,err
            assert ('session_cost=0.25 USD' if case=='usage' else 'session_cost=unknown') in err,err
        elif (base/'prompted').exists() and case != 'blocked-stderr':
            assert 'usage=unknown' in err,err
        if case == 'stderr-noise':
            assert 'stderr_bytes=1048577' in err,err
        if expected == 4:
            assert 'uncertain' in err
        print('PASS',case,source,'trusted' if trusted else 'deny',flush=True)


for case in ['version','route','widened','agent-widened','agent-reversed','empty']:
    check(case,2)
check('text',2,source='missing')
for source in ['inline','file','stdin']:
    check('text',0,source=source)
for case in ['read','edit','execute','search','external','other','no-once','kind-mismatch','unbound','argument-mismatch','empty-metadata','omitted-metadata']:
    check(case,0,trusted=True)
check('deny',0)
check('deny-progress',4)
for case in ['duplicate','empty-id','wrong-session','eof','oversized','deadline','interrupt','unexpected-write']:
    check(case,4,trusted=True)
check('before-prompt',3)
check('backend-cancelled',3)
check('session-model',1)
check('relative-path',0)
check('empty-path',0)
check('preflight-deadline',3)

for case in ['stderr-noise','progress','blocked-stderr']:
    check(case,0)
check('blocked-stdout',1)
check('known-failure',1)
for case in ['invalid-utf8','truncated-json','rpc-error','cancel-ack-only']:
    check(case,4)
check('cancel-ack',3)
check('cancel-deadline',3)
check('cancel-success',0)
check('cancel-permission',3,trusted=True)
check('usage',0)
check('usage-invalid-cost',0)
check('held-pipes',4)
check('session-controls',0)
