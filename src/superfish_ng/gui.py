# SPDX-License-Identifier: Apache-2.0
"""Single-user loopback UI; no remote service or web framework dependency."""
import hmac
import json
import mimetypes
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webbrowser

from .config import keys
from .geometry import linearize_profile
from .jobs import JobManager, read_job
from .project import Project, load_document

ASSETS=Path(__file__).with_name('web')


def create_server(workspace,port=0):
    manager=JobManager(workspace)
    token=secrets.token_urlsafe(32)
    render_lock=threading.Lock()
    plot_cache=manager.root/'.plot-cache'
    plot_cache.mkdir(exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def reply(self,data,status=200,content_type='application/json; charset=utf-8'):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass

        def valid_host(self):
            return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():return self.reply({'error':'invalid host'},403)
            name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(self.path)
            if name is None:return self.reply({'error':'not found'},404)
            self.reply((ASSETS/name).read_bytes(),content_type=mimetypes.guess_type(name)[0]+'; charset=utf-8')

        def do_POST(self):
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if (not self.valid_host() or self.headers.get('Origin',origin)!=origin
                    or not hmac.compare_digest(self.headers.get('X-NG-Token',''),token)):
                return self.reply({'error':'local session required; reopen the launch URL'},403)
            if self.path!='/api':return self.reply({'error':'not found'},404)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4*1024*1024:raise ValueError('request must be between 1 byte and 4 MiB')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):raise ValueError('request must be an object')
                action=data.get('action')
                allowed={'normalize':['document'],'assemble':['case','sections','reflect_full'],
                         'start':['document'],'jobs':[],'cancel':['id'],'result':['id'],
                         'plot':['id','mode','probe_z_m','mesh'],'log':['id']}
                if action not in allowed:raise ValueError('unknown operation')
                keys(data,['action',*allowed[action]],['action'],'request')
                if action=='normalize':
                    project=load_document(data['document']) if isinstance(data['document'],str) else Project.from_dict(data['document'])
                elif action=='assemble':
                    project=Project.from_sections(data['case'],data['sections'],reflect_full=data.get('reflect_full',False))
                elif action=='start':
                    project=Project.from_dict(data['document'])
                    return self.reply({'id':manager.start(project)})
                elif action=='jobs':return self.reply(manager.list())
                elif action=='cancel':return self.reply(manager.cancel(data['id']))
                else:
                    directory=manager.directory(data['id'])
                    if action=='log':return self.reply({'text':(directory/'log.txt').read_text(errors='replace')[-32000:]})
                    state=read_job(directory)
                    if state['status']!='complete':raise ValueError('run is not complete')
                    if action=='result':
                        return self.reply({'project':Project.load(directory/'project.json').to_dict(),
                                           'result':json.loads((directory/'solution/results.json').read_text()),'state':state})
                    mode=data.get('mode',1)
                    if type(mode) is not int or mode<1:raise ValueError('mode must be a positive integer')
                    if type(data.get('mesh',False)) is not bool:raise ValueError('mesh must be boolean')
                    # Serialize plotting processes to bound memory and avoid pyplot shared state.
                    with render_lock:
                        import hashlib
                        tag=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:20]
                        image=directory/f'plot-{tag}.png'
                        if not image.exists():
                            args=[sys.executable,'-m','superfish_ng','plot',str(directory/'solution'),
                                  '--mode',str(mode),'--out',str(image)]
                            if data.get('probe_z_m') is not None:args+=['--probe-z-m',str(data['probe_z_m'])]
                            if data.get('mesh'):args+=['--mesh']
                            import os
                            done=subprocess.run(args,capture_output=True,text=True,timeout=120,
                                                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','MPLCONFIGDIR':str(plot_cache)})
                            if done.returncode:raise ValueError(done.stderr.strip() or 'plot failed')
                        return self.reply(image.read_bytes(),content_type='image/png')
                return self.reply({'project':project.to_dict(),'outline_zr_m':[list(p) for p in linearize_profile(project.case)]})
            except (ValueError,KeyError,TypeError,OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
                self.reply({'error':str(exc)},400)

    try:server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    except Exception:manager.close();raise
    server.manager=manager
    server.launch_url=f'http://127.0.0.1:{server.server_port}/#{token}'
    return server


def serve(workspace,port=0,open_browser=True):
    server=create_server(workspace,port)
    print(f'Superfish-NG GUI: {server.launch_url}',flush=True)
    print(f'Workspace: {server.manager.root}',flush=True)
    if open_browser:webbrowser.open(server.launch_url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();server.manager.close()
