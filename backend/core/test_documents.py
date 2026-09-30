import tempfile
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,SimpleTestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from . import tests as fixtures
from .models import EvidenceDocument,EvidenceExtraction,EvidenceFragment,EvidenceReview,RoleAssignment
from .workflow import save_answer
from .documents import run_parser,claim,finish,process_one

class ParserTests(SimpleTestCase):
    def test_lines_and_csv_multiline_literal_formulas(self):
        data=run_parser(b'first\n\nthird','txt')['fragments']
        self.assertEqual([x['locator'] for x in data],['Línea 1','Línea 3'])
        data=run_parser(b'name,value\n"two\nlines",=1+1','csv')['fragments']
        self.assertEqual(data[1]['locator'],'Fila 2, líneas 2–3')
        self.assertEqual(data[1]['cells'],['two\nlines','=1+1'])
    def test_rejects_invalid_and_limits_without_partial_text(self):
        for raw,kind,error in [(b'"unfinished','csv','invalid_csv'),(b'\xff','txt','invalid_utf8'),(b'\x00','txt','binary_content'),(b' \n','txt','empty_document'),(b'a\n'*10001,'txt','fragment_limit'),(b'x'*2000001,'txt','text_limit'),(b'x','pdf','unsupported_format')]:
            self.assertEqual(run_parser(raw,kind),{'error':error})
    def test_timeout_is_reported_without_document_content(self):
        import subprocess
        with patch('core.documents.subprocess.run',side_effect=subprocess.TimeoutExpired('parser',8)):
            self.assertEqual(run_parser(b'private','txt'),{'error':'timeout'})

