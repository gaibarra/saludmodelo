import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from . import tests as fixtures
from .models import *
from .publication import save_help,review_help,publish,HELP_FIELDS
from .workflow import save_answer
from .ai import test_workflow as ai_fixtures
from .ai.workflow import process_one

class InterviewTests(TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        self.instance.refresh_from_db()
        content={k:'Synthetic guidance' for k in HELP_FIELDS};content['steps']='1. Indique responsable.\n2. Indique sede.\n3. Indique excepción.\nDespués revise el conjunto.'
        instance=save_help(self.author,self.instance.pk,self.instance.etag,content)
        instance=review_help(self.reviewer,instance.pk,instance.etag,'approved','Synthetic review')
        publish(self.reviewer,instance.pk,instance.etag)
        self.client=APIClient();self.client.force_authenticate(self.author)
        self.url=f'/api/v1/interviews/{instance.pk}/'

    def send(self,action,**values):
        current=self.client.get(self.url).data
        data={'action':action,'version':current['etag'],'answer_version':current['answer_etag'],'client_key':str(uuid.uuid4()),**values}
        return self.client.post(self.url,data,format='json')

    def begin(self):
        response=self.send('open');self.assertEqual(response.status_code,200,response.data);return response.data

    def test_two_at_a_time_resume_and_no_provider_calls(self):
        with patch('core.ai.workflow.invoke') as invoke:
            state=self.begin();self.assertEqual(len(state['next']),2)
            self.assertEqual(state['total'],3)
            first=state['items'][0]
            response=self.send('reply',item_id=first['id'],reply='Declaración privada',knowledge='known')
            self.assertEqual(response.status_code,200,response.data)
            resumed=APIClient();resumed.force_authenticate(self.author)
            state=resumed.get(self.url).data
            self.assertEqual(state['items'][0]['reply'],'Declaración privada')
            self.assertNotIn(first['id'],state['next']);self.assertEqual(len(state['next']),2)
            invoke.assert_not_called()
        self.assertEqual(InterviewTurn.objects.count(),2)
        self.assertEqual(resumed.get(self.url)['Cache-Control'],'private, no-store')

    def test_scope_owner_and_revocation(self):
        self.begin();self.client.force_authenticate(self.reviewer)
        self.assertFalse(self.client.get(self.url).data['exists'])
        self.client.force_authenticate(self.other);self.assertEqual(self.client.get(self.url).status_code,404)
        self.client.force_authenticate(self.author)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(self.url).status_code,404)

    def test_idempotency_and_conflicting_payload(self):
        key=str(uuid.uuid4());state=self.client.get(self.url).data
        payload={'action':'open','version':0,'answer_version':state['answer_etag'],'client_key':key}
        self.assertEqual(self.client.post(self.url,payload,format='json').status_code,200)
        self.assertTrue(self.client.post(self.url,payload,format='json').data['replayed'])
        payload['action']='rebase';self.assertEqual(self.client.post(self.url,payload,format='json').status_code,400)
        self.assertEqual(InterviewTurn.objects.count(),1)

    def test_stale_reply_does_not_erase_and_history_is_immutable(self):
        state=self.begin();item=state['items'][0]
        self.send('reply',item_id=item['id'],reply='Primera',knowledge='known')
        old={'action':'reply','version':state['etag'],'answer_version':state['answer_etag'],'client_key':str(uuid.uuid4()),'item_id':item['id'],'reply':'Vieja','knowledge':'known'}
        self.assertEqual(self.client.post(self.url,old,format='json').status_code,409)
        self.send('reply',item_id=item['id'],reply='Segunda',knowledge='known')
        turn=InterviewTurn.objects.get(version=2)
        self.assertEqual(turn.snapshot[0]['reply'],'Primera')
        self.assertEqual(self.client.get(self.url).data['items'][0]['reply'],'Segunda')

    def test_answer_change_rebase_preserves_text_requires_reconfirmation(self):
        state=self.begin();item=state['items'][0]
        self.send('reply',item_id=item['id'],reply='Conservar',knowledge='known')
        self.answer.refresh_from_db();save_answer(self.author,self.answer.pk,self.answer.etag,'Cambio manual','known')
        self.assertTrue(self.client.get(self.url).data['stale'])
        self.assertEqual(self.send('reply',item_id=item['id'],reply='Obsoleta',knowledge='known').status_code,409)
        state=self.send('rebase').data
        self.assertFalse(state['stale']);self.assertEqual(state['items'][0]['reply'],'Conservar')
        self.assertEqual(state['items'][0]['knowledge'],'pending')
        self.assertEqual(InterviewTurn.objects.get(version=2).snapshot[0]['knowledge'],'known')

    def test_help_change_requires_rebase(self):
        self.begin();self.instance.refresh_from_db()
        latest=save_help(self.author,self.instance.pk,self.instance.etag,{k:'Nueva ayuda' for k in HELP_FIELDS})
        latest=review_help(self.reviewer,latest.pk,latest.etag,'approved','Changed synthetic help')
        publish(self.reviewer,latest.pk,latest.etag)
        self.assertTrue(self.client.get(self.url).data['stale'])
        state=self.send('rebase').data;self.assertFalse(state['stale']);self.assertEqual(state['total'],1)

    def test_transfer_unconfirmed_once_and_pending_preserved(self):
        state=self.begin()
        self.assertEqual(self.send('apply').status_code,400)
        for item in state['items']:self.assertEqual(self.send('reply',item_id=item['id'],reply='',knowledge='unknown').status_code,200)
        current=self.client.get(self.url).data
        payload={'action':'apply','version':current['etag'],'answer_version':current['answer_etag'],'client_key':str(uuid.uuid4())}
        response=self.client.post(self.url,payload,format='json');self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(self.client.post(self.url,payload,format='json').data['replayed'])
        self.answer.refresh_from_db();self.assertEqual(self.answer.revisions.count(),1)
        self.assertEqual(self.answer.revisions.get().knowledge,'unconfirmed');self.assertEqual(self.answer.state,'draft')
        self.assertEqual(Task.objects.filter(answer=self.answer).count(),1)
        self.assertIsNotNone(InterviewTurn.objects.get(action='apply').applied_revision_id)
        self.assertEqual(self.send('apply').status_code,400)

    def test_known_and_non_applicability_need_text_and_no_unknown_fields(self):
        state=self.begin();item=state['items'][0]
        for knowledge in ['known','not_applicable']:
            self.assertEqual(self.send('reply',item_id=item['id'],reply='',knowledge=knowledge).status_code,400)
        self.assertEqual(self.send('reply',item_id='missing',reply='x',knowledge='known').status_code,400)
        self.assertEqual(self.send('reply',item_id=item['id'],reply='x',knowledge='known',approved=True).status_code,400)


