import json
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from core.importer import parse
from core.compliance_catalog import enrich
from core.models import ImportBatch,SourceRecord,Question,QuestionVersion,QuestionHelpVersion
class Command(BaseCommand):
    help='Vista previa por defecto; --approve-sha y --actor confirman exactamente el archivo revisado.'
    def add_arguments(self,p):
        p.add_argument('path');p.add_argument('--approve-sha');p.add_argument('--actor')
    @transaction.atomic
    def handle(self,*args,**o):
        records,report=parse(Path(o['path']))
        existing=ImportBatch.objects.filter(digest=report['sha256']).first()
        previous=ImportBatch.objects.order_by('-id').first()
        old={r.stable_id:r.text for r in previous.sourcerecord_set.all()} if previous else {}
        report['changes']={'new':[r['stable_id'] for r in records if r['stable_id'] not in old],'changed':[r['stable_id'] for r in records if r['stable_id'] in old and old[r['stable_id']]!=r['text']],'removed':sorted(set(old)-{r['stable_id'] for r in records})}
        self.stdout.write(json.dumps(report,ensure_ascii=False,indent=2))
        if not o['approve_sha']: return
        if o['approve_sha']!=report['sha256']: raise CommandError('El archivo cambió; revise otra vista previa.')
        actor=get_user_model().objects.filter(username=o['actor'],is_active=True,is_superuser=True).first()
        if not actor: raise CommandError('Se requiere operador de importación autorizado (bootstrap superusuario). No publica ni valida preguntas.')
        if existing:
            enrich(existing,Path(o['path']))
            self.stdout.write(f'Lote {existing.pk} conservado; catálogo normativo conciliado sin verificar vigencia.');return
        batch=ImportBatch.objects.create(digest=report['sha256'],filename=Path(o['path']).name,report=report,approved_by=actor)
        for row in records:
            s=SourceRecord.objects.create(batch=batch,**row)
            if row['kind'].startswith('question'):
                q,_=Question.objects.get_or_create(stable_id=row['stable_id'])
                previous=q.questionversion_set.order_by('-version').first()
                if previous and previous.source.text==s.text:continue
                v=QuestionVersion.objects.create(question=q,source=s,version=1 if not previous else previous.version+1)
                QuestionHelpVersion.objects.create(question_version=v,content={'original':s.text,'source':s.locator,'review_status':'draft','missing':['plain_explanation','purpose','knower','where_to_find','steps','fictional_example','evidence','sufficiency','applicability','escalation']})
        enrich(batch,Path(o['path']))
        self.stdout.write(f'Inventario importado en lote {batch.pk}. Ningún cuestionario publicado automáticamente.')
