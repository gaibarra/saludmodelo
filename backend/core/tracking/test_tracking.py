import uuid
from datetime import date,timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient
from core import tests as fixtures
from core.models import *
from .workflow import reminders

class TrackingTests(TestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        RoleAssignment.objects.filter(user=self.author).update(role='manager')
        RoleAssignment.objects.filter(user=self.reviewer).update(role='director')
        RoleAssignment.objects.all().update(ends=date(2027,12,31))
        self.sub=get_user_model().objects.create_user('substitute');self.coord=get_user_model().objects.create_user('coordinator')
        for user,role in [(self.sub,'contributor'),(self.coord,'coordinator')]:RoleAssignment.objects.create(user=user,service=self.service,role=role,starts=timezone.localdate(),ends=date(2027,12,31),approved_by=self.admin)
        self.client=APIClient();self.client.force_authenticate(self.author)
        self.url=f'/api/v1/tracking/services/{self.service.pk}/'
        self.body={'title':'Synthetic work','owner':self.author.pk,'substitute':self.sub.pk,'coordinator':self.coord.pk,'starts':'2026-10-05','due':'2026-10-06','priority':'high','estimated_minutes':120,'acceptance_criteria':'Synthetic normal and exception checks','predecessors':[]}
        self.clock=patch('core.tracking.workflow.today',return_value=date(2026,10,9));self.clock.start();self.addCleanup(self.clock.stop)
    def create(self,**extra):
        self.client.force_authenticate(self.author)
        r=self.client.post(self.url,{**self.body,**extra},format='json');self.assertEqual(r.status_code,201,r.data);return r.data
    def propose(self,t,**extra):
        self.client.force_authenticate(self.author)
        r=self.client.post(f"/api/v1/tracking/tasks/{t['id']}/change/",{**self.body,'version':t['etag'],'rationale':'Synthetic change',**extra},format='json');self.assertEqual(r.status_code,200,r.data);return r.data
    def approve(self,t):
        self.client.force_authenticate(self.reviewer)
        r=self.client.post(f"/api/v1/tracking/changes/{t['changes'][0]['id']}/decision/",{'approve':True,'rationale':'Synthetic independent decision'},format='json');self.assertEqual(r.status_code,200,r.data);return r.data
    def state(self,t,target,user=None):
        self.client.force_authenticate(user or self.author)
        return self.client.post(f"/api/v1/tracking/tasks/{t['id']}/state/",{'version':t['etag'],'target':target,'note':'Synthetic result'},format='json')
    def test_proposal_baseline_independent_acceptance_and_cancel_denominator(self):
        t=self.create();self.assertFalse(t['committed']);self.assertEqual(self.state(t,'in_progress').status_code,400)
        t=self.approve(self.propose(t));self.assertTrue(t['committed'])
        t=self.state(t,'in_progress').data;t=self.state(t,'submitted').data
        self.assertEqual(self.state(t,'accepted').status_code,400)
        t=self.state(t,'accepted',self.reviewer).data;self.assertEqual(t['state'],'accepted')
        t=self.approve(self.propose(t,cancel=True));self.assertEqual(t['state'],'cancelled')
        metrics=self.client.get(self.url).data['metrics'];self.assertEqual(metrics['accepted']['denominator'],1);self.assertEqual(metrics['cancelled_committed'],1);self.assertEqual(metrics['accepted']['numerator'],0)
        self.assertEqual(BaselineChange.objects.filter(state='approved').count(),2)
    def test_cross_service_and_expired_authority(self):
        t=self.create();self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.get(f"/api/v1/tracking/tasks/{t['id']}/").status_code,404)
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.post(self.url,{**self.body,'owner':self.other.pk},format='json').status_code,403)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.assertEqual(self.client.post(self.url,self.body,format='json').status_code,404)
    def test_dependency_cycle_scope_dates_and_closure(self):
        a=self.approve(self.propose(self.create()))
        b=self.create(title='Successor',starts='2026-10-07',due='2026-10-08',predecessors=[a['id']])
        b=self.approve(self.propose(b,title='Successor',starts='2026-10-07',due='2026-10-08',predecessors=[a['id']]))
        self.assertEqual(self.state(b,'in_progress').status_code,400)
        self.client.force_authenticate(self.author)
        r=self.client.post(f"/api/v1/tracking/tasks/{a['id']}/change/",{**self.body,'version':a['etag'],'starts':'2026-10-09','due':'2026-10-10','predecessors':[b['id']],'rationale':'Cycle'},format='json');self.assertEqual(r.status_code,400);self.assertIn('ciclo',str(r.data))
        foreign=Task.objects.create(service=self.foreign,owner=self.other,title='Foreign',deduplication_key='foreign-test')
        self.assertEqual(self.client.post(self.url,{**self.body,'predecessors':[foreign.pk]},format='json').status_code,400)
        a=self.state(a,'submitted').data;a=self.state(a,'accepted',self.reviewer).data
        self.assertEqual(self.state(b,'in_progress').status_code,200)
    def test_stale_change_cannot_overwrite_work_and_self_review_fails(self):
        t=self.approve(self.propose(self.create()));proposal=self.propose(t,title='Changed')
        working=self.state(t,'in_progress').data
        self.client.force_authenticate(self.reviewer)
        url=f"/api/v1/tracking/changes/{proposal['changes'][0]['id']}/decision/"
        self.assertEqual(self.client.post(url,{'approve':True,'rationale':'Stale'},format='json').status_code,409)
        RoleAssignment.objects.create(user=self.author,service=self.service,role='director',starts=timezone.localdate(),ends=date(2027,12,31),approved_by=self.admin)
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.post(url,{'approve':False,'rationale':'Self'},format='json').status_code,400)
        self.assertEqual(Task.objects.get(pk=t['id']).etag,working['etag'])
    def test_time_is_idempotent_scoped_and_bounded(self):
        t=self.create();url=f"/api/v1/tracking/tasks/{t['id']}/time/"
        payload={'day':'2026-10-08','minutes':120,'note':'Synthetic actual work','client_key':str(uuid.uuid4())}
        self.assertEqual(self.client.post(url,payload,format='json').status_code,200)
        self.assertEqual(self.client.post(url,payload,format='json').status_code,200);self.assertEqual(TimeEntry.objects.count(),1)
        self.assertEqual(self.client.post(url,{**payload,'minutes':121},format='json').status_code,400)
        for extra in [{'minutes':1400},{'day':'2026-09-30'},{'day':'2026-10-10'}]:self.assertEqual(self.client.post(url,{**payload,'client_key':str(uuid.uuid4()),**extra},format='json').status_code,400)
    def test_calendar_governance_reminders_holidays_and_revoked_recipient(self):
        t=self.create(due='2026-10-08');t=self.approve(self.propose(t,due='2026-10-08'))
        self.assertEqual(reminders(),0)
        url=self.url+'calendar/'
        values={'version':0,'weekdays':[0,1,2,3,4],'holidays':['2026-10-12'],'rationale':'Synthetic calendar'}
        self.assertEqual(self.client.post(url,values,format='json').status_code,403)
        InstitutionMandate.objects.create(institution=self.service.site.campus.institution,user=self.reviewer,approved_by=self.admin,starts=timezone.localdate(),ends=date(2027,12,31),rationale='Synthetic mandate')
        self.assertEqual(self.client.post(url,values,format='json').status_code,200)
        self.assertEqual(self.client.post(url,values,format='json').status_code,409)
        with patch('core.tracking.workflow.today',return_value=date(2026,10,13)):
            self.assertEqual(reminders(),2);self.assertEqual(reminders(),0)
        with patch('core.tracking.workflow.today',return_value=date(2026,10,14)):self.assertEqual(reminders(),1)
        RoleAssignment.objects.filter(user=self.sub).update(revoked_at=timezone.now())
        call_command('worker');call_command('worker')
        self.assertEqual(Notification.objects.count(),2);self.assertFalse(Notification.objects.filter(recipient=self.sub).exists())
    def test_stale_queued_notice_is_not_delivered_after_submission(self):
        t=self.approve(self.propose(self.create()));WorkPlan.objects.create(institution=self.service.site.campus.institution,weekdays=list(range(5)),holidays=[],confirmed_by=self.reviewer)
        self.assertGreater(reminders(),0);t=self.state(t,'submitted').data
        call_command('worker');self.assertEqual(Notification.objects.count(),0)
    def test_forecast_is_only_proposal_and_blocked_chains_have_no_date(self):
        a=self.approve(self.propose(self.create()));b=self.create(starts='2026-10-07',due='2026-10-08',predecessors=[a['id']])
        a=self.state(a,'blocked').data
        board=self.client.get(self.url).data
        self.assertTrue(all(f['blocked'] for f in board['forecast']));self.assertEqual(Task.objects.get(pk=b['id']).starts,date(2026,10,7))
        self.assertIsNone(board['capacity_reference']['reserve_used'])
    def test_zero_denominator_and_start_floor(self):
        self.assertEqual(self.client.get(self.url).data['metrics']['accepted']['label'],'Sin alcance definido')
        self.assertEqual(self.client.post(self.url,{**self.body,'starts':'2026-09-30'},format='json').status_code,400)
        t=self.approve(self.propose(self.create()))
        with patch('core.tracking.workflow.today',return_value=date(2026,9,30)):self.assertEqual(self.state(t,'in_progress').status_code,400)
    def test_changed_predecessor_reopens_accepted_successor_without_erasing_history(self):
        a=self.approve(self.propose(self.create()))
        b=self.create(title='Dependent',starts='2026-10-07',due='2026-10-08',predecessors=[a['id']])
        b=self.approve(self.propose(b,title='Dependent',starts='2026-10-07',due='2026-10-08',predecessors=[a['id']]))
        a=self.state(a,'submitted').data;a=self.state(a,'accepted',self.reviewer).data
        b=self.state(b,'submitted').data;b=self.state(b,'accepted',self.reviewer).data
        a=self.approve(self.propose(a,title='Revised predecessor'))
        child=Task.objects.get(pk=b['id']);self.assertEqual(child.state,'returned')
        self.assertTrue(child.events.filter(kind='state.accepted').exists())
        self.assertTrue(child.events.filter(kind='dependency.changed').exists())

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections,close_old_connections
from django.test import TransactionTestCase
from . import workflow as tracking_workflow

class ConcurrentTimeTests(TransactionTestCase):
    def test_concurrent_retries_record_one_time_entry(self):
        fixtures.WorkflowTests.setUp(self)
        task=Task.objects.create(service=self.service,owner=self.author,title='Synthetic concurrent work',deduplication_key='concurrent-time')
        actor_id=self.author.pk;task_id=task.pk;barrier=Barrier(2);key=uuid.uuid4()
        def record():
            close_old_connections()
            try:
                user=get_user_model().objects.get(pk=actor_id);row=Task.objects.get(pk=task_id)
                barrier.wait(timeout=10)
                return tracking_workflow.time_entry(user,row,{'day':date(2026,10,8),'minutes':60,'note':'Synthetic concurrent retry','client_key':key}).pk
            finally:connections['default'].close()
        with patch('core.tracking.workflow.today',return_value=date(2026,10,9)),ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(record),pool.submit(record)]
            ids=[f.result(timeout=20) for f in futures]
        self.assertEqual(ids[0],ids[1]);self.assertEqual(TimeEntry.objects.count(),1)
