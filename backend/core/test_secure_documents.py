import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase,TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from . import tests as fixtures
from .models import EvidenceDocument,EvidenceExtraction,EvidenceFragment
from .documents import process_one
from .workflow import save_answer
from .document_sandbox import execute,probe
from .secure_documents import scan,parse_binary
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
from document_fixtures import office,pdf,signatures,BLOCKED

class SandboxTests(SimpleTestCase):
    def test_isolation_network_filesystem_environment_and_read_only_input(self):
        self.assertTrue(probe())
        script=b'''import os,socket
assert not os.path.exists('/home/gaibarra')
assert not os.path.exists('/run')
assert not os.path.exists('/var')
assert not os.path.exists('/etc/passwd')
assert 'DJANGO_SECRET_KEY' not in os.environ
assert open('/input/document').read()=='synthetic'
try: open('/input/document','w').write('changed')
except OSError: pass
else: raise AssertionError('writable original')
print('safe')
'''
        code,out=execute(['/usr/bin/python3','-I','/app/test.py'],files={'/app/test.py':script,'/input/document':b'synthetic'})
        self.assertEqual((code,out.strip()),(0,b'safe'))
    def test_office_pdf_and_rejected_content_in_real_sandbox(self):
        with patch('core.secure_documents.scan',return_value={'security':'clean'}):
            word=parse_binary(office(),'docx');self.assertEqual(len(word['fragments']),2)
            self.assertIn('párrafo 2',word['fragments'][1]['locator'])
            sheet=parse_binary(office('xlsx'),'xlsx');self.assertIn('celda B1',sheet['fragments'][1]['locator'])
            self.assertIn('Fórmula sin evaluar: =1+1',sheet['fragments'][1]['text'])
            self.assertEqual(parse_binary(pdf(),'pdf')['fragments'][0]['locator'],'Página 1')
            self.assertEqual(parse_binary(pdf(''),'pdf')['error'],'ocr_required')
            for extra,error in [({'word/vbaProject.bin':'macro'},'active_content'),({'word/_rels/document.xml.rels':'<Relationships><Relationship TargetMode="External" Target="file:///etc/passwd"/></Relationships>'},'external_reference'),({'word/document.xml':'<!DOCTYPE x [<!ENTITY secret "secret">]><x>&secret;</x>'},'unsafe_xml'),({'../outside':'x'},'invalid_archive')]:
                data=parse_binary(office(extra=extra),'docx');self.assertEqual(data['error'],error);self.assertEqual(data['security'],'blocked')
    def test_zip_bomb_and_duplicate_parts_are_rejected(self):
        with patch('core.secure_documents.scan',return_value={'security':'clean'}):
            self.assertEqual(parse_binary(office(extra={'word/large.xml':'x'*1_000_000}),'docx')['error'],'archive_limit')
            self.assertEqual(parse_binary(b'not a zip','docx')['error'],'invalid_office')
    def test_antivirus_missing_fails_closed(self):
        with override_settings(DOCUMENT_SIGNATURES=''):
            self.assertEqual(parse_binary(pdf(),'pdf')['security'],'unavailable')

class RealScannerTests(SimpleTestCase):
    def test_real_engine_with_private_definitions_and_synthetic_signature(self):
        with tempfile.TemporaryDirectory(prefix='salud-av-test-') as folder:
            with override_settings(DOCUMENT_SIGNATURES=signatures(folder)):
                self.assertEqual(scan(BLOCKED)['security'],'blocked')
                result=parse_binary(pdf(),'pdf')
                self.assertEqual(result['security'],'clean');self.assertIn('fragments',result)

