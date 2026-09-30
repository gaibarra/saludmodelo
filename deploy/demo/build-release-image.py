#!/usr/bin/env python3
"""Send an explicit allowlist to Docker, including with the legacy builder.
Never sends runtime, backups, environment files, tests or unrelated project files.
"""
import argparse,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('service',choices=['backend','frontend']);p.add_argument('--tag',required=True);args=p.parse_args()
if not args.tag.startswith('salud-modelo-demo-'+args.service+':'):raise SystemExit('Invalid project image tag')
paths={'backend':['backend/requirements.lock','backend/config','backend/core','backend/manage.py','imports','Plan_Trabajo_Escuela_Salud_Modelo.docx','deploy/demo/seed.py'], 'frontend':['frontend/package.json','frontend/next.config.ts','frontend/node_modules','frontend/.next-demo','frontend/public']}[args.service]
def selected(info):
    parts=Path(info.name).parts
    if '__pycache__' in parts or '.git' in parts or info.name.startswith('frontend/.next-demo/cache/'):return None
    return info
cmd=['docker','build','--force-rm','-t',args.tag,'-']
if args.service=='frontend':cmd.insert(2,'--network=none')
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,cwd=ROOT)
try:
    with tarfile.open(fileobj=proc.stdin,mode='w|',format=tarfile.GNU_FORMAT) as archive:
        archive.add(ROOT/f'deploy/demo/{args.service}.Dockerfile',arcname='Dockerfile')
        for path in paths:archive.add(ROOT/path,arcname=path,filter=selected)
    proc.stdin.close()
    if proc.wait():raise SystemExit('Image build failed')
finally:
    if proc.poll() is None:proc.terminate();proc.wait()
