#!/usr/bin/env python3
"""Restore only a project backup into a disposable, private PostgreSQL cluster.
Checks original rows/columns survive the additive upgrade; never targets the live DB.
"""
import getpass,hashlib,json,os,secrets,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PYTHON=ROOT/'backend/.venv/bin/python'
PG=Path('/usr/lib/postgresql/16/bin')

def main():
    backup=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve()
    if not backup.is_relative_to(ROOT/'deploy/demo/runtime') or not output.is_relative_to(ROOT/'deploy/demo/runtime'):raise RuntimeError('Use only project runtime paths')
    with tempfile.TemporaryDirectory(prefix='salud-upgrade-') as folder:
        work=Path(folder);(work/'socket').mkdir(mode=0o700)
        env={**{k:v for k,v in os.environ.items() if not k.startswith('PG')},'PGHOST':str(work/'socket'),'PGDATABASE':'salud_upgrade_rehearsal','PGUSER':getpass.getuser(),'PGPASSWORD':'','PGPORT':'5432','DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'AI_EXTERNAL_ENABLED':'0','PATIENT_PORTAL_ENABLED':'0','PRIVATE_STORAGE':str(work/'private'),'MFA_REQUIRE_PRIVILEGED':'0'}
        started=False
        try:
            subprocess.run([str(PG/'initdb'),'-D',str(work/'pg'),'-A','trust','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
            subprocess.run([str(PG/'pg_ctl'),'-D',str(work/'pg'),'-l',str(work/'pg.log'),'-o',f'-k {work}/socket -h ""','start'],check=True,stdout=subprocess.DEVNULL);started=True
            subprocess.run([str(PG/'createdb'),env['PGDATABASE']],env=env,check=True)
            subprocess.run([str(PG/'pg_restore'),'--exit-on-error','--no-owner','--no-acl','--dbname',env['PGDATABASE'],str(backup)],env=env,check=True)
            code=r'''
import hashlib,json,os,subprocess,sys
import psycopg
from psycopg import sql
from pathlib import Path
conn=psycopg.connect('')
records=[]
with conn.cursor() as cur:
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'django_migrations' ORDER BY tablename")
    for (table,) in cur.fetchall():
        cur.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) WHERE i.indrelid=%s::regclass AND i.indisprimary",(table,))
        keys=[row[0] for row in cur.fetchall()]
        if len(keys)!=1:raise RuntimeError('Expected single primary key: '+table)
        key=keys[0]
        cur.execute(sql.SQL('SELECT * FROM {} ORDER BY {}').format(sql.Identifier(table),sql.Identifier(key)))
        rows=cur.fetchall();columns=[c.name for c in cur.description]
        if rows:
            records.append((table,key,columns,rows))
conn.close()
subprocess.run([sys.executable,'backend/manage.py','migrate','--noinput'],check=True)
subprocess.run([sys.executable,'backend/manage.py','check'],check=True)
conn=psycopg.connect('');preserved=0
with conn.cursor() as cur:
    for table,key,columns,rows in records:
        pk=columns.index(key);ids=[r[pk] for r in rows]
        cur.execute(sql.SQL('SELECT {} FROM {} WHERE {}=ANY(%s) ORDER BY {}').format(sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(table),sql.Identifier(key),sql.Identifier(key)),(ids,))
        after=cur.fetchall()
        if rows!=after:raise RuntimeError('Original rows changed in '+table)
        preserved+=len(rows)
    cur.execute("SELECT name FROM django_migrations WHERE app='core' ORDER BY name")
    migrations=[r[0] for r in cur.fetchall()]
    for table in ('core_academiccycle','core_academicevaluation','core_academiccyclereport','core_patientprofile'):
        cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
        if cur.fetchone()[0]!=0:raise RuntimeError('Unexpected intake in '+table)
result={'restored':True,'original_populated_tables_verified':len(records),'original_rows_preserved':preserved,'core_latest_migration':migrations[-1],'patient_intake_enabled':False,'external_ai_enabled':False,'database_transport':'private Unix socket; no TCP'}
Path(os.environ['REHEARSAL_OUTPUT']).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
'''
            subprocess.run([str(PYTHON),'-c',code],cwd=ROOT,env={**env,'REHEARSAL_OUTPUT':str(output)},check=True)
        finally:
            if started:subprocess.run([str(PG/'pg_ctl'),'-D',str(work/'pg'),'stop','-m','fast'],check=True,stdout=subprocess.DEVNULL)
if __name__=='__main__':main()
