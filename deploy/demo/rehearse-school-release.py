"""Restore, migrate and provision the authorized 0.35 release on private socket only."""
import getpass,json,os,secrets,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PG=Path('/usr/lib/postgresql/16/bin');PYTHON=ROOT/'backend/.venv/bin/python'
f=Path(sys.argv[1]).resolve()
assert f.is_relative_to(ROOT/'deploy/demo/runtime/releases')
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix='salud-school-rehearsal-') as folder:
    work=Path(folder);(work/'socket').mkdir(mode=0o700)
    env={**{k:v for k,v in os.environ.items() if not k.startswith('PG')},'PGHOST':str(work/'socket'),'PGDATABASE':'salud_school_rehearsal','PGUSER':getpass.getuser(),'PGPASSWORD':'','PGPORT':'5432','DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'DJANGO_SETTINGS_MODULE':'config.settings','PYTHONPATH':str(ROOT/'backend'),'AI_EXTERNAL_ENABLED':'0','PATIENT_PORTAL_ENABLED':'0','PRIVATE_STORAGE':str(work/'private'),'MFA_REQUIRE_PRIVILEGED':'1','ALLOWED_HOSTS':'plansaludmodelo.online,testserver','RELEASE_DIR':str(f)}
    started=False
    try:
        subprocess.run([str(PG/'initdb'),'-D',str(work/'pg'),'-A','trust','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([str(PG/'pg_ctl'),'-D',str(work/'pg'),'-l',str(work/'pg.log'),'-o',f'-k {work}/socket -h ""','start'],check=True,stdout=subprocess.DEVNULL);started=True
        subprocess.run([str(PG/'createdb'),env['PGDATABASE']],env=env,check=True)
        subprocess.run([str(PG/'pg_restore'),'--exit-on-error','--no-owner','--no-acl','--dbname',env['PGDATABASE'],str(f/'preparation.dump')],env=env,check=True)
        code=r'''
import os,sys,json,subprocess
from pathlib import Path
import psycopg
from psycopg import sql
f=Path(os.environ['RELEASE_DIR']);conn=psycopg.connect('');records=[]
with conn.cursor() as c:
    c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'django_migrations' ORDER BY tablename")
    for (t,) in c.fetchall():
        c.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) WHERE i.indrelid=%s::regclass AND i.indisprimary",(t,));keys=[r[0] for r in c.fetchall()];assert len(keys)==1
        c.execute(sql.SQL('SELECT * FROM {} ORDER BY {}').format(sql.Identifier(t),sql.Identifier(keys[0])))
        rows=c.fetchall();cols=[a.name for a in c.description]
        if rows:records.append((t,keys[0],cols,rows))
conn.close()
subprocess.run([sys.executable,'backend/manage.py','migrate','--noinput'],check=True)
# Run the exact same script with private stdin as the eventual deployment.
with psycopg.connect('') as probe:
    with probe.cursor() as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM core_governanceevent WHERE action='release.schools.configured' AND object_id=%s)",(json.loads((f/'bootstrap.json').read_text())['release_key'],))
        already_configured=cur.fetchone()[0]
for attempt in range(2):
    with (f/'bootstrap.json').open('rb') as cfg:
        r=subprocess.run(['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp:size=32m','--memory','256m','--cpus','0.5','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'-i','-v',os.environ['PGHOST']+':/tmp/salud-stage-socket:ro','-v',str(Path('deploy/demo/bootstrap-school-release.py').resolve())+':/tmp/bootstrap-school-release.py:ro','-e','PGHOST=/tmp/salud-stage-socket','-e','PGUSER='+os.environ['PGUSER'],'-e','PGDATABASE=salud_school_rehearsal','-e','DJANGO_SECRET_KEY='+os.environ['DJANGO_SECRET_KEY'],'-e','PATIENT_PORTAL_ENABLED=0','-e','AI_EXTERNAL_ENABLED=0','-e','MFA_REQUIRE_PRIVILEGED=1','-e','ALLOWED_HOSTS=plansaludmodelo.online,testserver','salud-modelo-demo-backend:0.35','python','/tmp/bootstrap-school-release.py'],stdin=cfg,stdout=subprocess.PIPE,check=True)
    result=json.loads(r.stdout);assert result['configured'] and result['idempotent_repeat']==bool(attempt or already_configured)
subprocess.run([sys.executable,'backend/manage.py','check'],check=True)
conn=psycopg.connect('');preserved=0;mutations=[]
allowed={'core_service':{'school_id'},'core_institution':{'name'},'core_institutionmandate':{'ends'},'core_roleassignment':{'revoked_at','revoked_by_id','revocation_reason'}}
with conn.cursor() as c:
    for t,key,cols,rows in records:
        ids=[r[cols.index(key)] for r in rows]
        c.execute(sql.SQL('SELECT {} FROM {} WHERE {}=ANY(%s) ORDER BY {}').format(sql.SQL(',').join(map(sql.Identifier,cols)),sql.Identifier(t),sql.Identifier(key),sql.Identifier(key)),(ids,));after=c.fetchall()
        assert len(rows)==len(after),t+' row count changed'
        for old,new in zip(rows,after):
            diffs={col for col,a,b in zip(cols,old,new) if a!=b}
            assert diffs<=allowed.get(t,set()),'Unexpected mutation '+t+str(diffs)
            if diffs:mutations.append({'table':t,'id':old[cols.index(key)],'fields':sorted(diffs)})
        preserved+=len(rows)
    c.execute("SELECT name FROM django_migrations WHERE app='core' ORDER BY name DESC LIMIT 1");latest=c.fetchone()[0]
    assert latest=='0042_school_boundaries'
report={'restored':True,'configured':True,'idempotency_verified':True,'original_rows_retained':preserved,'original_populated_tables_verified':len(records),'documented_original_changes':mutations,'core_latest_migration':latest,'school_ids':result['school_ids'],'account_ids':result['account_ids'],'mfa_required':True,'mfa_enrolled_by_agent':False,'database_transport':'private Unix socket; no TCP'}
(f/'rehearsal.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
        subprocess.run([str(PYTHON),'-c',code],cwd=ROOT,env=env,check=True)
    finally:
        if started:subprocess.run([str(PG/'pg_ctl'),'-D',str(work/'pg'),'stop','-m','fast'],check=True,stdout=subprocess.DEVNULL)
