from datetime import datetime,date,timezone as dt_timezone
from unittest.mock import patch
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from django.utils import timezone
from core import tests as fixtures
from core.models import Task,TaskEvent,BaselineChange,TimeEntry,RoleAssignment,AuditEvent
import uuid

class WeeklyReportTests(TransactionTestCase):
    def setUp(self):
        fixtures.WorkflowTests.setUp(self)
        self.client=APIClient();self.client.force_authenticate(self.author)
        self.url=f'/api/v1/reports/services/{self.service.pk}/weekly/'
        self.now=datetime(2026,10,9,18,tzinfo=dt_timezone.utc)
        RoleAssignment.objects.all().update(starts=date(2026,1,1),ends=date(2027,12,31))
        self.clock=patch('django.utils.timezone.now',return_value=self.now);self.clock.start();self.addCleanup(self.clock.stop)
    def task(self,**kwargs):
        return Task.objects.create(service=self.service,owner=self.author,title='Synthetic task',deduplication_key=str(uuid.uuid4()),committed=True,**kwargs)
    def test_zero_denominator_and_current_vs_period(self):
        response=self.client.get(self.url,{'start':'2026-10-05'})
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['current']['accepted_tasks']['label'],'Sin alcance definido')
        self.assertTrue(response.data['period']['partial'])
        self.assertEqual(response.data['delivery'],'not_sent')
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.assertEqual(AuditEvent.objects.filter(action='report.weekly_viewed').count(),1)
    def test_denominators_cancelled_hours_and_reference_dates(self):
        accepted=self.task(state='accepted');self.task(state='cancelled');self.task(state='blocked')
        Task.objects.create(service=self.service,owner=self.author,title='Proposal',deduplication_key='proposal')
        TaskEvent.objects.create(task=accepted,actor=self.author,kind='accepted',note='Private note excluded')
        old=TaskEvent.objects.create(task=accepted,actor=self.author,kind='created',note='Old')
        TaskEvent.objects.filter(pk=old.pk).update(created_at=datetime(2026,10,5,5,59,tzinfo=dt_timezone.utc))
        entry=TimeEntry.objects.create(task=accepted,actor=self.author,day=date(2026,10,6),minutes=45,note='Not exported',client_key=uuid.uuid4())
        response=self.client.get(self.url,{'start':'2026-10-05'});self.assertEqual(response.status_code,200,response.data)
        data=response.data
        self.assertEqual(data['current']['accepted_tasks'],{'numerator':1,'denominator':3,'pending':2,'label':'1 de 3'})
        self.assertEqual(data['current']['cancelled_committed'],1);self.assertEqual(data['current']['uncommitted'],1)
        self.assertEqual(data['period_activity']['minutes'],45)
        self.assertEqual(data['period_activity']['time_entries'][0]['id'],entry.pk)
        self.assertEqual(len(data['period_activity']['events']),1)
        self.assertNotIn('Private note',response.content.decode())
        older=self.client.get(self.url,{'start':'2026-09-28'}).data
        self.assertEqual(older['period_activity']['minutes'],0)
        self.assertEqual(older['current']['accepted_tasks']['denominator'],3)
    def test_cross_service_revoked_technical_account_and_exports(self):
        self.client.force_authenticate(self.other);self.assertEqual(self.client.get(self.url).status_code,404)
        self.client.force_authenticate(self.admin);self.assertEqual(self.client.get(self.url+'export/').status_code,404)
        self.client.force_authenticate(self.author)
        response=self.client.get(self.url+'export/');self.assertEqual(response.status_code,200,response.data)
        self.assertIn('attachment',response['Content-Disposition'])
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=self.now)
        self.assertEqual(self.client.get(self.url+'export/').status_code,404)
    def test_recipient_scope_and_invalid_filters(self):
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=self.now)
        data=self.client.get(self.url).data
        self.assertNotIn(self.reviewer.pk,[u['user_id'] for u in data['eligible_recipients']])
        self.assertNotIn(self.other.pk,[u['user_id'] for u in data['eligible_recipients']])
        for query in [{'start':'2026-10-10'},{'start':'invalid'},{'provider':'openai'}]:
            self.assertEqual(self.client.get(self.url,query).status_code,400)
    def test_limit_never_silently_truncates(self):
        self.task();self.task()
        with patch('core.reports.LIMIT',1):
            response=self.client.get(self.url)
        self.assertEqual(response.status_code,400)
        self.assertFalse(AuditEvent.objects.filter(action='report.weekly_viewed').exists())
    def test_snapshot_is_repeatable_when_other_connection_writes(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from core import reports
        task=self.task(state='pending');original=reports.bounded;changed=False
        def concurrent_change():
            try:Task.objects.filter(pk=task.pk).update(state='accepted')
            finally:connections.close_all()
        def observe(query):
            nonlocal changed
            if not changed:
                changed=True
                with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(concurrent_change).result(timeout=5)
            return original(query)
        with patch('core.reports.bounded',side_effect=observe):response=self.client.get(self.url)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['current']['accepted_tasks']['numerator'],0)
        task.refresh_from_db();self.assertEqual(task.state,'accepted')

    def test_operational_decisions_appear_in_pending_and_period_activity(self):
        RoleAssignment.objects.filter(user=self.reviewer).update(role='director')
        created=self.client.post(f'/api/v1/decisions/services/{self.service.pk}/',{'title':'Decision to report','question':'Which option?','alternatives':'A or B','due':'2026-10-09','task':None,'client_key':str(uuid.uuid4())},format='json')
        self.assertEqual(created.status_code,201,created.data)
        report=self.client.get(self.url,{'start':'2026-10-05'}).data
        self.assertEqual(report['current_pending_operational_decisions'][0]['id'],created.data['id'])
        self.client.force_authenticate(self.reviewer)
        resolved=self.client.post(f"/api/v1/decisions/{created.data['id']}/",{'version':1,'action':'resolve','note':'Independent recorded choice','task_version':None,'client_key':str(uuid.uuid4())},format='json')
        self.assertEqual(resolved.status_code,200,resolved.data)
        report=self.client.get(self.url,{'start':'2026-10-05'}).data
        self.assertEqual(report['current_pending_operational_decisions'],[])
        self.assertEqual([e['action'] for e in report['period_activity']['decision_events']],['create','resolve'])
