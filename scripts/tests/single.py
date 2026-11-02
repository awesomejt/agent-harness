#!/usr/bin/env python3
"""P2.2 public CLI fixtures; no model traffic. Build target/debug/ah first."""
import json
import os
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
        (base / 'ah.json').write_text(json.dumps(dict(version=1, mode='local-only',model='fixture',
            litellm=dict(api_base='http://127.0.0.1:9/v1',api_key_env='TEST_KEY'))))
        args = [str(BINARY),'single','--project',str(base),'--timeout-secs','4' if case == 'deadline' else '15']
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
        p = subprocess.Popen(args,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if case in ['interrupt','before-prompt']:
            marker = base / ('prompted' if case == 'interrupt' else 'pids.json')
            until = time.monotonic()+10
            while not marker.exists() and p.poll() is None and time.monotonic()<until:
                time.sleep(.02)
            assert marker.exists(), case
            p.send_signal(signal.SIGINT)
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
                assert option == ('once' if trusted and case in ['read','edit','execute','search','external','unexpected-write'] else 'reject'), (case,result)
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
        if expected == 4:
            assert 'uncertain' in err
        print('PASS',case,source,'trusted' if trusted else 'deny',flush=True)


for case in ['version','route','widened','agent-widened','agent-reversed','empty']:
    check(case,2)
check('text',2,source='missing')
for source in ['inline','file','stdin']:
    check('text',0,source=source)
for case in ['read','edit','execute','search','external','other','no-once','kind-mismatch','unbound']:
    check(case,0,trusted=True)
check('deny',0)
check('deny-progress',4)
for case in ['duplicate','empty-id','wrong-session','eof','oversized','deadline','interrupt','unexpected-write']:
    check(case,4,trusted=True)
check('before-prompt',3)
check('backend-cancelled',3)
check('session-model',1)
