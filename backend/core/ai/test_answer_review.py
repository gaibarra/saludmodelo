import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from core.models import AIAnswerRelease,AIRequest,RoleAssignment
from core.workflow import save_answer
from . import test_workflow as fixtures
from .test_providers import result
from .workflow import process_one

class AnswerReviewTests(TestCase):
    setUp=fixtures.AIWorkflowTests.setUp
    enqueue=fixtures.AIWorkflowTests.enqueue
    def release(self):
        self.policy.actions=['suggest','review'];self.policy.save()
        self.client.force_authenticate(self.reviewer)
        response=self.client.post(f'/api/v1/ai/answer-releases/{self.instance.pk}/',{'version':self.answer.etag,'provider':'openai','classification':'public','expires':str(timezone.localdate()+timedelta(days=2)),'rationale':'Synthetic text, independently checked','checked':True},format='json')
        self.assertEqual(response.status_code,201,response.data)
        self.client.force_authenticate(self.author)
        self.payload.update(action='review',answer_release_id=response.data['id'],confirm_answer_send=True,fragment_ids=[])
        return AIAnswerRelease.objects.get(pk=response.data['id'])
    def output(self):
        return {'result':result(),'input_tokens':20,'output_tokens':30,'latency_ms':1}
    def test_review_exact_saved_text_no_write_and_explicit_confirmation(self):
        release=self.release()
        self.payload['confirm_answer_send']=False
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['confirm_answer_send']=True
        job=self.enqueue();self.assertEqual(self.enqueue().pk,job.pk)
        with patch('core.ai.workflow.invoke',return_value=self.output()) as invoke:process_one()
        self.assertEqual(invoke.call_args.args[3]['answer'],{'version':self.answer.version,'text':release.revision.content})
        job.refresh_from_db();self.assertEqual(job.state,'ready')
        self.assertEqual(self.client.post(f'/api/v1/ai/requests/{job.pk}/',format='json').status_code,400)
        self.answer.refresh_from_db();self.assertEqual(self.answer.version,1)
    def test_other_actions_cannot_send_answer_and_release_bound_to_provider(self):
        self.release()
        self.payload['action']='suggest'
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['action']='review';self.payload['provider']='deepseek'
        self.policy.providers=['openai','deepseek'];self.policy.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
    def test_independent_reviewer_and_foreign_scope(self):
        self.release()
        self.client.force_authenticate(self.other)
        path=f'/api/v1/ai/answer-releases/{self.instance.pk}/'
        self.assertEqual(self.client.get(path).status_code,404)
        self.client.force_authenticate(self.author)
        RoleAssignment.objects.filter(user=self.author).update(role='manager')
        data={'version':self.answer.etag,'provider':'openai','classification':'public','expires':str(timezone.localdate()+timedelta(days=1)),'rationale':'Invalid self approval','checked':True}
        self.assertEqual(self.client.post(path,data,format='json').status_code,400)
    def test_expired_revoked_and_reviewer_access_removed(self):
        release=self.release()
        release.expires=timezone.localdate()-timedelta(days=1);release.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        release.expires=timezone.localdate()+timedelta(days=1);release.revoked_at=timezone.now();release.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        release.revoked_at=None;release.save()
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=timezone.now())
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,403)
        listing=self.client.get(f'/api/v1/ai/answer-releases/{self.instance.pk}/')
        self.assertFalse(listing.data['releases'][0]['usable'])
    def test_change_before_send_and_revocation_during_send(self):
        release=self.release();job=self.enqueue()
        self.answer=save_answer(self.author,self.answer.pk,self.answer.etag,'New saved statement','known')
        with patch('core.ai.workflow.invoke') as invoke:process_one();invoke.assert_not_called()
        job.refresh_from_db();self.assertEqual(job.state,'failed')
        self.payload.update(version=self.answer.etag,client_key=str(uuid.uuid4()))
        release=self.release();job=self.enqueue()
        def revoke(*args,**kwargs):
            self.client.force_authenticate(self.reviewer)
            response=self.client.post(f'/api/v1/ai/answer-releases/{release.pk}/revoke/',format='json')
            self.assertEqual(response.status_code,200)
            self.client.force_authenticate(self.author)
            return self.output()
        with patch('core.ai.workflow.invoke',side_effect=revoke):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result)
    def test_ready_result_blocked_after_text_change_and_hash_tamper(self):
        release=self.release();job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output()):process_one()
        self.assertEqual(self.client.get(f'/api/v1/ai/requests/{job.pk}/').status_code,200)
        release.content_sha256='0'*64;release.save()
        self.assertEqual(self.client.get(f'/api/v1/ai/requests/{job.pk}/').status_code,400)
        self.answer=save_answer(self.author,self.answer.pk,self.answer.etag,'Changed','known')
        self.assertEqual(self.client.get(f'/api/v1/ai/requests/{job.pk}/').status_code,409)
