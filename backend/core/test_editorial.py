import hashlib
import json
import uuid
from datetime import date, timedelta
from django.conf import settings
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from . import test_administration as fixtures
from .models import *
from .help_drafts import catalog
from .publication import HELP_FIELDS

class CatalogTests(SimpleTestCase):
    def test_all_177_questions_and_citations_match_preserved_source(self):
        records={r['stable_id']:r for r in json.loads((settings.BASE_DIR.parent/'imports/source-inventory.json').read_text())}
        data=catalog()
        self.assertEqual(data['source_sha256'],hashlib.sha256((settings.BASE_DIR.parent/'Plan_Trabajo_Escuela_Salud_Modelo.docx').read_bytes()).hexdigest())
        expected={key for key,r in records.items() if r['kind'] in {'question_original','question_compliance','question_additional'}}
        self.assertEqual(set(data['questions']),expected)
        self.assertEqual(len(expected),177)
        self.assertEqual(data['status'],'draft_requires_human_review')
        for key,entry in data['questions'].items():
            self.assertEqual(entry['question_text'],records[key]['text'])
            self.assertEqual(entry['question_sha256'],hashlib.sha256(records[key]['text'].encode()).hexdigest())
            self.assertEqual(set(entry['content']),set(HELP_FIELDS))
            self.assertTrue(all(0<len(v)<=5000 for v in entry['content'].values()))
            self.assertIn('Ejemplo ficticio',entry['content']['fictional_example'])
            for ref in entry['references']:
                record=records[ref['stable_id']]
                self.assertEqual(ref['locator'],record['locator'])
                self.assertEqual(ref['text_sha256'],hashlib.sha256(record['text'].encode()).hexdigest())

class EditorialTests(TestCase):
    setUpFixture=fixtures.AdministrationTests.setUp
    post=fixtures.AdministrationTests.post
    select=fixtures.AdministrationTests.select
    help_cycle=fixtures.AdministrationTests.help_cycle
    def setUp(self):
        self.setUpFixture()
        self.instance=self.select()
        data=catalog(); key='Unidad de odontología::6'; entry=data['questions'][key]
        source=self.qv.source; batch=source.batch;batch.digest=data['source_sha256'];batch.save()
        records={r['stable_id']:r for r in json.loads((settings.BASE_DIR.parent/'imports/source-inventory.json').read_text())}
        for ref in entry['references']:
            record=records[ref['stable_id']]
            values={k:record[k] for k in ('stable_id','locator','section','text','kind','links')}
            if ref['stable_id']==key:
                for k,v in values.items():setattr(source,k,v)
                source.save()
            else:SourceRecord.objects.create(batch=batch,**values)
        question=self.qv.question;question.stable_id=key;question.save()
        self.client.force_authenticate(self.writer)
    def preview(self,status=200):
        response=self.client.get(f'/api/v1/questionnaires/{self.instance.pk}/draft/')
        self.assertEqual(response.status_code,status,response.data);return response.data
    def test_preview_is_read_only_and_adapted_draft_keeps_sources_without_approval(self):
        data=self.preview();self.assertEqual(HelpRevision.objects.count(),0)
        content={**data['content'],'purpose':'Adaptación sintética del servicio'}
        result=self.post(f'questionnaires/{self.instance.pk}/help/',{'version':0,'content':content,'proposal_digest':data['digest']})
        revision=HelpRevision.objects.get()
        self.assertEqual(revision.origin,'source_draft_edited');self.assertEqual(revision.source_links.count(),len(data['references']))
        self.assertFalse(result['published']);self.assertEqual(HelpReview.objects.count(),0)
    def test_tampered_or_other_instance_digest_is_rejected(self):
        data=self.preview()
        self.post(f'questionnaires/{self.instance.pk}/help/',{'version':0,'content':data['content'],'proposal_digest':'0'*64},409)
        self.assertEqual(HelpRevision.objects.count(),0)
        other=QuestionnaireInstance.objects.create(service=self.other_service,question_version=self.qv)
        CatalogAccess.objects.create(institution=self.foreign,batch=self.qv.source.batch,granted_by=self.operator)
        self.client.force_authenticate(self.outsider)
        self.post(f'questionnaires/{other.pk}/help/',{'version':0,'content':data['content'],'proposal_digest':data['digest']},409)
        self.preview(404)
    def test_source_changes_or_withdrawn_catalog_fail_closed(self):
        SourceRecord.objects.filter(pk=self.qv.source_id).update(text='Changed original')
        self.preview(404)
    def test_missing_citation_rejects_preview(self):
        SourceRecord.objects.exclude(pk=self.qv.source_id).delete();self.preview(400)
    def test_withdrawn_catalog_rejects_preview(self):
        CatalogAccess.objects.all().delete();self.preview(404)

