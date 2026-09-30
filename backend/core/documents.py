import math
import hashlib
import json
import subprocess
import sys
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .access import require, REVIEW
from .models import EvidenceDocument, EvidenceExtraction, EvidenceFragment, EvidenceReview, AuditEvent
from .workflow import Conflict

ERRORS={'security_blocked','scanner_unavailable','sandbox_failed','invalid_pdf','page_limit','page_mismatch','ocr_required','invalid_office','archive_limit','encrypted_document','invalid_archive','active_content','unsafe_xml','external_reference','locator_limit','ocr_failed','ocr_timeout','ocr_no_text','ocr_page_limit','invalid_image','image_limit','input_limit','text_limit','fragment_limit','column_limit','empty_document','binary_content','invalid_utf8','invalid_csv','memory_limit','unsupported_format','process_failed','timeout','storage_unavailable','digest_mismatch','attempt_limit'}

def validate_result(data):
    """Treat the sandbox output as untrusted; never pass arbitrary keys to the ORM."""
    if not isinstance(data,dict):return {'error':'process_failed'}
    security={'security':data['security']} if isinstance(data.get('security'),str) and data['security'] in {'clean','blocked','unavailable'} else {}
    if 'error' in data:return {'error':data['error'] if isinstance(data['error'],str) and data['error'] in ERRORS else 'process_failed',**security}
    fragments=data.get('fragments')
    if not isinstance(fragments,list) or not 1<=len(fragments)<=10000:return {'error':'process_failed',**security}
    total=0;text_total=0
    for i,f in enumerate(fragments,1):
        if not isinstance(f,dict) or set(f)-{'ordinal','locator','text','cells','method','confidence'}:return {'error':'process_failed',**security}
        if f.get('ordinal')!=i or not isinstance(f.get('locator'),str) or not 0<len(f['locator'])<=120:return {'error':'process_failed',**security}
        if not isinstance(f.get('text'),str) or not f['text'].strip():return {'error':'process_failed',**security}
        total+=len(f['text']);text_total+=len(f['text'])
        if text_total>2000000:return {'error':'text_limit',**security}
        cells=f.get('cells')
        if cells is not None and (not isinstance(cells,list) or len(cells)>200 or any(not isinstance(c,str) or len(c)>200000 for c in cells)):return {'error':'process_failed',**security}
        if cells:total+=sum(len(c) for c in cells)
        if total>4000000:return {'error':'text_limit',**security}
        if not isinstance(f.get('method','literal'),str) or f.get('method','literal') not in {'literal','ocr'}:return {'error':'process_failed',**security}
        confidence=f.get('confidence')
        if confidence is not None and (not isinstance(confidence,(float,int)) or not math.isfinite(confidence) or not 0<=confidence<=100):return {'error':'process_failed',**security}
    return {'fragments':fragments,**security}

def run_parser(raw,kind):
    with tempfile.TemporaryDirectory(prefix='salud-extract-') as folder:
        try:
            result=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('extract_text.py')),kind],input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8,cwd=folder,env={'LANG':'C.UTF-8'},check=False)
        except subprocess.TimeoutExpired:return {'error':'timeout'}
    if result.returncode or len(result.stdout)>16_000_000:return {'error':'process_failed'}
    try:data=json.loads(result.stdout)
    except (ValueError,UnicodeDecodeError):return {'error':'process_failed'}
    if 'error' in data and data['error'] not in ERRORS:return {'error':'process_failed'}
    return data

def enqueue_legacy():
    # Bounded backfill; existing originals and reviews are never replaced.
    for document in EvidenceDocument.objects.filter(extraction__isnull=True).order_by('created_at')[:100]:
        EvidenceExtraction.objects.get_or_create(document=document)

@transaction.atomic
def claim():
    now=timezone.now()
    query=Q(state='pending')|Q(state='running',leased_until__lt=now)
    job=EvidenceExtraction.objects.select_for_update(skip_locked=True).filter(query).order_by('id').first()
    if job is None:return None
    if job.attempts>=3:
        job.state='failed';job.error='attempt_limit';job.leased_until=None;job.token=None;job.save();return (job.pk,None)
    job.attempts+=1;job.state='running';job.token=uuid.uuid4();job.leased_until=now+timedelta(seconds=180);job.error='';job.save()
    return (job.pk,job.token)

