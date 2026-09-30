import os
import socket
import sys
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from django.core.wsgi import get_wsgi_application

class Server(ThreadingMixIn, WSGIServer):
    daemon_threads = True

application = get_wsgi_application()
# Domain clock only for synthetic tracking tests. Never available in production settings.
from django.conf import settings
sandbox=Path(os.environ['E2E_WORKDIR']).resolve()
if not sandbox.name.startswith('salud-e2e-') or settings.DATABASES['default']['HOST']!=str(sandbox/'socket') or settings.DATABASES['default']['NAME']!='salud_e2e':
    raise RuntimeError('Synthetic clock refused outside owned browser cluster')
from core.tracking import workflow as tracking_workflow
from datetime import date
tracking_workflow.today=lambda service:date(2026,10,15)
server = Server(('127.0.0.1', 0), WSGIRequestHandler, bind_and_activate=False)
server.socket.close()
server.socket = socket.socket(fileno=int(os.environ['E2E_BACKEND_FD']))
server.server_address = server.socket.getsockname()
server.server_name = 'localhost'
server.server_port = server.server_address[1]
server.setup_environ()
server.set_app(application)
server.serve_forever()
