#!/usr/bin/env python3
"""Prepare/check an immutable demo release; activation requires an explicit command.
No Nginx host/Certbot changes, no compose down, no volume removal, no seed/reset.
"""
import argparse,datetime,fcntl,hashlib,json,os,subprocess,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deploy/demo/compose.yaml'
PROJECT='salud-modelo-demo'
SERVICES=('db','backend','frontend','worker','gateway')

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def output(args):return subprocess.check_output(args,text=True).strip()
def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def compose(release=None):
    cmd=['docker','compose','-p',PROJECT,'-f',str(BASE)]
    if release:cmd+=['-f',str(release)]
    return cmd

def inventory():
    ids=output(['docker','ps','-q']).splitlines()
    if not ids:raise RuntimeError('No running containers')
    fmt='{"id":{{json .Id}},"name":{{json .Name}},"started":{{json .State.StartedAt}},"image":{{json .Image}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}},"network_mode":{{json .HostConfig.NetworkMode}}}'
    rows=list(map(json.loads,output(['docker','inspect','--format',fmt,*ids]).splitlines()))
    for row in rows:row['mounts']=sorted(row['mounts'],key=lambda mount:mount['Destination'])
    return {row['name']:row for row in rows}

def preflight(folder,allow_updated=False):
    hold=folder/'superseded.json'
    if hold.exists() and not allow_updated:
        raise RuntimeError('Release superseded: '+json.loads(hold.read_text())['reason'])
    manifest=json.loads((folder/'manifest.json').read_text())
    if manifest['project']!=PROJECT or manifest['domain']!='plansaludmodelo.online':raise RuntimeError('Unexpected release target')
    if sha(BASE)!=manifest['compose_sha256'] or sha(ROOT/'deploy/demo/gateway.conf')!=manifest['gateway_sha256']:raise RuntimeError('Deployment files changed; prepare again')
    for name,digest in manifest['config_hashes'].items():
        if sha(ROOT/'deploy/demo/runtime'/name)!=digest:raise RuntimeError('Private configuration changed; prepare again')
    if sha(Path(__file__))!=manifest['runner_sha256']:raise RuntimeError('Release runner changed; prepare again')
    for filename,digest in manifest['release_hashes'].items():
        if sha(folder/filename)!=digest:raise RuntimeError('Release file changed: '+filename)
    current=inventory();own={v['service']:v for v in current.values() if v['project']==PROJECT}
    if set(own)!=set(SERVICES):raise RuntimeError('Unexpected or missing demo services')
    if not allow_updated:
        for service in SERVICES:
            if own[service]['id']!=manifest['before'][service]['id']:raise RuntimeError('Running demo changed; prepare again')
    else:
        for service in ('db','gateway'):
            if own[service]['id']!=manifest['before'][service]['id']:raise RuntimeError('Infrastructure changed; review rollback')
        for service in ('backend','frontend','worker'):
            expected=manifest['images']['backend' if service=='worker' else service]
            if own[service]['image']!=expected:raise RuntimeError('Current release differs; review rollback')
    if own['db']['network_mode']!='none':raise RuntimeError('Database network isolation changed')
    ports=own['gateway']['ports'].get('8080/tcp',[])
    if ports!=[{'HostIp':'127.0.0.1','HostPort':'3117'}]:raise RuntimeError('Unexpected gateway binding')
    for service in ('db','backend','frontend','worker'):
        if own[service]['ports']:raise RuntimeError('Unexpected exposed application/database port')
    for row in own.values():
        for mount in row['mounts']:
            if mount['Type']=='volume' and not mount['Name'].startswith(PROJECT+'_'):raise RuntimeError('Foreign volume detected')
    for service,image in manifest['images'].items():
        if output(['docker','image','inspect',image,'--format','{{.Id}}'])!=image:raise RuntimeError('Prepared image unavailable')
    for service in ('backend','frontend','worker'):
        image=manifest['before'][service]['image']
        if output(['docker','image','inspect',image,'--format','{{.Id}}'])!=image:raise RuntimeError('Rollback image unavailable')
    run(compose(folder/'release.compose.json')+['config','--quiet'])
    run(compose(folder/'rollback.compose.json')+['config','--quiet'])
    rehearsal=json.loads((folder/'rehearsal.json').read_text())
    if not rehearsal.get('restored'):raise RuntimeError('Restore rehearsal not successful')
    if manifest.get('bootstrap') and not (rehearsal.get('configured') and rehearsal.get('idempotency_verified')):raise RuntimeError('School configuration rehearsal missing')
    return manifest,current

def check_routes():
    for path in ('/health','/','/portal','/escuelas','/academico','/academico/evaluaciones','/images/salud-hero.png','/api/v1/public/services/'):
        req=urllib.request.Request('https://plansaludmodelo.online'+path)
        with urllib.request.urlopen(req,timeout=20) as response:
            if response.status!=200:raise RuntimeError('Route failed: '+path)
            if path.endswith('services/') and json.load(response)['appointments_enabled']:raise RuntimeError('Patient intake unexpectedly enabled')

