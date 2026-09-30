from unittest.mock import patch
from django.test import TestCase
from . import test_workflow as fixtures
from .test_providers import result
from .workflow import process_one

class ReportActionTests(TestCase):
    setUp=fixtures.AIWorkflowTests.setUp
    enqueue=fixtures.AIWorkflowTests.enqueue
    def test_report_requires_explicit_policy_and_verified_sources(self):
        self.payload['action']='report'
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.policy.actions=['report'];self.policy.save()
        self.payload['fragment_ids']=[]
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['fragment_ids']=[self.fragment.pk];job=self.enqueue()
        output={'result':result(),'input_tokens':10,'output_tokens':20,'latency_ms':1}
        with patch('core.ai.workflow.invoke',return_value=output):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result)
    def test_report_is_cited_draft_without_application_or_answer_disclosure(self):
        self.policy.actions=['report'];self.policy.save();self.payload['action']='report';job=self.enqueue()
        output=fixtures.AIWorkflowTests.output(self)
        output['result'].update(status='needs_information',suggested_fields=[],plain_explanation='Synthetic draft from the selected source.')
        with patch('core.ai.workflow.invoke',return_value=output) as invoke:process_one()
        job.refresh_from_db();self.assertEqual(job.state,'ready');self.assertNotIn('answer',invoke.call_args.args[3])
        self.assertEqual(self.client.post(f'/api/v1/ai/requests/{job.pk}/',format='json').status_code,400)
        self.answer.refresh_from_db();self.assertEqual(self.answer.version,1)