@transaction.atomic
def finish(pk,token,data):
    data=validate_result(data)
    document_id=EvidenceExtraction.objects.values_list('document_id',flat=True).get(pk=pk)
    document=EvidenceDocument.objects.select_for_update().get(pk=document_id)
    job=EvidenceExtraction.objects.select_for_update().get(pk=pk)
    if job.state!='running' or job.token!=token:return False
    if document.format in {'pdf','docx','xlsx','png','jpg','jpeg'}:job.extractor='sandbox-pdf-office-v1'
    if data.get('security') in {'clean','blocked','unavailable'}:
        document.security_state=data['security'];document.scanned_at=timezone.now();document.save(update_fields=['security_state','scanned_at'])
    if 'error' in data:
        job.state='failed';job.error=data['error']
    else:
        EvidenceFragment.objects.bulk_create([EvidenceFragment(extraction=job,**fragment) for fragment in data['fragments']])
        job.state='ready';job.error=''
    job.finished_at=timezone.now();job.leased_until=None;job.token=None;job.save()
    return True

def process_one():
    claimed=claim()
    if claimed is None:return False
    pk,token=claimed
    if token is None:return True
    job=EvidenceExtraction.objects.select_related('document').get(pk=pk)
    try:
        with job.document.file.open('rb') as file:raw=file.read(10_000_001)
    except OSError:data={'error':'storage_unavailable'}
    else:
        if hashlib.sha256(raw).hexdigest()!=job.document.sha256:data={'error':'digest_mismatch'}
        elif job.document.format in {'pdf','docx','xlsx','png','jpg','jpeg'}:
            from .secure_documents import parse_binary
            data=parse_binary(raw,job.document.format)
        elif job.document.scan_required:
            from .secure_documents import scan
            from .document_sandbox import execute,SandboxError
            data=scan(raw)
            if 'error' not in data:
                try:
                    code,output=execute(['/usr/bin/python3','-I','/app/extract_text.py',job.document.format,'/input/document'],files={'/input/document':raw,'/app/extract_text.py':Path(__file__).with_name('extract_text.py')})
                    data={**(json.loads(output) if code==0 else {'error':'process_failed'}),**data}
                except (OSError,SandboxError,ValueError):data={'error':'process_failed',**data}
        else:data=run_parser(raw,job.document.format)
    finish(pk,token,data)
    return True

@transaction.atomic
def review_document(user,pk,version,decision,rationale,valid_until,ocr_checked=False):
    doc=EvidenceDocument.objects.select_for_update().select_related('answer__instance','revision').get(pk=pk)
    require(user,doc.answer.instance.service_id,REVIEW)
    if user.pk in {doc.uploader_id,doc.revision.author_id}:raise ValidationError('Otra persona debe revisar esta evidencia.')
    if doc.etag!=version:raise Conflict()
    if decision=='accepted':
        if (doc.scan_required or doc.format not in {'txt','csv'}) and doc.security_state!='clean':raise ValidationError('El análisis de seguridad todavía no permite revisar este documento.')
        if not EvidenceExtraction.objects.filter(document=doc,state='ready').exists():raise ValidationError('Espere la extracción y revise el original antes de aceptar.')
        if EvidenceFragment.objects.filter(extraction__document=doc,method='ocr').exists() and not ocr_checked:raise ValidationError('Compare el texto OCR con el original y confirme su cotejo antes de aceptar.')
        if valid_until is None or valid_until<timezone.localdate():raise ValidationError('Indique una fecha de vigencia igual o posterior a hoy.')
    elif valid_until is not None:raise ValidationError('La devolución no registra vigencia.')
    EvidenceReview.objects.create(ocr_checked=ocr_checked,document=doc,reviewer=user,decision=decision,rationale=rationale,valid_until=valid_until)
    doc.state=decision;doc.etag+=1;doc.save(update_fields=['state','etag'])
    AuditEvent.objects.create(actor=user,service=doc.answer.instance.service,action='evidence.'+decision,object_id=str(doc.pk))
    return doc

@transaction.atomic
def retry_document(user,pk,version):
    from .access import WRITE
    doc=EvidenceDocument.objects.select_for_update().select_related('answer__instance').get(pk=pk)
    require(user,doc.answer.instance.service_id,WRITE|REVIEW)
    if doc.etag!=version:raise Conflict()
    job=EvidenceExtraction.objects.select_for_update().get(document=doc)
    if job.state!='failed' or job.attempts>=3:raise ValidationError('No hay un fallo reintentable. Revise el original y adjunte una nueva versión si corresponde.')
    job.state='pending';job.error='';job.token=None;job.leased_until=None;job.finished_at=None;job.save()
    doc.etag+=1;doc.save(update_fields=['etag'])
    AuditEvent.objects.create(actor=user,service=doc.answer.instance.service,action='evidence.extraction_retried',object_id=str(doc.pk))
    return doc
