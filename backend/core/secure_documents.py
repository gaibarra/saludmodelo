import json
import logging
import re
from pathlib import Path
from django.conf import settings
from .document_sandbox import execute,SandboxError

BINARY_FORMATS={'pdf','docx','xlsx','png','jpg','jpeg'}

def scan(raw):
    signatures=getattr(settings,'DOCUMENT_SIGNATURES','')
    if not signatures:return {'error':'scanner_unavailable','security':'unavailable'}
    command=['/usr/bin/clamscan','--database=/signatures','--cvdcertsdir=/certificates','--no-summary','--stdout','--infected','--fail-if-cvd-older-than=3','--max-scantime=90000','--max-filesize=12M','--max-scansize=30M','--max-files=1000','--max-recursion=10','--alert-exceeds-max=yes','--alert-encrypted=yes','--alert-macros=yes','--bytecode=no','/input/document']
    try:code,output=execute(command,files={'/input/document':raw},signatures=signatures,certificates=getattr(settings,'DOCUMENT_SCAN_CERTIFICATES','/etc/clamav/certs'),timeout=45,memory=1536*1024*1024)
    except (OSError,SandboxError):return {'error':'scanner_unavailable','security':'unavailable'}
    if code==1 and b' FOUND' in output:
        match=re.search(rb': ([A-Za-z0-9_.-]{1,120}) FOUND',output)
        logging.getLogger(__name__).warning('Document scanner blocked: %s',match.group(1).decode() if match else 'unclassified_detection')
        return {'error':'security_blocked','security':'blocked'}
    if code!=0:return {'error':'scanner_unavailable','security':'unavailable'}
    return {'security':'clean'}

def parse_binary(raw,kind):
    security=scan(raw)
    if 'error' in security:return security
    files={'/input/document':raw}
    if kind in {'png','jpg','jpeg'}:return {**ocr(raw,kind,1),**security}
    try:
        if kind=='pdf':
            if not raw.startswith(b'%PDF-'):return {'error':'invalid_pdf',**security}
            code,info=execute(['/usr/bin/pdfinfo','/input/document'],files=files)
            if code:return {'error':'invalid_pdf',**security}
            lines=info.decode('utf-8','replace').splitlines()
            pages=next((int(line.split(':',1)[1]) for line in lines if line.startswith('Pages:')),0)
            if not 1<=pages<=200:return {'error':'page_limit',**security}
            code,output=execute(['/usr/bin/pdftotext','-enc','UTF-8','-layout','/input/document','-'],files=files)
            if code:return {'error':'invalid_pdf',**security}
            if len(output)>2_000_000:return {'error':'text_limit',**security}
            page_text=output.decode('utf-8').split('\f')
            if page_text and not page_text[-1].strip():page_text.pop()
            if len(page_text)!=pages:return {'error':'page_mismatch',**security}
            if any(not text.strip() for text in page_text):return {**ocr(raw,'pdf',pages),**security}
            fragments=[]
            for number,text in enumerate(page_text,1):
                fragments.append({'ordinal':number,'locator':f'Página {number}','text':text,'cells':None})
            return {'fragments':fragments,**security}
        files['/app/extract_office.py']=Path(__file__).with_name('extract_office.py')
        code,output=execute(['/usr/bin/python3','-I','/app/extract_office.py',kind],files=files)
        if code:return {'error':'invalid_office',**security}
        result=json.loads(output)
        if result.get('error') in {'active_content','unsafe_xml','external_reference','encrypted_document','invalid_archive'}:security={'security':'blocked'}
        return {**result,**security}
    except (OSError,SandboxError,ValueError,UnicodeDecodeError):return {'error':'sandbox_failed',**security}


def ocr(raw,kind,pages):
    import time
    from .extract_ocr import image_size,parse_tsv
    runtime=getattr(settings,'DOCUMENT_OCR_RUNTIME','')
    if not runtime:return {'error':'ocr_required'}
    if not 1<=pages<=10:return {'error':'ocr_page_limit'}
    deadline=time.monotonic()+50
    fragments=[]
    try:
        if kind!='pdf':image_size(raw,kind)
        for number in range(1,pages+1):
            image=raw
            if kind=='pdf':
                remaining=deadline-time.monotonic()
                if remaining<=0:return {'error':'ocr_timeout'}
                code,image=execute(['/usr/bin/pdftoppm','-f',str(number),'-l',str(number),'-singlefile','-scale-to','1600','-png','/input/document'],files={'/input/document':raw},timeout=min(20,remaining))
                if code:return {'error':'ocr_failed'}
            remaining=deadline-time.monotonic()
            if remaining<=0:return {'error':'ocr_timeout'}
            code,output=execute(['/ocr/usr/bin/tesseract','/input/document','stdout','--tessdata-dir','/ocr/usr/share/tesseract-ocr/4.00/tessdata','-l','spa+eng','--psm','3','tsv'],files={'/input/document':image},ocr_runtime=runtime,timeout=min(25,remaining))
            if code:return {'error':'ocr_failed'}
            fragments.append(parse_tsv(output,number))
        if sum(len(f['text']) for f in fragments)>2000000:return {'error':'text_limit'}
        return {'fragments':fragments}
    except (OSError,SandboxError,ValueError,KeyError,IndexError) as error:
        return {'error':str(error) if str(error) in {'invalid_image','image_limit','ocr_no_text','text_limit'} else 'ocr_failed'}
