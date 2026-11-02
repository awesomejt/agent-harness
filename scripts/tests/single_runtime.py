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
    t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    try:
        yield s,'http://127.0.0.1:'+str(s.server_port)+'/v1'
    finally:
        s.shutdown();s.server_close();t.join(timeout=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--endpoint',default='http://litellm:4000/v1')
    parser.add_argument('--model',default='macmini-qwen3-coder-30b')
    parser.add_argument('--key-env',default='LITELLM_API_KEY')
    parser.add_argument('--timeout-secs',type=int,default=300)
    args=parser.parse_args()
    with server(args) as (s,endpoint),tempfile.TemporaryDirectory(prefix='ah-single-runtime-') as d, tempfile.TemporaryDirectory(prefix='ah-outside-') as outside:
        cwd=Path(d).resolve();s.cwd=cwd;s.outside=Path(outside).resolve()
        (s.outside/'outside.txt').write_text('OUTSIDE_READ_OK')
        subprocess.run(['git','init','-q',str(cwd)],check=True)
        (cwd/'ah.json').write_text(json.dumps(dict(version=1,mode='local-only',model=s.alias,
            litellm=dict(api_base=endpoint,api_key_env='TEST_KEY'))))
        (cwd/'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (cwd/'test_calc.py').write_text('from calc import add\nassert add(2, 3) == 5\nprint("PASS arithmetic")\n')
        prompt='Fix add in calc.py so it adds correctly. Read calc.py, edit it with the edit tool, then use bash to run python3 test_calc.py and touch verified only if it passes. Do not change test_calc.py. Do not use subagents. Reply briefly.'
        p=subprocess.run([str(ROOT/'target/debug/ah'),'single',prompt,'--project',str(cwd),'--permissions','trusted','--timeout-secs',str(args.timeout_secs)],
            env={**os.environ,'TEST_KEY':s.key},capture_output=True,text=True,timeout=args.timeout_secs+20)
        print('CLI exit:',p.returncode,'; stderr:',p.stderr.strip(),flush=True)
        print('Wire:',json.dumps(s.records),flush=True)
        print('Observed project effects:',json.dumps(dict(edited='return a + b' in (cwd/'calc.py').read_text(), verified=(cwd/'verified').exists())),flush=True)
        assert p.returncode == 0 and not s.failed
        assert 'return a + b' in (cwd/'calc.py').read_text()
        assert (cwd/'verified').exists()
        verify=subprocess.run(['python3','test_calc.py'],cwd=cwd,capture_output=True,text=True)
        assert verify.returncode == 0
        print('PASS actual project edit and independent arithmetic test; '+('live LiteLLM' if args.live else 'local deterministic model stub'),flush=True)


if __name__=='__main__':
    main()