class InterviewAITests(TestCase):
    def setUp(self):
        ai_fixtures.AIWorkflowTests.setUp(self)
        job=ai_fixtures.AIWorkflowTests.enqueue(self)
        output=ai_fixtures.AIWorkflowTests.output(self)
        output['result']['follow_up_questions']=['¿Cuál es la excepción?','¿Quién resuelve la excepción?']
        with patch('core.ai.workflow.invoke',return_value=output):process_one()
        self.job=job;self.iurl=f'/api/v1/interviews/{self.instance.pk}/'
        self.send('open')

    def send(self,action,**values):
        state=self.client.get(self.iurl).data
        return self.client.post(self.iurl,{'action':action,'version':state['etag'],'answer_version':state['answer_etag'],'client_key':str(uuid.uuid4()),**values},format='json')

    def test_import_validated_followups_deduplicates_and_keeps_memory_off_provider(self):
        response=self.send('add_ai',request_id=self.job.pk);self.assertEqual(response.status_code,200,response.data)
        items=response.data['items'];self.assertEqual(len(items),3)
        self.assertEqual(self.send('add_ai',request_id=self.job.pk).data['total'],3)
        self.send('reply',item_id=items[1]['id'],reply='PRIVATE-INTERVIEW-MEMORY',knowledge='known')
        self.payload['client_key']=str(uuid.uuid4());ai_fixtures.AIWorkflowTests.enqueue(self)
        with patch('core.ai.workflow.invoke',return_value=ai_fixtures.AIWorkflowTests.output(self)) as invoke:
            process_one();self.assertNotIn('PRIVATE-INTERVIEW-MEMORY',str(invoke.call_args))

    def test_source_revocation_redacts_memory_and_rebase_discards_ai(self):
        self.send('add_ai',request_id=self.job.pk)
        AIFragmentRelease.objects.update(revoked_at=timezone.now())
        state=self.client.get(self.iurl).data
        self.assertTrue(state['sources_blocked']);self.assertEqual(state['items'],[]);self.assertEqual(state['preview'],'')
        self.assertEqual(self.send('apply').status_code,409)
        state=self.send('rebase').data
        self.assertFalse(state['sources_blocked']);self.assertTrue(all(i['origin']=='help' for i in state['items']))
        self.assertEqual(InterviewTurn.objects.get(version=2).snapshot[-1]['origin'],'ai')

    def test_fabricated_saved_result_rejected(self):
        self.job.refresh_from_db();data=self.job.result;data['citations'][0]['quote']='Invented citation';self.job.result=data;self.job.save()
        self.assertEqual(self.send('add_ai',request_id=self.job.pk).status_code,400)

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections,connections
from django.test import TransactionTestCase

class InterviewConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        self.url=f'/api/v1/interviews/{self.instance.pk}/'

    def race(self,payloads):
        barrier=Barrier(2)
        def send(payload):
            close_old_connections()
            try:
                client=APIClient();client.force_authenticate(self.author)
                barrier.wait(timeout=10)
                return client.post(self.url,payload,format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(send,payloads))

    def test_concurrent_start_and_apply_idempotent(self):
        payload={'action':'open','version':0,'answer_version':0,'client_key':str(uuid.uuid4())}
        self.assertEqual(self.race([payload,payload]),[200,200])
        self.assertEqual(Interview.objects.count(),1);self.assertEqual(InterviewTurn.objects.count(),1)
        client=APIClient();client.force_authenticate(self.author)
        state=client.get(self.url).data
        result=client.post(self.url,{'action':'reply','version':state['etag'],'answer_version':state['answer_etag'],'client_key':str(uuid.uuid4()),'item_id':state['items'][0]['id'],'reply':'Concurrent synthetic declaration','knowledge':'known'},format='json')
        self.assertEqual(result.status_code,200)
        payload={'action':'apply','version':result.data['etag'],'answer_version':result.data['answer_etag'],'client_key':str(uuid.uuid4())}
        self.assertEqual(self.race([payload,payload]),[200,200])
        self.assertEqual(AnswerRevision.objects.count(),1)
        self.assertEqual(InterviewTurn.objects.filter(action='apply').count(),1)
