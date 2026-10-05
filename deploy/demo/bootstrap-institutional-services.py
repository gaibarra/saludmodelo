"""Apply only the reviewed public directory to the authorized isolated demo."""
import os,sys,json,io,hashlib
from pathlib import Path
sys.path.insert(0,os.getcwd())
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
if settings.DATABASES['default']['NAME'] not in {'salud_modelo_demo','salud_catalog_rehearsal'}:
    raise RuntimeError('Unexpected database target')
cfg=json.load(sys.stdin)['institutional_import']
from core import institutional_services
path=Path(institutional_services.__file__).parent/'data/institutional_services_20261001_1.json'
if hashlib.sha256(path.read_bytes()).hexdigest()!=cfg['dataset_sha256']:raise RuntimeError('Dataset changed')
out=io.StringIO()
call_command('import_institutional_services',institution=cfg['institution'],actor=cfg['actor'],apply=True,stdout=out)
result=json.loads(out.getvalue())
print(json.dumps({'configured':True,'idempotent_repeat':not result['changed'],'catalog':result}))
