import uuid
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from core.models import AIFragmentRelease,EvidenceFragment
from . import test_workflow as fixtures
from .test_providers import result
from .workflow import process_one

class ContradictionTests(TestCase):
    enqueue=fixtures.AIWorkflowTests.enqueue
    def setUp(self):
        fixtures.AIWorkflowTests.setUp(self)
        self.second=EvidenceFragment.objects.create(extraction=self.doc.extraction,ordinal=2,locator='synthetic paragraph 2',text='Synthetic second version of the procedure.')
        first=AIFragmentRelease.objects.get(fragment=self.fragment)
        self.release=AIFragmentRelease.objects.create(fragment=self.second,provider='openai',reviewer=self.reviewer,classification='public',expires=first.expires,rationale='Synthetic comparison fixture')
        self.policy.actions=['suggest','contradictions'];self.policy.save()
        self.payload.update(action='contradictions',fragment_ids=[self.fragment.pk,self.second.pk])
    def output(self,conflicts=True):
        data=result()
        data['plain_explanation']='Two synthetic sources require human clarification.'
        data['citations']=[dict(fragment_id=f.pk,locator=f.locator,quote=f.text,document_sha256=self.doc.sha256) for f in [self.fragment,self.second]]
        data['conflicts']=[dict(description='Possible synthetic conflict.',fragment_ids=[self.fragment.pk,self.second.pk])] if conflicts else []
        return dict(result=data,input_tokens=20,output_tokens=30,latency_ms=1)
    def test_two_distinct_authorized_fragments_required(self):
        for ids in [[],[self.fragment.pk],[self.fragment.pk,self.fragment.pk]]:
            self.payload['fragment_ids']=ids
            self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['fragment_ids']=[self.fragment.pk,self.second.pk]
        self.release.revoked_at=timezone.now();self.release.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
    def test_cited_comparison_never_applies_or_sends_answer(self):
        job=self.enqueue();self.assertEqual(job.pk,self.enqueue().pk)
        with patch('core.ai.workflow.invoke',return_value=self.output()) as invoke:process_one()
        context=invoke.call_args.args[3]
        self.assertNotIn('answer',context);self.assertEqual(context['action'],'contradictions')
        job.refresh_from_db();self.assertEqual(job.state,'ready')
        self.assertEqual(self.client.post(f'/api/v1/ai/requests/{job.pk}/',format='json').status_code,400)
        self.answer.refresh_from_db();self.assertEqual(self.answer.version,1)
    def test_no_conflicts_is_a_valid_limited_observation(self):
        job=self.enqueue()
        with patch('core.ai.workflow.invoke',return_value=self.output(False)):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'ready');self.assertEqual(job.result['conflicts'],[])
    def test_missing_citation_and_clarification_fail_closed(self):
        for failure in ['citation','clarification','duplicate','invented']:
            self.payload['client_key']=str(uuid.uuid4());job=self.enqueue();output=self.output()
            if failure=='citation':output['result']['citations'].pop()
            if failure=='clarification':output['result']['follow_up_questions']=[]
            if failure=='duplicate':output['result']['conflicts'][0]['fragment_ids']=[self.fragment.pk]*2
            if failure=='invented':output['result']['citations'][1]['quote']='Invented quotation'
            with patch('core.ai.workflow.invoke',return_value=output):process_one()
            job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result)
            # Keep the circuit-breaker out of this output-contract test.
            job.reserved_tokens=0;job.save(update_fields=['reserved_tokens'])
    def test_revocation_during_comparison_discards_output(self):
        job=self.enqueue()
        def revoke(*args,**kwargs):
            self.release.revoked_at=timezone.now();self.release.save();return self.output()
        with patch('core.ai.workflow.invoke',side_effect=revoke):process_one()
        job.refresh_from_db();self.assertEqual(job.state,'failed');self.assertIsNone(job.result)
    def test_policy_does_not_implicitly_enable_comparison(self):
        self.policy.actions=['suggest'];self.policy.save()
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
