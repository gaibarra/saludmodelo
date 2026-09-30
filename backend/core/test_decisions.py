import uuid
from concurrent.futures import ThreadPoolExecutor
from django.db import connections
from django.test import TestCase,TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from core.tracking import test_tracking as fixtures
from core.models import Decision,DecisionEvent,RoleAssignment,Task,BaselineChange

class DecisionTests(TestCase):
    def setUp(self):
        fixtures.TrackingTests.setUp(self)
        self.url=f'/api/v1/decisions/services/{self.service.pk}/'
        self.payload={'title':'Synthetic decision','question':'Which documented option?','alternatives':'A or B, awaiting direction','due':'2026-10-09','task':None,'client_key':str(uuid.uuid4())}
    def create(self):
        response=self.client.post(self.url,self.payload,format='json');self.assertEqual(response.status_code,201,response.data);return response.data
    def act(self,d,action='resolve',**extra):
        data={'version':d['etag'],'action':action,'note':'Synthetic reason','task_version':d['task_current']['etag'] if d['task_current'] else None,'client_key':str(uuid.uuid4()),**extra}
        return self.client.post(f"/api/v1/decisions/{d['id']}/",data,format='json')
    def test_independent_resolution_reopen_and_history(self):
        d=self.create();self.client.force_authenticate(self.reviewer)
        d=self.act(d).data;self.assertEqual(d['state'],'resolved');self.assertEqual(len(d['events']),2)
        d=self.act(d,'reopen').data;self.assertEqual(d['state'],'pending');self.assertEqual(d['resolution'],'')
        self.assertEqual(d['events'][1]['snapshot']['resolution'],'Synthetic reason')
        d=self.act(d,'dismiss').data;self.assertEqual(d['state'],'dismissed');self.assertEqual(len(d['events']),4)
    def test_creation_and_action_idempotency_are_bound_to_payload(self):
        d=self.create();self.assertEqual(d['id'],self.create()['id']);self.assertEqual(Decision.objects.count(),1)
        self.payload['title']='Different';self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.client.force_authenticate(self.reviewer);key=str(uuid.uuid4())
        first=self.act(d,client_key=key);second=self.act(d,client_key=key)
        self.assertEqual(first.status_code,200);self.assertEqual(second.status_code,200)
        self.assertEqual(DecisionEvent.objects.count(),2)
        self.assertEqual(self.act(d,client_key=key,note='Different').status_code,400)
    def test_scope_expired_roles_and_self_resolution(self):
        d=self.create();self.assertEqual(self.act(d).status_code,403)
        RoleAssignment.objects.filter(user=self.author).update(role='director')
        self.assertEqual(self.act(d).status_code,400)
        self.client.force_authenticate(self.other);self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.get(f"/api/v1/decisions/{d['id']}/").status_code,404)
        self.client.force_authenticate(self.admin);self.assertEqual(self.client.get(self.url).status_code,404)
        self.client.force_authenticate(self.reviewer);RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=timezone.now())
        self.assertEqual(self.act(d).status_code,404)
    def test_task_scope_changes_and_no_automatic_execution(self):
        task=Task.objects.create(service=self.service,owner=self.author,title='Original task',deduplication_key='decision-task')
        self.payload['task']=task.pk;d=self.create()
        Task.objects.filter(pk=task.pk).update(etag=1,title='Changed task')
        self.client.force_authenticate(self.reviewer);self.assertEqual(self.act(d).status_code,409)
        fresh=self.client.get(f"/api/v1/decisions/{d['id']}/").data
        self.assertEqual(fresh['task_snapshot']['title'],'Original task');self.assertEqual(fresh['task_current']['title'],'Changed task')
        self.assertEqual(self.act(fresh).status_code,200)
        task.refresh_from_db();self.assertEqual(task.state,'pending');self.assertFalse(task.committed);self.assertEqual(task.etag,1);self.assertFalse(BaselineChange.objects.exists())
        self.client.force_authenticate(self.author)
        foreign=Task.objects.create(service=self.foreign,owner=self.other,title='Foreign',deduplication_key='foreign-decision-task')
        self.payload.update(task=foreign.pk,client_key=str(uuid.uuid4()))
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,404)
    def test_stale_version_and_withdrawal_without_erasing(self):
        d=self.create();withdrawn=self.act(d,'withdraw');self.assertEqual(withdrawn.status_code,200)
        self.assertEqual(withdrawn.data['state'],'withdrawn')
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.act(d).status_code,409)
        self.assertEqual(Decision.objects.count(),1);self.assertEqual(DecisionEvent.objects.count(),2)
    def test_date_and_required_fields(self):
        self.payload['due']='2026-09-30';self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['due']='2026-10-09';self.payload['alternatives']='  ';self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)

class DecisionConcurrencyTests(TransactionTestCase):
    setUp=DecisionTests.setUp
    def test_identical_concurrent_requests_create_one_decision(self):
        def send():
            try:
                client=APIClient();client.force_authenticate(self.author)
                result=client.post(self.url,self.payload,format='json')
                return result.status_code,result.data.get('id')
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:send(),range(2)))
        self.assertEqual([r[0] for r in results],[201,201]);self.assertEqual(results[0][1],results[1][1]);self.assertEqual(Decision.objects.count(),1);self.assertEqual(DecisionEvent.objects.count(),1)
