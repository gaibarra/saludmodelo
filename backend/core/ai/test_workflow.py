import tempfile
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from core import tests as fixtures
from core.models import AIServicePolicy,AIFragmentRelease,AIRequest,EvidenceDocument,RoleAssignment
from core.workflow import save_answer
from core.documents import process_one as extract
from .workflow import process_one
from .test_providers import result

class AIWorkflowTests(TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        self.folder=tempfile.TemporaryDirectory(prefix='salud-ai-test-');self.addCleanup(self.folder.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.folder.name,DOCUMENT_SIGNATURES='',AI_EXTERNAL_ENABLED=True,AI_KEYS={'openai':'synthetic-key'},AI_MODELS={'openai':{'model':'synthetic-model','max_output_tokens':1000,'input_per_million':'1','output_per_million':'2','rates_verified_on':timezone.localdate().isoformat()}})
        self.override.enable();self.addCleanup(self.override.disable)
        self.answer=save_answer(self.author,self.answer.pk,0,'Unconfirmed statement','known')
        self.client=APIClient();self.client.force_authenticate(self.author)
        response=self.client.post(f'/api/v1/answers/{self.answer.pk}/evidence/',{'version':self.answer.etag,'file':SimpleUploadedFile('synthetic.txt',b'Synthetic public procedure.')},format='multipart')
        self.assertEqual(response.status_code,201,response.data);extract()
        self.doc=EvidenceDocument.objects.get();self.fragment=self.doc.extraction.fragments.get()
        self.client.force_authenticate(self.reviewer)
        response=self.client.post(f'/api/v1/evidence/{self.doc.pk}/',{'version':0,'decision':'accepted','rationale':'Synthetic verification','valid_until':str(timezone.localdate()+timedelta(days=10))},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.release_data={'fragment_ids':[self.fragment.pk],'provider':'openai','classification':'public','expires':str(timezone.localdate()+timedelta(days=5)),'rationale':'Synthetic public information'}
        self.assertEqual(self.client.post(f'/api/v1/ai/releases/{self.instance.pk}/',self.release_data,format='json').status_code,201)
        self.policy=AIServicePolicy.objects.create(service=self.service,approved_by=self.reviewer,enabled=True,providers=['openai'],monthly_calls=10,monthly_user_calls=5,monthly_tokens=1000000,monthly_cost_limit=10,rationale='Synthetic policy')
        self.client.force_authenticate(self.author)
        self.answer.refresh_from_db()
        self.url=f'/api/v1/ai/questions/{self.instance.pk}/'
        self.payload={'provider':'openai','fragment_ids':[self.fragment.pk],'version':self.answer.etag,'client_key':str(uuid.uuid4())}
    def enqueue(self):
        r=self.client.post(self.url,self.payload,format='json');self.assertEqual(r.status_code,202,r.data);return AIRequest.objects.get(pk=r.data['id'])
    def output(self):
        return {'result':{**result(),'status':'proposal','suggested_fields':[{'field_id':'answer','value':'Synthetic proposal','origin':'ai_proposal','fragment_ids':[self.fragment.pk]}],'citations':[{'fragment_id':self.fragment.pk,'locator':self.fragment.locator,'quote':self.fragment.text,'document_sha256':self.doc.sha256}],'support_level':'partial'},'input_tokens':50,'output_tokens':80,'latency_ms':10}
    def test_idempotency_verified_proposal_and_application_remain_unconfirmed(self):
        job=self.enqueue();self.assertEqual(self.enqueue().pk,job.pk)
        with patch('core.ai.workflow.invoke',return_value=self.output()) as invoke:
            self.assertTrue(process_one());self.assertFalse(process_one());invoke.assert_called_once()
            context=invoke.call_args.args[3];self.assertNotIn('answer',context);self.assertNotIn('synthetic.txt',str(context))
        job.refresh_from_db();self.assertEqual(job.state,'ready');self.assertGreater(job.reserved_tokens,0)
        url=f'/api/v1/ai/requests/{job.pk}/'
        self.assertEqual(self.client.get(url).status_code,200)
        response=self.client.post(url,format='json');self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['state'],'draft');self.assertEqual(response.data['revisions'][0]['knowledge'],'unconfirmed')
        self.assertEqual(self.client.post(url,format='json').data['version'],2)
        job.refresh_from_db();self.assertEqual(job.applied_revision.version,2)
    def test_offline_fallback_and_foreign_scope(self):
        with override_settings(AI_EXTERNAL_ENABLED=False),patch('core.ai.workflow.invoke') as invoke:
            self.assertEqual(self.client.get(self.url).data['providers'],[])
            self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
            process_one();invoke.assert_not_called()
        self.client.force_authenticate(self.other);self.assertEqual(self.client.get(self.url).status_code,404)
    def test_self_release_expiry_revocation_and_stale_answer(self):
        self.assertEqual(self.client.post(f'/api/v1/ai/releases/{self.instance.pk}/',self.release_data,format='json').status_code,404)
        RoleAssignment.objects.filter(user=self.author).update(role='manager')
        self.assertEqual(self.client.post(f'/api/v1/ai/releases/{self.instance.pk}/',self.release_data,format='json').status_code,400)
        release=AIFragmentRelease.objects.get();release.expires=timezone.localdate()-timedelta(days=1);release.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        release.expires=timezone.localdate()+timedelta(days=1);release.revoked_at=timezone.now();release.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        release.revoked_at=None;release.save();save_answer(self.author,self.answer.pk,self.answer.etag,'Changed','known')
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,409)
    def test_budget_and_quota_block_before_network(self):
        for field in ['monthly_calls','monthly_user_calls','monthly_tokens','monthly_cost_limit']:
            with self.subTest(field=field):
                job=self.enqueue();setattr(self.policy,field,0);self.policy.save()
                with patch('core.ai.workflow.invoke') as invoke:process_one();invoke.assert_not_called()
                job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertEqual(job.reserved_tokens,0)
                setattr(self.policy,field,1000000 if field=='monthly_tokens' else 10);self.policy.save()
                self.payload['client_key']=str(uuid.uuid4())
    def test_fabricated_citation_fails_and_consumes_reserved_budget(self):
        job=self.enqueue();output=self.output();output['result']['citations'][0]['quote']='Not in the original'
        with patch('core.ai.workflow.invoke',return_value=output):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result);self.assertGreater(job.reserved_cost,0)
    def test_revocation_during_request_discards_result(self):
        job=self.enqueue()
        def revoke(*args,**kwargs):
            AIFragmentRelease.objects.update(revoked_at=timezone.now());return self.output()
        with patch('core.ai.workflow.invoke',side_effect=revoke):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result)
    def test_policy_revoked_during_request_discards_result(self):
        job=self.enqueue()
        def revoke(*args,**kwargs):
            AIServicePolicy.objects.update(enabled=False);return self.output()
        with patch('core.ai.workflow.invoke',side_effect=revoke):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result)
    def test_stale_proposal_cannot_overwrite_answer(self):
        job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output()):process_one()
        save_answer(self.author,self.answer.pk,self.answer.etag,'Changed','known')
        url=f'/api/v1/ai/requests/{job.pk}/'
        self.assertEqual(self.client.get(url).status_code,409);self.assertEqual(self.client.post(url,format='json').status_code,409)
    def test_cancel_before_network_and_during_call_ignores_late_completion(self):
        job=self.enqueue();url=f'/api/v1/ai/requests/{job.pk}/decision/'
        self.assertEqual(self.client.post(url,{'decision':'cancel'},format='json').status_code,200)
        with patch('core.ai.workflow.invoke') as invoke:process_one();invoke.assert_not_called()
        self.payload['client_key']=str(uuid.uuid4());job=self.enqueue();url=f'/api/v1/ai/requests/{job.pk}/decision/'
        def cancel(*args,**kwargs):
            self.assertEqual(self.client.post(url,{'decision':'cancel'},format='json').status_code,200);return self.output()
        with patch('core.ai.workflow.invoke',side_effect=cancel):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'cancelled');self.assertIsNone(job.result);self.assertGreater(job.reserved_cost,0)
    def test_reject_preserves_audit_and_does_not_modify_answer(self):
        job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output()):process_one()
        url=f'/api/v1/ai/requests/{job.pk}/decision/'
        self.assertEqual(self.client.post(url,{'decision':'reject'},format='json').status_code,200)
        self.assertEqual(self.client.post(f'/api/v1/ai/requests/{job.pk}/',format='json').status_code,400)
        self.answer.refresh_from_db();self.assertEqual(self.answer.version,1)
        job.refresh_from_db();self.assertEqual(job.state,'rejected');self.assertIsNotNone(job.result)
    def test_policy_requires_director_scope_and_current_version(self):
        url=f'/api/v1/ai/policies/{self.service.pk}/'
        data={'version':0,'enabled':True,'providers':['openai'],'monthly_calls':10,'monthly_user_calls':5,'monthly_tokens':1000000,'monthly_cost_limit':'1.000000','rationale':'Synthetic approved budget'}
        self.assertEqual(self.client.post(url,data,format='json').status_code,404)
        RoleAssignment.objects.filter(user=self.reviewer).update(role='director');self.client.force_authenticate(self.reviewer)
        response=self.client.post(url,data,format='json');self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['monthly_user_calls'],5)
        self.assertEqual(self.client.post(url,data,format='json').status_code,409)
        self.assertEqual(self.client.post(url,{**data,'version':1,'monthly_user_calls':0},format='json').status_code,400)
