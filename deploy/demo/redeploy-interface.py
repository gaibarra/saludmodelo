#!/usr/bin/env python3
"""Frontend-only patch; never stops backend, worker, database or other projects."""
import argparse, re, datetime, fcntl, json, os, shutil, time, urllib.request
from pathlib import Path
import redeploy as shared

RUNTIME=shared.ROOT/'deploy/demo/runtime'
POINTER=RUNTIME/'active-release.txt'

def verify_routes():
    origin='https://plansaludmodelo.online'
    deadline=time.monotonic()+45
    while True:
        try:
            for path,marker in [('/', 'Tu bienestar tiene un lugar'),('/personal','Portal de servicios'),('/portal','Tu bienestar tiene un lugar'),('/health',None)]:
                with urllib.request.urlopen(origin+path,timeout=10) as response:
                    body=response.read().decode()
                    if response.status!=200 or (marker and marker not in body):raise RuntimeError('Unexpected response: '+path)
            return
        except Exception:
            if time.monotonic()>=deadline:raise
            time.sleep(2)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','activate','rollback']);p.add_argument('target');args=p.parse_args()
    os.umask(0o077)
    with (RUNTIME/'redeploy.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.mode=='prepare':
            if not args.target.startswith('salud-modelo-demo-frontend:'):raise RuntimeError('Unexpected image namespace')
            version=args.target.rsplit(':',1)[1]
            if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise RuntimeError('Expected semantic version image tag')
            previous=Path(POINTER.read_text().strip())
            current=shared.inventory();own={r['service']:r for r in current.values() if r['project']==shared.PROJECT}
            if set(own)!=set(shared.SERVICES):raise RuntimeError('Unexpected project services')
            override=json.loads((previous/'release.compose.json').read_text())
            for s in ['frontend','backend','worker']:
                if override['services'][s]['image']!=own[s]['image']:raise RuntimeError('Active release differs: '+s)
            if own['gateway']['ports']!={'8080/tcp':[{'HostIp':'127.0.0.1','HostPort':'3117'}]} or own['db']['network_mode']!='none':raise RuntimeError('Isolation differs')
            if own['frontend']['ports'] or own['frontend']['mounts']:raise RuntimeError('Unexpected frontend resources')
            folder=RUNTIME/'releases'/(version+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir(mode=0o700)
            image=shared.output(['docker','image','inspect',args.target,'--format','{{.Id}}'])
            shared.write(folder/'rollback.compose.json',override)
            override['services']['frontend']['image']=image
            shared.write(folder/'release.compose.json',override)
            # Keep private login verification data; never run account bootstrap in this patch.
            shutil.copyfile(previous/'bootstrap.json',folder/'bootstrap.json');(folder/'bootstrap.json').chmod(0o600)
            manifest={'version':version,'project':shared.PROJECT,'domain':'plansaludmodelo.online','kind':'frontend-only','previous_release':str(previous),'runner':'redeploy-interface.py','runner_sha256':shared.sha(Path(__file__)),'compose_sha256':shared.sha(shared.BASE),'gateway_sha256':shared.sha(shared.ROOT/'deploy/demo/gateway.conf'),'before':current,'images':{'frontend':image,'backend':own['backend']['image']},'release_hashes':{name:shared.sha(folder/name) for name in ['release.compose.json','rollback.compose.json','bootstrap.json']},'config_hashes':{name:shared.sha(RUNTIME/name) for name in ['backend.env','database.env']}}
            shared.write(folder/'manifest.json',manifest)
            shared.run(shared.compose(folder/'release.compose.json')+['config','--quiet'])
            print(folder);return
        folder=Path(args.target).resolve()
        if not folder.is_relative_to(RUNTIME/'releases'):raise RuntimeError('Invalid release path')
        m=json.loads((folder/'manifest.json').read_text())
        if m['kind']!='frontend-only' or m['project']!=shared.PROJECT:raise RuntimeError('Wrong release kind')
        if m['runner_sha256']!=shared.sha(Path(__file__)) or m['compose_sha256']!=shared.sha(shared.BASE) or m['gateway_sha256']!=shared.sha(shared.ROOT/'deploy/demo/gateway.conf'):raise RuntimeError('Deployment inputs changed')
        for name,digest in m['release_hashes'].items():
            if shared.sha(folder/name)!=digest:raise RuntimeError('Release file changed')
        for name,digest in m['config_hashes'].items():
            if shared.sha(RUNTIME/name)!=digest:raise RuntimeError('Configuration changed')
        before=shared.inventory();frontend_name=next(k for k,v in m['before'].items() if v['project']==shared.PROJECT and v['service']=='frontend')
        protected=lambda rows:{k:v for k,v in rows.items() if k!=frontend_name}
        if protected(before)!=protected(m['before']):raise RuntimeError('Other running containers changed since preparation')
        if args.mode=='activate':
            if before!=m['before'] or POINTER.read_text().strip()!=m['previous_release']:raise RuntimeError('Active release changed')
        else:
            if POINTER.read_text().strip()!=str(folder) or before[frontend_name]['image']!=m['images']['frontend']:raise RuntimeError('Rollback target is not active')
        target=folder/('release.compose.json' if args.mode=='activate' else 'rollback.compose.json')
        shared.run(shared.compose(target)+['config','--quiet'])
        try:
            shared.run(shared.compose(target)+['up','-d','--no-deps','--no-build','frontend'])
            shared.reload_gateway()
            if args.mode=='activate':verify_routes()
            else:
                with urllib.request.urlopen('https://plansaludmodelo.online/',timeout=20) as r:
                    if r.status!=200:raise RuntimeError('Rollback response failed')
        except Exception:
            if args.mode=='activate':
                shared.run(shared.compose(folder/'rollback.compose.json')+['up','-d','--no-deps','--no-build','frontend'])
                shared.reload_gateway()
            raise
        after=shared.inventory()
        if protected(after)!=protected(before):raise RuntimeError('Protected inventory differs; investigate without altering it')
        active=str(folder) if args.mode=='activate' else m['previous_release']
        temporary=RUNTIME/'active-release.tmp';temporary.write_text(active+'\n');temporary.replace(POINTER)
        shared.write(folder/(args.mode+'-verified.json'),{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':args.mode,'only_frontend_replaced':True,'protected_containers_unchanged':len(protected(after)),'after':after})
        print('Frontend updated; other containers, backend, database and worker unchanged.')
if __name__=='__main__':main()
