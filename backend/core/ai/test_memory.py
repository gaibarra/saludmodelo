from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from . import test_answer_review as fixtures
from .workflow import process_one

class AuthorizedMemoryTests(TestCase):
    setUp=fixtures.AnswerReviewTests.setUp
    release=fixtures.AnswerReviewTests.release
    enqueue=fixtures.AnswerReviewTests.enqueue
    output=fixtures.AnswerReviewTests.output
    def prepare(self):
        release=self.release()
        self.policy.actions=['review','interview'];self.policy.save()
        self.payload['action']='interview'
        return release
    def test_review_release_cannot_authorize_interview(self):
        self.prepare()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
    def test_guide_sends_only_explicitly_authorized_revision_with_knowledge(self):
        release=self.prepare();release.purpose='interview';release.save()
        job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output()) as invoke:process_one()
        context=invoke.call_args.args[3]
        self.assertEqual(context['answer'],{'version':release.revision.version,'text':release.revision.content,'knowledge':release.revision.knowledge})
        self.assertNotIn('history',context);self.assertNotIn('interview',context)
        job.refresh_from_db();self.assertEqual(job.state,'ready')
        self.assertEqual(self.client.post(f'/api/v1/ai/requests/{job.pk}/',format='json').status_code,400)
    def test_memory_is_optional_and_requires_confirmation(self):
        release=self.prepare();release.purpose='interview';release.save()
        self.payload['confirm_answer_send']=False
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload.pop('answer_release_id')
        job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output()) as invoke:process_one()
        self.assertNotIn('answer',invoke.call_args.args[3])
        job.refresh_from_db();self.assertEqual(job.state,'ready')
    def test_memory_release_cannot_authorize_review_or_survive_revocation(self):
        release=self.prepare();release.purpose='interview';release.save()
        self.payload['action']='review'
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['action']='interview';job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output()):process_one()
        release.revoked_at=timezone.now();release.save()
        self.assertEqual(self.client.get(f'/api/v1/ai/requests/{job.pk}/').status_code,400)
    def test_independent_release_api_preserves_purpose(self):
        self.prepare();self.client.force_authenticate(self.reviewer)
        data={'version':self.answer.etag,'provider':'openai','purpose':'interview','classification':'public','expires':str(timezone.localdate()),'rationale':'Synthetic explicitly authorized antecedent','checked':True}
        response=self.client.post(f'/api/v1/ai/answer-releases/{self.instance.pk}/',data,format='json')
        self.assertEqual(response.status_code,201,response.data)
        listing=self.client.get(f'/api/v1/ai/answer-releases/{self.instance.pk}/').data
        self.assertEqual(listing['releases'][0]['purpose'],'interview')
        self.assertEqual(listing['releases'][1]['purpose'],'review')