class ConsultationTests(TestCase):
    setUp=fixtures.AdministrationTests.setUp
    post=fixtures.AdministrationTests.post
    select=fixtures.AdministrationTests.select
    help_cycle=fixtures.AdministrationTests.help_cycle
    def open(self):
        self.instance=self.select();self.help_cycle(self.instance)
        self.client.force_authenticate(self.writer)
        self.payload={'instance':self.instance.pk,'assigned_to':self.reviewer.pk,'question':'Duda sintética sobre recursos','due':str(max(date(2026,10,1),timezone.localdate()+timedelta(days=1))),'client_key':str(uuid.uuid4())}
        return self.post('consultations/',self.payload,201)
    def message(self,obj,body='Respuesta sintética',status=200,key=None):
        return self.post(f"consultations/{obj['id']}/message/",{'version':obj['etag'],'body':body,'client_key':key or str(uuid.uuid4())},status)
    def test_idempotency_conflicts_and_resolution_preserve_help_and_answer(self):
        obj=self.open();answer=Answer.objects.get(instance=self.instance);before=(answer.state,answer.etag,HelpReview.objects.count(),HelpRevision.objects.count())
        self.assertEqual(self.post('consultations/',self.payload,201)['id'],obj['id'])
        self.post('consultations/',{**self.payload,'question':'Different'},400)
        self.assertEqual(ClarificationRequest.objects.count(),1)
        self.assertEqual(obj['help_version'],1)
        self.post(f"consultations/{obj['id']}/resolve/",{'version':0,'rationale':'Too early'},400)
        self.client.force_authenticate(self.reviewer)
        key=str(uuid.uuid4());replied=self.message(obj,key=key)
        self.message(obj,key=key);self.assertEqual(ClarificationMessage.objects.count(),1)
        self.message(obj,status=409)
        self.post(f"consultations/{obj['id']}/resolve/",{'version':replied['etag'],'rationale':'Wrong actor'},403)
        self.client.force_authenticate(self.writer)
        reopened=self.message(replied,'Necesito aclaración');self.assertEqual(reopened['state'],'open')
        self.client.force_authenticate(self.reviewer);answered=self.message(reopened)
        self.client.force_authenticate(self.writer)
        closed=self.post(f"consultations/{obj['id']}/resolve/",{'version':answered['etag'],'rationale':'Duda aclarada'})
        self.assertEqual(closed['state'],'resolved');self.message(closed,status=400)
        answer.refresh_from_db();self.assertEqual(before,(answer.state,answer.etag,HelpReview.objects.count(),HelpRevision.objects.count()))
    def test_participants_only_and_revocation_removes_access(self):
        obj=self.open()
        RoleAssignment.objects.create(user=self.outsider,service=self.service,role='manager',starts=self.start,ends=self.end,approved_by=self.director)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get('/api/v1/consultations/').data['count'],0)
        self.assertEqual(self.client.get(f"/api/v1/consultations/{obj['id']}/").status_code,404)
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=timezone.now())
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.client.get(f"/api/v1/consultations/{obj['id']}/").status_code,404)
        self.message(obj,status=404)
    def test_invalid_recipients_dates_and_fields(self):
        self.open()
        for changes in [{'assigned_to':self.outsider.pk},{'assigned_to':self.writer.pk},{'due':'2026-09-01'},{'state':'resolved'}]:
            self.post('consultations/',{**self.payload,'client_key':str(uuid.uuid4()),**changes},400)
        people=self.client.get(f'/api/v1/consultations/recipients/?instance={self.instance.pk}').data['people']
        self.assertEqual([p['id'] for p in people],[self.reviewer.pk])

    def test_expiration_removes_participant_access(self):
        obj=self.open()
        RoleAssignment.objects.filter(user=self.writer).update(ends=self.start)
        self.assertEqual(self.client.get('/api/v1/consultations/').data['count'],0)
        self.message(obj,status=404)
