#!/usr/bin/env python3
"""P2.2 installed OpenCode edit/test check. Default uses a local model stub.

--live forwards only the explicitly selected alias to the existing LiteLLM host;
credentials and raw requests/responses remain in memory, never printed.
"""
import argparse
import contextlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import signal
import tempfile
import threading
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length','0'))
            assert self.path == '/v1/chat/completions' and 0 < size <= 2_000_000
            raw = self.rfile.read(size)
            body = json.loads(raw)
            assert body['model'] == self.server.alias
            tools = [t['function']['name'] for t in body.get('tools',[])]
            assert set(tools) <= {'read','glob','grep','edit','write','apply_patch','bash','invalid'}
            self.server.records.append(dict(model=body['model'],tools=tools))
            if self.server.upstream:
                req = urllib.request.Request(self.server.upstream+'/chat/completions',data=raw,
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+self.server.key})
                with urllib.request.urlopen(req,timeout=150) as response:
                    self.send_response(response.status)
                    self.send_header('Content-Type',response.headers.get('Content-Type','text/event-stream'))
                    self.end_headers()
                    while chunk := response.read1(8192):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                return
            self.send_response(200)
            self.send_header('Content-Type','text/event-stream')
            self.end_headers()
            def event(delta,finish=None):
                packet=dict(id='fixture',object='chat.completion.chunk',model=self.server.alias,
                            choices=[dict(index=0,delta=delta,finish_reason=finish)])
                self.wfile.write(('data: '+json.dumps(packet)+'\n\n').encode()); self.wfile.flush()
            if tools:
                stage=self.server.stage
                self.server.stage+=1
                calls=[('read',dict(filePath=str(self.server.outside/'outside.txt'))),
                       ('read',dict(filePath=str(self.server.cwd/'calc.py'))),
                       ('edit',dict(filePath=str(self.server.cwd/'calc.py'),oldString='return a - b',newString='return a + b')),
                       ('bash',dict(command='cat '+str(self.server.outside/'outside.txt')+' && python3 test_calc.py && touch verified',description='Run arithmetic test'))]
                if self.server.cancel and stage == len(calls):
                    event(dict(role='assistant',content='Waiting for cancellation'))
                    self.server.waiting.set()
                    self.server.release.wait(15)
                if stage < len(calls):
                    name,arguments=calls[stage]
                    assert name in tools
                    event(dict(role='assistant',tool_calls=[dict(index=0,id='call-'+str(stage),type='function',function=dict(name=name,arguments=json.dumps(arguments)))]))
                    event({},'tool_calls')
                else:
                    event(dict(role='assistant',content='Fixed and tested.')); event({},'stop')
            else:
                event(dict(role='assistant',content='OK')); event({},'stop')
            self.wfile.write(b'data: [DONE]\n\n')
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception:
            self.server.failed=True
            self.send_error(502,'test request failed')


@contextlib.contextmanager
def server(args):
    s=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    s.daemon_threads=True
    s.alias=args.model if args.live else 'fixture'
    s.upstream=args.endpoint if args.live else None
    s.key=os.environ[args.key_env] if args.live else 'unused'
    s.records=[];s.failed=False;s.stage=0
    s.cancel=args.cancel; s.waiting=threading.Event(); s.release=threading.Event()
    t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    try:
        yield s,'http://127.0.0.1:'+str(s.server_port)+'/v1'
    finally:
        s.release.set()
        s.shutdown();s.server_close();t.join(timeout=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--cancel',action='store_true',help='cancel the installed runtime after the deterministic edit/test')
    parser.add_argument('--endpoint',default='http://litellm:4000/v1')
    parser.add_argument('--model',default='macmini-qwen3-coder-30b')
    parser.add_argument('--key-env',default='LITELLM_API_KEY')
    parser.add_argument('--binary',type=Path,default=ROOT/'target/debug/ah',help='Path to the ah binary to test')
    parser.add_argument('--timeout-secs',type=int,default=300)
    parser.add_argument('--group',help='select the proxy model group through this harness litellm.groups name (P3.3)')
    args=parser.parse_args()
    args.binary=args.binary.expanduser().resolve()
    if not args.binary.is_file() or not os.access(args.binary,os.X_OK):
        parser.error(f'not an executable ah binary: {args.binary}')
    assert not (args.live and args.cancel),"cancellation fixture uses the local deterministic model only"
    with server(args) as (s,endpoint),tempfile.TemporaryDirectory(prefix='ah-single-runtime-') as d, tempfile.TemporaryDirectory(prefix='ah-outside-') as outside:
        cwd=Path(d).resolve();s.cwd=cwd;s.outside=Path(outside).resolve()
        (s.outside/'outside.txt').write_text('OUTSIDE_READ_OK')
        subprocess.run(['git','init','-q',str(cwd)],check=True)
        litellm=dict(api_base=endpoint,api_key_env='TEST_KEY')
        if args.group:
            # The wire model must stay the proxy group; the harness name never leaves ah.
            litellm['groups']={args.group:s.alias,'unselected-group':'unselected-proxy-group'}
        (cwd/'ah.json').write_text(json.dumps(dict(version=1,mode='local-only',
            model='group:'+args.group if args.group else s.alias,litellm=litellm)))
        (cwd/'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (cwd/'test_calc.py').write_text('from calc import add\nassert add(2, 3) == 5\nprint("PASS arithmetic")\n')
        prompt='Fix add in calc.py so it adds correctly. Read calc.py, edit it with the edit tool, then use bash to run python3 test_calc.py and touch verified only if it passes. Do not change test_calc.py. Do not use subagents. Reply briefly.'
        p=subprocess.Popen([str(args.binary),'single',prompt,'--project',str(cwd),'--permissions','trusted','--timeout-secs',str(args.timeout_secs)],
            env={**os.environ,'TEST_KEY':s.key},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if args.cancel:
            assert s.waiting.wait(60),'runtime did not reach post-edit/test cancellation point'
            p.send_signal(signal.SIGINT)
        stdout,stderr=p.communicate(timeout=args.timeout_secs+20)
        print('CLI exit:',p.returncode,'; stderr:',stderr.strip(),flush=True)
        print('Wire:',json.dumps(s.records),flush=True)
        print('Observed project effects:',json.dumps(dict(edited='return a + b' in (cwd/'calc.py').read_text(), verified=(cwd/'verified').exists())),flush=True)
        assert p.returncode == (3 if args.cancel else 0) and not s.failed
        assert not args.group or f'ah-litellm/{s.alias} (group {args.group})' in stderr
        assert s.records and all(r['model'] == s.alias for r in s.records)
        assert 'return a + b' in (cwd/'calc.py').read_text()
        assert (cwd/'verified').exists()
        verify=subprocess.run(['python3','test_calc.py'],cwd=cwd,capture_output=True,text=True)
        assert verify.returncode == 0
        print(('PASS confirmed cancellation after ' if args.cancel else 'PASS ')+ 'actual project edit and independent arithmetic test; '+('live LiteLLM' if args.live else 'local deterministic model stub')+(f'; harness group {args.group}' if args.group else ''),flush=True)


if __name__=='__main__':
    main()
