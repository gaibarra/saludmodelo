from datetime import datetime,timezone as dtz
from unittest.mock import patch
from django.test import TransactionTestCase
from core import test_report_schedules
from core.models import ReportSchedule,ScheduledReportRun,SavedReport,RoleAssignment
from core.report_schedules import run_schedule

class ReportBackfillTests(TransactionTestCase):
    configure=test_report_schedules.ReportScheduleTests.configure
    def setUp(self):
        test_report_schedules.ReportScheduleTests.setUp(self)
        self.configure()
        self.backfill=f'/api/v1/reports/services/{self.service.pk}/backfill/'
        self.later=datetime(2026,10,19,18,tzinfo=dtz.utc)
        clock=patch('django.utils.timezone.now',return_value=self.later);clock.start();self.addCleanup(clock.stop)
    def recover(self,**extra):return self.client.post(self.backfill,{'version':1,'period':'2026-10-05','rationale':'Synthetic missing week',**extra},format='json')
    def test_recovery_while_paused_is_pending_and_has_origin(self):
        ReportSchedule.objects.update(enabled=False)
        response=self.recover();self.assertEqual(response.status_code,201,response.data)
        report=SavedReport.objects.get();self.assertEqual(report.state,'pending');self.assertEqual(report.content['delivery'],'not_sent')
        data=self.client.get(f'/api/v1/reports/saved/{report.pk}/').data
        self.assertEqual(data['generation']['kind'],'backfill');self.assertEqual(data['generation']['rationale'],'Synthetic missing week')
        self.assertEqual(str(report.start),'2026-10-05');self.assertIn('2026-10-19',report.content['generated_at'])
    def test_existing_run_is_not_replaced_even_when_withdrawn(self):
        from core.models import ReportDisposition
        first=self.recover().data
        ReportDisposition.objects.create(report_id=first['report_id'],actor=self.reviewer,rationale='Synthetic withdrawal',expected_state='pending')
        second=self.recover(rationale='Another attempt')
        self.assertEqual(second.status_code,200);self.assertFalse(second.data['created']);self.assertEqual(second.data['report_id'],first['report_id'])
        self.assertEqual(SavedReport.objects.count(),1);self.assertEqual(ScheduledReportRun.objects.get().rationale,'Synthetic missing week')
    def test_invalid_dates_version_and_authority(self):
        for values in [{'period':'2026-10-06'},{'period':'2026-09-28'},{'period':'2026-10-19'},{'rationale':''}]:self.assertEqual(self.recover(**values).status_code,400)
        self.assertEqual(self.recover(version=2).status_code,409)
        self.client.force_authenticate(self.author);self.assertEqual(self.recover().status_code,403)
        for user in [self.other,self.admin]:
            self.client.force_authenticate(user);self.assertEqual(self.recover().status_code,404)
    def test_configuration_or_authority_changes_during_read_prevent_commit(self):
        from core.report_schedules import snapshot
        for change in ['configuration','role','account']:
            ReportSchedule.objects.update(version=1);RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=None)
            self.reviewer.is_active=True;self.reviewer.save()
            def altered(*args):
                content=snapshot(*args)
                if change=='configuration':ReportSchedule.objects.update(version=2)
                elif change=='role':RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=self.later)
                else:type(self.reviewer).objects.filter(pk=self.reviewer.pk).update(is_active=False)
                return content
            with patch('core.report_schedules.snapshot',side_effect=altered):
                self.assertIn(self.recover().status_code,[403,409])
            self.assertEqual(SavedReport.objects.count(),0)
    def test_failure_can_retry_without_partial_records(self):
        with patch('core.report_schedules.snapshot',side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):self.recover()
        self.assertEqual(SavedReport.objects.count(),0);self.assertEqual(self.recover().status_code,201)
    def test_concurrent_automatic_and_explicit_generation_share_uniqueness(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from rest_framework.test import APIClient
        schedule=ReportSchedule.objects.get()
        def execute(manual):
            try:
                if not manual:return run_schedule(schedule.pk,self.later)
                c=APIClient();c.force_authenticate(self.reviewer)
                response=c.post(self.backfill,{'version':1,'period':'2026-10-12','rationale':'Concurrent recovery'},format='json')
                self.assertIn(response.status_code,[200,201]);return response.data
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(execute,[True,False]))
        self.assertEqual(ScheduledReportRun.objects.count(),1);self.assertEqual(SavedReport.objects.count(),1)
