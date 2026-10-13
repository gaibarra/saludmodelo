#!/usr/bin/env python3
"""One-off authorized account import. Password is accepted only through stdin."""
import argparse,json,subprocess,importlib.util,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
folder=ROOT/'deploy/demo/runtime/salud-20261013'
config=json.loads((folder/'accounts.json').read_text());config['apply']=args.apply
if args.apply:
    import sys
    config['password']=sys.stdin.read().strip()
    assert config['password']
spec=importlib.util.spec_from_file_location('pilot',ROOT/'deploy/demo/redeploy-pilot.py');pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
before=pilot.inventory()
if args.apply:pilot.backup_to(folder/'before-accounts.dump')
script='CONFIG='+repr(config)+'\n'+(ROOT/'deploy/demo/import-health-accounts.py').read_text()
result=subprocess.run(['docker','exec','-i','salud-modelo-demo-backend-1','python','-c','import django;django.setup();exec(__import__("sys").stdin.read())'],input=script,text=True,capture_output=True)
if result.returncode:raise RuntimeError(result.stderr)
report=json.loads(result.stdout);out=folder/('created.json' if args.apply else 'preview.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2));out.chmod(0o600)
assert pilot.inventory()==before,'Container inventory changed'
print(json.dumps({k:v for k,v in report.items() if k not in ['created','skipped']}));print('created',len(report['created']),'skipped',len(report['skipped']),'containers_unchanged',len(before))
