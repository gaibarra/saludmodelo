import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timezone as dt_timezone
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import connections
from rest_framework.test import APIClient
from core.models import TimeEntry,TimeCorrection,RoleAssignment,TaskEvent
from . import test_tracking

class TimeCorrectionTests(TransactionTestCase):
    create=test_tracking.TrackingTests.create
    def setUp(self):
        test_tracking.TrackingTests.setUp(self)
        self.task=self.create()
        self.entry=TimeEntry.objects.create(task_id=self.task['id'],actor=self.author,day=date(2026,10,6),minutes=60,note='Original',client_key=uuid.uuid4())
        self.endpoint=f'/api/v1/tracking/time/{self.entry.pk}/correct/'
    def correct(self,**extra):
        return self.client.post(self.endpoint,{'version':0,'minutes':30,'rationale':'Synthetic correction',**extra},format='json')
    def test_original_history_totals_idempotence_and_conflict(self):
        response=self.correct();self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['actual_minutes'],30)
        row=response.data['time_entries'][0]
        self.assertEqual((row['minutes'],row['effective_minutes'],row['correction_version']),(60,30,1))
        self.assertEqual(self.correct().status_code,200)
        self.assertEqual(self.correct(minutes=40).status_code,409)
        self.assertEqual(self.correct(version=1,minutes=0).status_code,200)
        self.assertEqual(self.client.get(self.url).data['metrics']['actual_minutes'],0)
        self.entry.refresh_from_db();self.assertEqual(self.entry.minutes,60)
        self.assertEqual(TimeCorrection.objects.count(),2)
        self.assertEqual(TaskEvent.objects.filter(kind='time.corrected').count(),2)
    def test_other_people_technical_accounts_and_revocation(self):
        for user in [self.sub,self.reviewer,self.other,self.admin]:
            self.client.force_authenticate(user);self.assertEqual(self.correct().status_code,404)
        self.client.force_authenticate(self.author)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=datetime.now(dt_timezone.utc))
        self.assertEqual(self.correct().status_code,404)
        self.assertEqual(TimeCorrection.objects.count(),0)
    def test_inactive_account_and_invalid_values(self):
        for values in [{'minutes':1441},{'minutes':-1},{'minutes':60},{'rationale':''},{'version':-1}]:
            self.assertEqual(self.correct(**values).status_code,400)
        type(self.author).objects.filter(pk=self.author.pk).update(is_active=False)
        self.assertEqual(self.correct().status_code,404)
    def test_daily_limit_applies_to_corrections_and_new_entries(self):
        self.assertEqual(self.correct(minutes=1400).status_code,200)
        url=f"/api/v1/tracking/tasks/{self.task['id']}/time/"
        body={'day':'2026-10-06','minutes':41,'note':'New time','client_key':str(uuid.uuid4())}
        self.assertEqual(self.client.post(url,body,format='json').status_code,400)
        body['minutes']=40;self.assertEqual(self.client.post(url,body,format='json').status_code,200)
        self.assertEqual(self.correct(version=1,minutes=1401).status_code,400)
        self.assertEqual(self.correct(version=1,minutes=0).status_code,200)
        body.update(minutes=1400,client_key=str(uuid.uuid4()))
        self.assertEqual(self.client.post(url,body,format='json').status_code,200)
    def test_concurrent_same_version_has_one_winner(self):
        def send(minutes):
            try:
                client=APIClient();client.force_authenticate(self.author)
                return client.post(self.endpoint,{'version':0,'minutes':minutes,'rationale':'Race'},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(send,[20,40]))
        self.assertEqual(sorted(codes),[200,409]);self.assertEqual(TimeCorrection.objects.count(),1)
    def test_saved_report_remains_fixed_new_report_uses_effective_time(self):
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,9,18,tzinfo=dt_timezone.utc)):
            url=f"/api/v1/reports/services/{self.task['service']}/saved/"
            first=self.client.post(url,{'start':'2026-10-05','client_key':str(uuid.uuid4())},format='json')
            self.assertEqual(first.status_code,201,first.data)
            self.assertEqual(first.data['content']['period_activity']['minutes'],60)
            self.assertEqual(self.correct().status_code,200)
            second=self.client.post(url,{'start':'2026-10-05','client_key':str(uuid.uuid4())},format='json')
            self.assertEqual(second.data['content']['period_activity']['minutes'],30)
            old=self.client.get(f"/api/v1/reports/saved/{first.data['id']}/").data
            self.assertEqual(old['content'],first.data['content'])
            self.assertEqual(old['content_hash'],first.data['content_hash'])