def reload_gateway():
    run(compose()+['exec','-T','gateway','nginx','-t'])
    run(compose()+['exec','-T','gateway','nginx','-s','reload'])

def backup_to(path):
    with path.open('xb') as stream:
        run(compose()+['exec','-T','db','pg_dump','-h','/var/run/postgresql','-U','salud_modelo_demo','-d','salud_modelo_demo','-Fc'],stdout=stream)
    path.chmod(0o600)
    if path.stat().st_size<1000:raise RuntimeError('Empty database backup')

def application_ready():
    run(compose()+['exec','-T','backend','python','-c',"import urllib.request,json; r=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/public/services/',headers={'Host':'plansaludmodelo.online'})); assert not json.load(r)['appointments_enabled']"])
    run(compose()+['exec','-T','frontend','node','-e',"Promise.all(['/portal','/escuelas','/academico','/images/salud-hero.png'].map(async p=>{const r=await fetch('http://127.0.0.1:3000'+p);if(!r.ok)throw Error(p)})).catch(e=>{console.error(e.message);process.exit(1)})"])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['check','activate','rollback']);parser.add_argument('release');args=parser.parse_args()
    os.umask(0o077);folder=Path(args.release).resolve()
    if not folder.is_relative_to(ROOT/'deploy/demo/runtime/releases'):raise RuntimeError('Invalid release location')
    lock=(ROOT/'deploy/demo/runtime/redeploy.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest,before=preflight(folder,allow_updated=args.mode=='rollback')
    if args.mode=='check':print('Release verified; live containers and schema unchanged.');return
    unrelated={k:v for k,v in before.items() if v['project']!=PROJECT}
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    if args.mode=='rollback':
        # Deliberately retain additive schema and all data recorded after activation.
        run(compose(folder/'rollback.compose.json')+['up','-d','--no-deps','--no-build','backend','frontend','worker'])
        reload_gateway()
        with urllib.request.urlopen('https://plansaludmodelo.online/',timeout=20) as response:
            if response.status!=200:raise RuntimeError('Rollback route check failed')
        write(folder/'rolled-back.json',{'at':stamp,'schema_retained':True})
        (ROOT/'deploy/demo/runtime/active-release.txt').write_text('previous-images; see '+str(folder)+'\n')
        print('Previous application images restored; database and new records retained.')
    else:
        backup_to(folder/f'before-activation-{stamp}.dump')
        try:
            run(compose()+['stop','worker','backend'])
            # Final quiescent database copy: no application writers during upgrade.
            backup_to(folder/f'quiescent-{stamp}.dump')
            with (folder/f'private-files-{stamp}.tar').open('xb') as private_copy:
                run(compose(folder/'release.compose.json')+['run','--rm','--no-deps','-T','backend','tar','-C','/private','-cf','-','.'],stdout=private_copy)
            run(compose(folder/'release.compose.json')+['run','--rm','--no-deps','backend','python','manage.py','migrate','--noinput'])
            if manifest.get('bootstrap'):
                with (folder/'bootstrap.json').open('rb') as config:
                    result=run(compose(folder/'release.compose.json')+['run','--rm','--no-deps','-T','-v',str(folder/'bootstrap-school-release.py')+':/tmp/bootstrap-school-release.py:ro','backend','python','/tmp/bootstrap-school-release.py'],stdin=config,stdout=subprocess.PIPE)
                configured=json.loads(result.stdout)
                if not configured.get('configured'):raise RuntimeError('School bootstrap failed')
                write(folder/'configured.json',configured)
            run(compose(folder/'release.compose.json')+['up','-d','--no-deps','--no-build','backend','frontend','worker'])
            deadline=time.monotonic()+45
            while True:
                try:application_ready();break
                except subprocess.CalledProcessError:
                    if time.monotonic()>deadline:raise
                    time.sleep(2)
            reload_gateway()
            # nginx reload is asynchronous; allow old workers/upstreams to drain.
            public_deadline=time.monotonic()+45
            while True:
                try:check_routes();break
                except urllib.error.HTTPError as error:
                    if error.code not in (502,503,504) or time.monotonic()>public_deadline:raise
                    time.sleep(2)
        except Exception:
            run(compose(folder/'rollback.compose.json')+['up','-d','--no-deps','--no-build','backend','frontend','worker'])
            reload_gateway()
            raise RuntimeError('Activation failed; previous code restored, additive schema/data retained. Review before retrying.')
        write(folder/'activated.json',{'activated_at':stamp,'version':manifest['version'],'database_restored':False})
        (ROOT/'deploy/demo/runtime/active-release.txt').write_text(str(folder)+'\n')
        print('Version '+manifest['version']+' activated; patient intake remains disabled.')
    after=inventory()
    if {k:v for k,v in after.items() if v['project']!=PROJECT}!=unrelated:raise RuntimeError('Unrelated container inventory changed; investigate without modifying it')
    write(folder/f'verified-{stamp}.json',{'unrelated_containers_unchanged':True,'count':len(unrelated),'mode':args.mode})
if __name__=='__main__':main()
