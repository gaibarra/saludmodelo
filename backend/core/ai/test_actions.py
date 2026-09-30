import uuid
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from core.models import AIRequest, AIFragmentRelease
from . import test_workflow as fixtures
from .test_providers import result
from .workflow import process_one


class ActionTests(TestCase):
    setUp = fixtures.AIWorkflowTests.setUp
    enqueue = fixtures.AIWorkflowTests.enqueue

    def authorize(self, action):
        self.policy.actions = ['suggest', action]
        self.policy.save()
        self.payload.update(action=action, client_key=str(uuid.uuid4()))

    def output(self):
        return {'result': result(), 'input_tokens': 30, 'output_tokens': 40, 'latency_ms': 1}

    def test_existing_policy_does_not_authorize_new_action(self):
        self.payload['action'] = 'explain'
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 400)
        self.assertEqual(AIRequest.objects.count(), 0)
        self.payload['action'] = 'unknown'
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 400)

    def test_explain_without_documents_and_action_idempotency(self):
        self.authorize('explain')
        self.payload['fragment_ids'] = []
        job = self.enqueue()
        self.assertEqual(self.enqueue().pk, job.pk)
        self.payload['action'] = 'interview'
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 400)
        output = self.output()
        output['result']['plain_explanation'] = 'Explique el proceso de recepción.'
        with patch('core.ai.workflow.invoke', return_value=output) as invoke:
            process_one()
        context = invoke.call_args.args[3]
        self.assertEqual(context['action'], 'explain')
        self.assertEqual(context['fragments'], [])
        self.assertNotIn('answer', context)
        job.refresh_from_db()
        self.assertEqual(job.state, 'ready')
        self.assertEqual(job.prompt_version, 'salud-actions-6')
        response = self.client.get(f'/api/v1/ai/requests/{job.pk}/')
        self.assertEqual(response.data['action'], 'explain')
        self.assertEqual(self.client.post(f'/api/v1/ai/requests/{job.pk}/', format='json').status_code, 400)

    def test_non_suggest_proposal_rejected(self):
        self.authorize('extract')
        job = self.enqueue()
        output = fixtures.AIWorkflowTests.output(self)
        with patch('core.ai.workflow.invoke', return_value=output):
            process_one()
        job.refresh_from_db()
        self.assertEqual(job.state, 'failed')
        self.assertIsNone(job.result)

    def test_extract_requires_evidence_and_verifies_citations(self):
        self.authorize('extract')
        self.payload['fragment_ids'] = []
        self.assertEqual(self.client.post(self.url, self.payload, format='json').status_code, 400)
        self.payload['fragment_ids'] = [self.fragment.pk]
        job = self.enqueue()
        output = fixtures.AIWorkflowTests.output(self)
        output['result'].update(status='needs_information', suggested_fields=[])
        with patch('core.ai.workflow.invoke', return_value=output):
            process_one()
        job.refresh_from_db()
        self.assertEqual(job.state, 'ready')
        AIFragmentRelease.objects.update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(f'/api/v1/ai/requests/{job.pk}/').status_code, 400)

    def test_action_revoked_before_and_during_call(self):
        self.authorize('interview')
        job = self.enqueue()
        self.policy.actions = ['suggest']
        self.policy.save()
        with patch('core.ai.workflow.invoke') as invoke:
            process_one()
            invoke.assert_not_called()
        job.refresh_from_db()
        self.assertEqual(job.state, 'failed')
        self.authorize('interview')
        job = self.enqueue()
        def revoke(*args, **kwargs):
            self.policy.actions = ['suggest']
            self.policy.save()
            return self.output()
        with patch('core.ai.workflow.invoke', side_effect=revoke):
            process_one()
        job.refresh_from_db()
        self.assertEqual(job.state, 'failed')
        self.assertIsNone(job.result)

    def test_action_model_configuration(self):
        self.authorize('interview')
        job = self.enqueue()
        config = {'model': 'synthetic-interview', 'max_output_tokens': 500,
                  'input_per_million': '1', 'output_per_million': '2',
                  'rates_verified_on': timezone.localdate().isoformat()}
        output = self.output()
        output['result']['follow_up_questions'] = ['¿Quién verifica la solicitud?']
        with override_settings(AI_MODELS={'openai': {'actions': {'interview': config}}}), patch('core.ai.workflow.invoke', return_value=output) as invoke:
            process_one()
        self.assertEqual(invoke.call_args.args[2], 'synthetic-interview')
        job.refresh_from_db()
        self.assertEqual(job.state, 'ready')
        self.policy.actions = ['suggest']
        self.policy.save()
        self.assertEqual(self.client.get(f'/api/v1/ai/requests/{job.pk}/').status_code, 400)
