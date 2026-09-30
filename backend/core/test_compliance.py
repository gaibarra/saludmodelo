from datetime import timedelta
from pathlib import Path
from django.test import TestCase,SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from . import tests as fixtures
from .models import *
from .workflow import save_answer,transition
from .compliance_catalog import table_entries,enrich
class NormativeCatalogTests(SimpleTestCase):
    def test_literal_rows_are_complete_and_keep_source_links(self):
        rows=table_entries(Path(__file__).resolve().parents[2]/'Plan_Trabajo_Escuela_Salud_Modelo.docx')
        self.assertEqual(len(rows),60);self.assertEqual({r['code'] for r in rows},{f'N{i:02}' for i in range(1,61)})
        self.assertIn('NOM-004-SSA3-2012',rows[0]['title']);self.assertEqual(rows[0]['subject'],'Expediente clínico');self.assertTrue(rows[0]['links'])
class ComplianceTests(TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        RoleAssignment.objects.filter(user=self.author).update(role='manager')
        RoleAssignment.objects.filter(user=self.reviewer).update(role='compliance')
        self.answer=save_answer(self.author,self.answer.pk,0,'Synthetic statement','known')
        self.answer=transition(self.author,self.answer.pk,self.answer.etag,'submitted','')
        self.answer=transition(self.reviewer,self.answer.pk,self.answer.etag,'validated','Synthetic review')
        self.rev=self.answer.revisions.get(version=1)
        self.doc=EvidenceDocument.objects.create(answer=self.answer,revision=self.rev,file='synthetic-only',original_name='Synthetic',sha256='f'*64,uploader=self.author,format='txt',state='accepted')
        EvidenceReview.objects.create(document=self.doc,reviewer=self.reviewer,decision='accepted',rationale='Synthetic review',valid_until=timezone.localdate()+timedelta(days=10))
        batch=ImportBatch.objects.first();CatalogAccess.objects.create(batch=batch,institution=self.service.site.campus.institution,granted_by=self.admin)
        source=SourceRecord.objects.create(batch=batch,stable_id='synthetic-norm',locator='Synthetic row',section='Synthetic',text='N01',kind='regulation')
        self.norm=NormativeEntry.objects.create(source=source,code='N01',title='Synthetic norm',subject='Synthetic',scope_text='Synthetic')
        self.control=SourceRecord.objects.create(batch=batch,stable_id='synthetic-control',locator='Synthetic control',section='Synthetic',text='C01 Synthetic control',kind='annex')
        self.data={'version':0,'norm':self.norm.pk,'control':self.control.pk,'process_name':'Synthetic process','question':self.instance.pk,'owner':self.author.pk,'evidence':[str(self.doc.pk)],'nature':'legal_obligation','numeral':'Synthetic numeral','consulted_version':'Synthetic version','official_url':'https://example.invalid/synthetic','consulted_on':str(timezone.localdate()),'validity':'verified','applicability':'applies','applicability_reason':'Synthetic assumption','obligation':'Synthetic requirement','link_reason':'Synthetic link','next_review':str(timezone.localdate()+timedelta(days=10))}
        self.client=APIClient();self.client.force_authenticate(self.author);self.url=f'/api/v1/compliance/services/{self.service.pk}/'
    def create(self,**changes):
        response=self.client.post(self.url,{**self.data,**changes},format='json');self.assertEqual(response.status_code,201,response.data);return response.data
    def record_test(self,row,result='passed'):
        response=self.client.post(f"/api/v1/compliance/records/{row['id']}/test/",{'version':row['etag'],'procedure':'Synthetic procedure','expected':'Synthetic expected','observed':'Synthetic observed','result':result},format='json');self.assertEqual(response.status_code,200,response.data);return response.data
    def approve(self,row):
        self.client.force_authenticate(self.reviewer)
        return self.client.post(f"/api/v1/compliance/records/{row['id']}/review/",{'version':row['etag'],'decision':'approved','rationale':'Synthetic independent review'},format='json')
    def test_approval_trace_and_changed_answer_requires_new_review(self):
        row=self.record_test(self.create());response=self.approve(row);self.assertEqual(response.status_code,200,response.data);self.assertEqual(response.data['state'],'approved')
        save_answer(self.author,self.answer.pk,self.answer.etag,'Changed declaration','known')
        response=self.client.get(f"/api/v1/compliance/records/{row['id']}/")
        self.assertEqual(response.data['state'],'needs_review');self.assertEqual(ComplianceReview.objects.count(),1)
        self.assertTrue(response.data['history']);self.assertEqual(ComplianceRevision.objects.count(),1)
    def test_pending_validity_and_nonapplicability_never_infer_compliance(self):
        row=self.create(validity='pending',applicability='pending',evidence=[])
        self.assertEqual(self.approve(row).status_code,400)
        self.client.force_authenticate(self.author);row=self.create(applicability='not_applies',evidence=[])
        response=self.approve(row);self.assertEqual(response.status_code,200,response.data);self.assertEqual(response.data['state'],'not_applicable_reviewed')
    def test_self_approval_and_stale_edits_are_rejected(self):
        row=self.record_test(self.create());RoleAssignment.objects.filter(user=self.author).update(role='compliance')
        response=self.client.post(f"/api/v1/compliance/records/{row['id']}/review/",{'version':row['etag'],'decision':'approved','rationale':'Synthetic self review'},format='json');self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.post(f"/api/v1/compliance/records/{row['id']}/",self.data,format='json').status_code,409)
    def test_new_revision_preserves_history_and_resets_approval(self):
        row=self.record_test(self.create());approved=self.approve(row).data
        self.client.force_authenticate(self.author)
        response=self.client.post(f"/api/v1/compliance/records/{row['id']}/",{**self.data,'version':approved['etag'],'obligation':'Changed proposed requirement'},format='json')
        self.assertEqual(response.status_code,200,response.data);self.assertEqual(response.data['state'],'draft');self.assertEqual(response.data['version'],2)
        self.assertEqual(ComplianceReview.objects.count(),1);self.assertEqual(ComplianceRevision.objects.count(),2)
    def test_expired_evidence_and_new_tests_invalidate_effective_review(self):
        row=self.record_test(self.create());approved=self.approve(row).data
        self.client.force_authenticate(self.author);row=self.record_test(approved)
        self.assertEqual(row['state'],'needs_review');self.assertEqual(self.approve(row).data['state'],'approved')
        EvidenceReview.objects.filter(document=self.doc).update(valid_until=timezone.localdate()-timedelta(days=1))
        response=self.client.get(f"/api/v1/compliance/records/{row['id']}/");self.assertEqual(response.data['state'],'needs_review')
    def test_scope_catalog_owner_and_evidence_cannot_be_forged(self):
        row=self.create();self.client.force_authenticate(self.other)
        for url in [self.url,self.url+'options/',self.url+'export/',f"/api/v1/compliance/records/{row['id']}/"]:self.assertEqual(self.client.get(url).status_code,404)
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.post(self.url,{**self.data,'owner':self.other.pk},format='json').status_code,403)
        foreign_question=QuestionnaireInstance.objects.create(service=self.foreign,question_version=self.instance.question_version)
        foreign_answer=Answer.objects.create(instance=foreign_question,version=1)
        foreign_revision=AnswerRevision.objects.create(answer=foreign_answer,version=1,author=self.other,content='Foreign synthetic content')
        foreign_doc=EvidenceDocument.objects.create(answer=foreign_answer,revision=foreign_revision,file='foreign-synthetic',original_name='Foreign',sha256='b'*64,uploader=self.other)
        self.assertEqual(self.client.post(self.url,{**self.data,'evidence':[str(foreign_doc.pk)]},format='json').status_code,400)
        CatalogAccess.objects.all().delete()
        self.assertEqual(self.client.post(self.url,self.data,format='json').status_code,404)
    def test_export_is_private_versioned_scoped_and_audited(self):
        row=self.create();response=self.client.get(self.url+'export/',HTTP_ACCEPT='text/html,application/xhtml+xml,*/*;q=0.8')
        self.assertEqual(response.status_code,200);self.assertEqual(response['Cache-Control'],'private, no-store');self.assertEqual(response.data['records'][0]['id'],row['id']);self.assertEqual(response.data['schema_version'],'salud-compliance-1')
        self.assertTrue(AuditEvent.objects.filter(action='compliance.exported',actor=self.author).exists())