class BinaryDocumentTests(TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        self.folder=tempfile.TemporaryDirectory(prefix='salud-binary-test-');self.addCleanup(self.folder.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.folder.name,DOCUMENT_SIGNATURES='configured-for-mocked-scanner');self.override.enable();self.addCleanup(self.override.disable)
        self.answer=save_answer(self.author,self.answer.pk,0,'Synthetic source','known')
        self.client=APIClient();self.client.force_authenticate(self.author)
    def upload(self):
        response=self.client.post(f'/api/v1/answers/{self.answer.pk}/evidence/',{'version':self.answer.etag,'file':SimpleUploadedFile('fixture.pdf',pdf())},format='multipart')
        self.assertEqual(response.status_code,201,response.data)
        return EvidenceDocument.objects.get()
    def test_quarantine_clean_extraction_and_download_integrity(self):
        doc=self.upload();url=f'/api/v1/evidence/{doc.pk}/download/'
        self.assertEqual(self.client.get(url).status_code,400)
        with patch('core.secure_documents.scan',return_value={'security':'clean'}):process_one()
        doc.refresh_from_db();self.assertEqual(doc.security_state,'clean');self.assertEqual(doc.extraction.state,'ready')
        response=self.client.get(url);self.assertEqual(response.status_code,200)
        Path(doc.file.path).write_bytes(b'changed')
        self.assertEqual(self.client.get(url).status_code,400)
    def test_blocked_document_has_no_fragments_or_download(self):
        doc=self.upload()
        with patch('core.secure_documents.scan',return_value={'error':'security_blocked','security':'blocked'}):process_one()
        doc.refresh_from_db();self.assertEqual(doc.security_state,'blocked');self.assertEqual(EvidenceFragment.objects.count(),0)
        self.assertEqual(self.client.get(f'/api/v1/evidence/{doc.pk}/download/').status_code,400)
        self.client.force_authenticate(self.reviewer)
        response=self.client.post(f'/api/v1/evidence/{doc.pk}/',{'version':0,'decision':'accepted','rationale':'Should be denied','valid_until':'2026-12-15'},format='json')
        self.assertEqual(response.status_code,400)
    def test_unavailable_scanner_cannot_publish_clean_status(self):
        doc=self.upload()
        with override_settings(DOCUMENT_SIGNATURES=''):process_one()
        doc.refresh_from_db();self.assertEqual(doc.security_state,'unavailable');self.assertEqual(doc.extraction.state,'failed')

    def test_ocr_acceptance_requires_explicit_human_comparison(self):
        doc=self.upload()
        payload={'security':'clean','fragments':[{'ordinal':1,'locator':'Página 1 · OCR','text':'Synthetic OCR','cells':None,'method':'ocr','confidence':95.0}]}
        with patch('core.secure_documents.parse_binary',return_value=payload):process_one()
        self.client.force_authenticate(self.reviewer)
        url=f'/api/v1/evidence/{doc.pk}/'
        self.assertTrue(self.client.get(url).data['requires_ocr_check'])
        data={'version':0,'decision':'accepted','rationale':'Cotejo sintético','valid_until':'2026-12-15'}
        self.assertEqual(self.client.post(url,data,format='json').status_code,400)
        result=self.client.post(url,{**data,'ocr_checked':True},format='json')
        self.assertEqual(result.status_code,200,result.data)
        self.assertTrue(doc.reviews.get().ocr_checked)

class OCRTests(SimpleTestCase):
    def test_real_private_ocr_and_limits(self):
        from .secure_documents import ocr
        runtime=Path(__file__).resolve().parents[1]/'vendor/ocr/runtime'
        with override_settings(DOCUMENT_OCR_RUNTIME=str(runtime)):
            result=ocr(pdf('SALUD MODELO TEST DOCUMENT'),'pdf',1)
            self.assertIn('SALUD MODELO',result['fragments'][0]['text'])
            self.assertEqual(result['fragments'][0]['method'],'ocr')
            self.assertGreater(result['fragments'][0]['confidence'],0)
            self.assertEqual(ocr(pdf(),'pdf',11)['error'],'ocr_page_limit')
            self.assertEqual(ocr(b'bad image','png',1)['error'],'invalid_image')
    def test_untrusted_child_output_cannot_inject_model_fields(self):
        from .documents import validate_result
        invalid={'fragments':[{'ordinal':1,'locator':'page1','text':'x','cells':None,'extraction_id':999}]}
        self.assertEqual(validate_result(invalid)['error'],'process_failed')
