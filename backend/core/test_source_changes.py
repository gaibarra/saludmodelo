from django.test import TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from core import tests as fixtures
from core.models import RoleAssignment,ImportBatch,SourceRecord,QuestionVersion,CatalogAccess,QuestionSourceChange,Review,HelpRevision
from core.workflow import save_answer,transition
from core.publication import publish,save_help,review_help,HELP_FIELDS
from rest_framework.exceptions import ValidationError

class SourceChangeTests(TransactionTestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        for user in [self.author,self.reviewer]:RoleAssignment.objects.create(user=user,service=self.service,role='director',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=30),approved_by=self.admin)
        self.instance.refresh_from_db()
        batch=ImportBatch.objects.create(digest='9'*64,filename='Synthetic revision')
        source=SourceRecord.objects.create(batch=batch,stable_id='Q1',locator='p1',section='Synthetic',text='Revised synthetic question',kind='question_original')
        self.target=QuestionVersion.objects.create(question=self.instance.question_version.question,source=source,version=2)
        CatalogAccess.objects.create(institution=self.service.site.campus.institution,batch=batch,granted_by=self.admin)
        self.client=APIClient();self.client.force_authenticate(self.author)
        self.url=f'/api/v1/questionnaires/{self.instance.pk}/source-changes/'
    def propose(self):
        response=self.client.post(self.url,{'version':self.instance.etag,'target':self.target.pk,'rationale':'Synthetic source update'},format='json')
        self.assertEqual(response.status_code,201,response.data);return response.data['id']
    def review(self,pk):return self.client.post(f'/api/v1/source-changes/{pk}/review/',{'approve':True,'rationale':'Independent source review'},format='json')
    def test_approved_source_withdraws_current_but_preserves_history(self):
        answer=save_answer(self.author,self.answer.pk,self.answer.etag,'Retained answer','known');answer=transition(self.author,answer.pk,answer.etag,'submitted','');answer=transition(self.reviewer,answer.pk,answer.etag,'validated','Accepted before upgrade')
        old_help=answer.revisions.get(version=answer.version).help_revision
        pk=self.propose();self.assertEqual(self.review(pk).status_code,400)
        self.client.force_authenticate(self.reviewer);self.assertEqual(self.review(pk).status_code,200)
        self.instance.refresh_from_db();answer.refresh_from_db();old_help.refresh_from_db()
        history=self.client.get(self.url).data['changes'][0]
        self.assertEqual(history['from_text'],'Synthetic question')
        self.assertEqual(history['to_text'],'Revised synthetic question')
        self.assertFalse(self.instance.published);self.assertEqual(self.instance.question_version_id,self.target.pk)
        self.assertEqual(answer.state,'draft');self.assertEqual(Review.objects.count(),1)
        self.assertNotEqual(old_help.question_version_id,self.target.pk)
        with self.assertRaises(ValidationError):publish(self.reviewer,self.instance.pk)
        with self.assertRaises(ValidationError):transition(self.author,answer.pk,answer.etag,'submitted','')
        instance=save_help(self.author,self.instance.pk,self.instance.etag,{k:'New source guidance' for k in HELP_FIELDS})
        instance=review_help(self.reviewer,instance.pk,instance.etag,'approved','New source reviewed');publish(self.reviewer,instance.pk,instance.etag)
        with self.assertRaises(ValidationError):transition(self.author,answer.pk,answer.etag,'submitted','')
    def test_stale_proposal_and_revoked_catalog_cannot_upgrade(self):
        pk=self.propose();self.client.force_authenticate(self.reviewer)
        CatalogAccess.objects.all().delete()
        self.assertEqual(self.review(pk).status_code,404)
        self.assertEqual(QuestionSourceChange.objects.get(pk=pk).state,'pending')
    def test_cross_scope_and_non_direction_denied(self):
        for user in [self.other,self.admin]:
            self.client.force_authenticate(user);self.assertEqual(self.client.get(self.url).status_code,404)
        RoleAssignment.objects.filter(user=self.author,role='director').delete()
        self.client.force_authenticate(self.author);self.assertEqual(self.client.get(self.url).status_code,403)
