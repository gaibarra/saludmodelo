"""Trusted editorial proposals matched to exact imported sources. No external AI calls."""
import hashlib
import json
from functools import lru_cache
from django.conf import settings
from rest_framework.exceptions import ValidationError, NotFound
from .models import SourceRecord, CatalogAccess

@lru_cache(maxsize=1)
def catalog():
    path=settings.BASE_DIR.parent/'imports/help-drafts-v1.json'
    return json.loads(path.read_text())

def entry_for(instance):
    data=catalog()
    source=instance.question_version.source
    entry=data['questions'].get(instance.question_version.question.stable_id)
    if not entry or source.batch.digest!=data['source_sha256']:
        return None
    if hashlib.sha256(source.text.encode()).hexdigest()!=entry['question_sha256']:
        return None
    return entry

def available(instance):
    return entry_for(instance) is not None

def build(instance):
    entry=entry_for(instance)
    if entry is None:
        raise NotFound('No hay una propuesta compatible con esta versión de la fuente. Puede preparar la ayuda manualmente.')
    source=instance.question_version.source
    if not CatalogAccess.objects.filter(institution_id=instance.service.site.campus.institution_id,batch=source.batch).exists():
        raise NotFound('El inventario ya no está autorizado para este servicio.')
    references=[]
    for ref in entry['references']:
        record=SourceRecord.objects.filter(batch=source.batch,stable_id=ref['stable_id']).first()
        if record is None or record.locator!=ref['locator'] or hashlib.sha256(record.text.encode()).hexdigest()!=ref['text_sha256']:
            raise ValidationError('Una referencia del borrador no coincide con el inventario. Revise la fuente; no se inventarán citas.')
        references.append({'id':record.pk,'locator':record.locator,'text':record.text,'section':record.section})
    payload={'instance':instance.pk,'question_version':instance.question_version.version,'catalog_version':catalog()['version'],'content':entry['content'],'references':references}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {**payload,'digest':digest,'status':'draft_requires_human_review'}
