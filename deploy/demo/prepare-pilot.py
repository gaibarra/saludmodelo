#!/usr/bin/env python3
"""Prepare the explicitly authorized persistent portal pilot; never activate or seed."""
import datetime,importlib.util,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pilot',ROOT/'deploy/demo/redeploy-pilot.py');pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
os.umask(0o077)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
folder=ROOT/'deploy/demo/runtime/releases'/('0.40.0-'+stamp);folder.mkdir()
before=pilot.inventory();own={v['service']:v for v in before.values() if v['project']==pilot.PROJECT}
assert set(own)==set(pilot.SERVICES)
images={k:pilot.output(['docker','image','inspect',f'salud-modelo-demo-{k}:0.40.0','--format','{{.Id}}']) for k in ['backend','frontend']}
flags={'PATIENT_PORTAL_ENABLED':'1','MFA_PASSWORD_ONLY_PILOT':'1','MFA_DEMO_PASSWORD_ONLY':'0','MFA_REQUIRE_PRIVILEGED':'1','AI_EXTERNAL_ENABLED':'0'}
release={'services':{k:{'image':images['backend' if k=='worker' else k],**({'environment':flags} if k!='frontend' else {})} for k in ['backend','frontend','worker']}}
# Preserve actual prior flags, not a guessed default, without exposing secrets.
rollback={'services':{}}
for service in ['backend','frontend','worker']:
    entry={'image':own[service]['image']}
    if service!='frontend':
        values=json.loads(pilot.output(['docker','inspect',own[service]['id'],'--format','{{json .Config.Env}}']))
        env=dict(v.split('=',1) for v in values)
        entry['environment']={k:env.get(k,'0') for k in flags}
    rollback['services'][service]=entry
pilot.write(folder/'release.compose.json',release);pilot.write(folder/'rollback.compose.json',rollback)
pilot.backup_to(folder/'preparation.dump')
subprocess.run(['python3',str(ROOT/'deploy/demo/rehearse-upgrade.py'),str(folder/'preparation.dump'),str(folder/'rehearsal.json')],check=True,cwd=ROOT)
manifest={'project':pilot.PROJECT,'domain':'plansaludmodelo.online','version':'0.40.0','bootstrap':False,'patient_portal_enabled':True,'previous_release':(ROOT/'deploy/demo/runtime/active-release.txt').read_text().strip(),'compose_sha256':pilot.sha(pilot.BASE),'gateway_sha256':pilot.sha(ROOT/'deploy/demo/gateway.conf'),'runner_sha256':pilot.sha(ROOT/'deploy/demo/redeploy-pilot.py'),'config_hashes':{k:pilot.sha(ROOT/'deploy/demo/runtime'/k) for k in ['backend.env','database.env']},'release_hashes':{k:pilot.sha(folder/k) for k in ['release.compose.json','rollback.compose.json','rehearsal.json','preparation.dump']},'images':images,'before':own,'authorization_status':'User explicitly requested implementation and publication of the persistent account/request pilot with password-only staff access.'}
pilot.write(folder/'manifest.json',manifest)
pilot.preflight(folder)
print('PREPARED_RELEASE='+str(folder))
