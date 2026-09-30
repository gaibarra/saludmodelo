"""Run browser acceptance against exclusively owned ephemeral PostgreSQL and sockets.
No reuse of existing servers; no commands that stop unrelated processes.
"""
import json
import base64
import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from document_fixtures import signatures,office

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / 'backend/.venv/bin/python'
PG_BIN = Path(os.environ.get('TEST_PG_BIN', '/usr/lib/postgresql/16/bin'))

def reserve():
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(32)
    return sock

with tempfile.TemporaryDirectory(prefix='salud-e2e-') as folder:
    work=Path(folder);(work/'socket').mkdir(mode=0o700)
    backend_socket=reserve();frontend_socket=reserve()
    backend_port=backend_socket.getsockname()[1];frontend_port=frontend_socket.getsockname()[1]
    env={**os.environ,'MFA_REQUIRE_PRIVILEGED':'0','MFA_ENCRYPTION_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),'EXCEPTIONAL_MFA_RECOVERY_ENABLED':'1','AI_EXTERNAL_ENABLED':'0','OPENAI_API_KEY':'','DEEPSEEK_API_KEY':'','AI_MODELS_JSON':'{}','E2E_WORKDIR':str(work),'DJANGO_SETTINGS_MODULE':'e2e_settings','PYTHONPATH':str(ROOT/'tests')+os.pathsep+str(ROOT/'backend'),'DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'DEBUG':'1','PGHOST':str(work/'socket'),'PGPORT':'5432','PGDATABASE':'salud_e2e','PGUSER':os.environ.get('USER','gaibarra'),'PGPASSWORD':'','ALLOWED_HOSTS':'127.0.0.1,localhost','CSRF_TRUSTED_ORIGINS':f'http://127.0.0.1:{frontend_port}','PRIVATE_STORAGE':str(work/'private'),'BACKEND_URL':f'http://127.0.0.1:{backend_port}','E2E_BASE_URL':f'http://127.0.0.1:{frontend_port}','E2E_PASSWORD':'T!'+secrets.token_urlsafe(24),'E2E_START':str(date.today()-timedelta(days=2)),'E2E_END':str(date.today()+timedelta(days=30)),'E2E_BACKEND_FD':str(backend_socket.fileno()),'E2E_FRONTEND_FD':str(frontend_socket.fileno()),'E2E_FRONTEND_PORT':str(frontend_port),'NEXT_TELEMETRY_DISABLED':'1'}
    env['DOCUMENT_SIGNATURES']=signatures(work/'signatures')
    (work/'document.docx').write_bytes(office())
    env['E2E_DOCUMENT']=str(work/'document.docx')
    children=[];pg_started=False
    try:
        subprocess.run([str(PG_BIN/'initdb'),'-D',str(work/'pg'),'-A','trust','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([str(PG_BIN/'pg_ctl'),'-D',str(work/'pg'),'-l',str(work/'pg.log'),'-o',f'-k {work}/socket -h ""','start'],check=True,stdout=subprocess.DEVNULL)
        pg_started=True
        subprocess.run([str(PG_BIN/'createdb'),'salud_e2e'],env=env,check=True)
        subprocess.run([str(PYTHON),'backend/manage.py','migrate','--noinput'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
        subprocess.run([str(PYTHON),'tests/seed_browser.py'],cwd=ROOT,env=env,check=True)
        with (work/'backend.log').open('w') as back_log,(work/'frontend.log').open('w') as front_log,(work/'extractor.log').open('w') as extract_log:
            backend=subprocess.Popen([str(PYTHON),'tests/serve_browser_backend.py'],cwd=ROOT,env=env,stdout=back_log,stderr=subprocess.STDOUT,pass_fds=(backend_socket.fileno(),),start_new_session=True);children.append(backend)
            frontend=subprocess.Popen(['node','e2e/server.cjs'],cwd=ROOT/'frontend',env=env,stdout=front_log,stderr=subprocess.STDOUT,pass_fds=(frontend_socket.fileno(),),start_new_session=True);children.append(frontend)
            extractor=subprocess.Popen([str(PYTHON),'tests/serve_browser_extractor.py'],cwd=ROOT,env=env,stdout=extract_log,stderr=subprocess.STDOUT,start_new_session=True);children.append(extractor)
            backend_socket.close();frontend_socket.close()
            deadline=time.monotonic()+90
            while True:
                if any(child.poll() is not None for child in children): raise RuntimeError('Owned test server stopped before readiness')
                try:
                    with urllib.request.urlopen(env['E2E_BASE_URL'],timeout=2) as response:
                        if response.status==200:break
                except (OSError,TimeoutError):pass
                if time.monotonic()>deadline:raise RuntimeError('Owned test servers did not become ready')
                time.sleep(.5)
            result=subprocess.run(['node','node_modules/@playwright/test/cli.js','test']+(['--grep',os.environ['E2E_TEST_PATTERN']] if os.environ.get('E2E_TEST_PATTERN') else []),cwd=ROOT/'frontend',env=env)
            if result.returncode:raise RuntimeError('Browser tests failed; inspect frontend/test-results')
    except Exception:
        for name in ['backend.log','frontend.log','extractor.log']:
            path=work/name
            if path.exists():print(f'--- {name} ---\n'+path.read_text()[-10000:],file=sys.stderr)
        raise
    finally:
        for child in reversed(children):
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        backend_socket.close();frontend_socket.close()
        if pg_started:subprocess.run([str(PG_BIN/'pg_ctl'),'-D',str(work/'pg'),'stop','-m','fast'],stdout=subprocess.DEVNULL,check=True)