class DocumentTests(TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        self.folder=tempfile.TemporaryDirectory(prefix='salud-doc-test-');self.addCleanup(self.folder.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.folder.name);self.override.enable();self.addCleanup(self.override.disable)
        self.answer=save_answer(self.author,self.answer.pk,0,'Synthetic declaration','known')
        self.client=APIClient();self.client.force_authenticate(self.author)
    def upload(self,name='test.txt',raw=b'first\nsecond',status=201):
        self.answer.refresh_from_db()
        response=self.client.post(f'/api/v1/answers/{self.answer.pk}/evidence/',{'version':self.answer.etag,'file':SimpleUploadedFile(name,raw)},format='multipart')
        self.assertEqual(response.status_code,status,response.data)
        if status==201:return EvidenceDocument.objects.latest('created_at')
    def review(self,doc,decision='accepted',version=0,status=200,**extra):
        response=self.client.post(f'/api/v1/evidence/{doc.pk}/',{'version':version,'decision':decision,'rationale':'Synthetic independent review','valid_until':str(timezone.localdate()+timedelta(days=5)) if decision=='accepted' else None,**extra},format='json')
        self.assertEqual(response.status_code,status,response.data);return response.data
    def test_upload_extract_and_review_do_not_validate_answer(self):
        doc=self.upload();self.assertEqual(doc.extraction.state,'pending')
        import os,stat
        self.assertEqual(stat.S_IMODE(os.stat(doc.file.path).st_mode),0o600)
        self.client.force_authenticate(self.reviewer);self.review(doc,status=400)
        call_command('extract_evidence');call_command('extract_evidence')
        self.assertEqual(EvidenceFragment.objects.count(),2)
        result=self.review(doc);self.assertEqual(result['state'],'accepted');self.assertTrue(result['is_current'])
        self.review(doc,status=409)
        self.review(doc,'returned',version=1)
        self.assertEqual(EvidenceReview.objects.count(),2)
        self.answer.refresh_from_db();self.assertEqual(self.answer.state,'draft')
    def test_permissions_self_review_foreign_and_revoked(self):
        doc=self.upload();process_one();self.review(doc,status=403)
        RoleAssignment.objects.create(user=self.author,service=self.service,role='manager',starts=timezone.localdate(),ends=timezone.localdate()+timedelta(days=1),approved_by=self.admin)
        self.review(doc,status=400)
        for user in [self.other,self.admin]:
            self.client.force_authenticate(user)
            for suffix in ['', 'fragments/', 'download/']:
                self.assertEqual(self.client.get(f'/api/v1/evidence/{doc.pk}/{suffix}').status_code,404)
        self.client.force_authenticate(self.reviewer)
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=timezone.now())
        self.review(doc,status=404)
    def test_integrity_failure_and_lease_recovery_fences_old_worker(self):
        doc=self.upload();first=claim();self.assertIsNone(claim())
        EvidenceExtraction.objects.filter(document=doc).update(leased_until=timezone.now()-timedelta(seconds=1))
        second=claim();self.assertNotEqual(first[1],second[1])
        self.assertFalse(finish(*first,{'fragments':[]}))
        self.assertTrue(finish(*second,{'error':'timeout'}))
        self.assertEqual(EvidenceFragment.objects.count(),0)
        doc2=self.upload('other.txt');doc2.file.save('changed.txt',SimpleUploadedFile('changed.txt',b'changed'))
        process_one();doc2.extraction.refresh_from_db();self.assertEqual(doc2.extraction.error,'digest_mismatch')
    def test_csv_pagination_and_history_context(self):
        doc=self.upload('table.csv',b'one,two\n'*51);process_one()
        data=self.client.get(f'/api/v1/evidence/{doc.pk}/fragments/').data
        self.assertEqual(len(data['fragments']),50);self.assertTrue(data['has_next'])
        self.assertEqual(len(self.client.get(f'/api/v1/evidence/{doc.pk}/fragments/?page=2').data['fragments']),1)
        self.answer.refresh_from_db();save_answer(self.author,self.answer.pk,self.answer.etag,'Changed answer','known')
        self.assertFalse(self.client.get(f'/api/v1/evidence/{doc.pk}/').data['is_current'])
    def test_expiry_and_invalid_fields(self):
        doc=self.upload();process_one();self.client.force_authenticate(self.reviewer)
        self.review(doc,status=400,valid_until=str(timezone.localdate()-timedelta(days=1)))
        self.review(doc,status=400,unexpected=True)
        self.review(doc)
        EvidenceReview.objects.filter(document=doc).update(valid_until=timezone.localdate()-timedelta(days=1))
        self.assertTrue(self.client.get(f'/api/v1/evidence/{doc.pk}/').data['expired'])
    def test_blocked_formats_and_empty_document(self):
        self.upload('bad.pdf',b'%PDF-1.7',400);self.upload('bad.docx',b'PK',400);self.upload(raw=b'',status=400)
    def test_legacy_backfill_and_attempt_limit(self):
        doc=self.upload();doc.extraction.delete();call_command('extract_evidence')
        self.assertEqual(EvidenceFragment.objects.count(),2)
        other=self.upload('another.txt');EvidenceExtraction.objects.filter(document=other).update(attempts=3)
        process_one();other.extraction.refresh_from_db();self.assertEqual(other.extraction.error,'attempt_limit')

    def test_manual_retry_has_version_and_attempt_limit(self):
        doc=self.upload()
        with patch('core.documents.run_parser',return_value={'error':'timeout'}):process_one()
        url=f'/api/v1/evidence/{doc.pk}/retry/'
        self.assertTrue(self.client.get(f'/api/v1/evidence/{doc.pk}/').data['can_retry'])
        self.assertEqual(self.client.post(url,{'version':0},format='json').status_code,200)
        self.assertEqual(self.client.post(url,{'version':0},format='json').status_code,409)
        process_one();doc.extraction.refresh_from_db();self.assertEqual(doc.extraction.state,'ready')
        self.assertEqual(self.client.post(url,{'version':1},format='json').status_code,400)
        EvidenceExtraction.objects.filter(document=doc).update(state='failed',attempts=3)
        self.assertEqual(self.client.post(url,{'version':1},format='json').status_code,400)

    def test_document_metadata_is_hidden_without_document_role(self):
        self.upload()
        RoleAssignment.objects.create(user=self.other,service=self.service,role='director',starts=timezone.localdate(),ends=timezone.localdate()+timedelta(days=1),approved_by=self.admin)
        self.client.force_authenticate(self.other)
        response=self.client.get(f'/api/v1/answers/{self.answer.pk}/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['evidence'],[])
