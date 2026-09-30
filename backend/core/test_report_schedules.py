from datetime import datetime,timezone as dtz
from unittest.mock import patch
from django.test import TransactionTestCase
from core import test_reports
from core.models import ReportSchedule,ScheduledReportRun,SavedReport,RoleAssignment
from core.report_schedules import run_schedule

class ReportScheduleTests(TransactionTestCase):
    def setUp(self):
        test_reports.WeeklyReportTests.setUp(self)
        RoleAssignment.objects.filter(user=self.reviewer).update(role='director')
        self.client.force_authenticate(self.reviewer)
        self.url=f'/api/v1/reports/services/{self.service.pk}/schedule/'
        self.monday=datetime(2026,10,12,18,tzinfo=dtz.utc)
    def configure(self,**extra):
        return self.client.post(self.url,{'version':0,'enabled':True,'rationale':'Synthetic weekly drafts',**extra},format='json')
    def test_week_closed_once_and_human_review_stays_pending(self):
        response=self.configure();self.assertEqual(response.status_code,200,response.data)
        schedule=ReportSchedule.objects.get()
        self.assertEqual(run_schedule(schedule.pk,self.now),'waiting')
        self.assertEqual(run_schedule(schedule.pk,self.monday),'generated')
        self.assertEqual(run_schedule(schedule.pk,self.monday),'already_generated')
        report=SavedReport.objects.get();self.assertEqual(report.state,'pending');self.assertIsNone(report.reviewed_by_id)
        self.assertEqual(str(report.start),'2026-10-05');self.assertFalse(report.content['period']['partial']);self.assertEqual(report.content['delivery'],'not_sent')
        self.assertEqual(ScheduledReportRun.objects.count(),1)
        exported=self.client.get(f'/api/v1/reports/saved/{report.pk}/').data
        self.assertEqual(exported['generation']['kind'],'scheduled')
        self.assertEqual(exported['generation']['schedule_id'],schedule.pk)
    def test_scope_permission_revocation_and_pause(self):
        self.client.force_authenticate(self.author);self.assertEqual(self.configure().status_code,403)
        self.client.force_authenticate(self.admin);self.assertEqual(self.configure().status_code,404)
        self.client.force_authenticate(self.reviewer);self.configure();schedule=ReportSchedule.objects.get()
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=self.now)
        self.assertEqual(run_schedule(schedule.pk,self.monday),'authorization_required');self.assertEqual(SavedReport.objects.count(),0)
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=None)
        self.assertEqual(self.configure(version=1,enabled=False).status_code,200)
        self.assertEqual(run_schedule(schedule.pk,self.monday),'disabled')
    def test_configuration_conflict_and_idempotent_retry(self):
        self.configure();self.assertEqual(self.configure().status_code,200)
        self.assertEqual(self.configure(enabled=False).status_code,409)
        self.assertEqual(self.configure(version=1,enabled=False).status_code,200)
        self.assertFalse(ReportSchedule.objects.get().enabled)
    def test_pause_during_snapshot_prevents_commit(self):
        from core.report_schedules import snapshot
        self.configure();schedule=ReportSchedule.objects.get()
        def paused(*args):
            content=snapshot(*args)
            ReportSchedule.objects.filter(pk=schedule.pk).update(enabled=False,version=2)
            return content
        with patch('core.report_schedules.snapshot',side_effect=paused):self.assertEqual(run_schedule(schedule.pk,self.monday),'configuration_changed')
        self.assertEqual(SavedReport.objects.count(),0)
    def test_latest_week_only_and_retry_after_failure(self):
        self.configure();schedule=ReportSchedule.objects.get()
        later=datetime(2026,11,2,18,tzinfo=dtz.utc)
        with patch('core.report_schedules.snapshot',side_effect=RuntimeError('Synthetic')):
            with self.assertRaises(RuntimeError):run_schedule(schedule.pk,later)
        schedule.refresh_from_db();self.assertEqual(schedule.last_status,'failed')
        self.assertEqual(run_schedule(schedule.pk,later),'generated')
        self.assertEqual(str(SavedReport.objects.get().start),'2026-10-26');self.assertEqual(SavedReport.objects.count(),1)
    def test_concurrent_cycles_conserve_one_report(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        self.configure();schedule=ReportSchedule.objects.get()
        def run(_):
            try:return run_schedule(schedule.pk,self.monday)
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
        self.assertEqual(sorted(results),['already_generated','generated']);self.assertEqual(SavedReport.objects.count(),1)
    def test_scheduler_command_surfaces_lost_authority_and_self_review_is_denied(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        self.configure();schedule=ReportSchedule.objects.get();run_schedule(schedule.pk,self.monday)
        report=SavedReport.objects.get()
        data={'approve':True,'content_hash':report.content_hash,'rationale':'Synthetic review'}
        self.assertEqual(self.client.post(f'/api/v1/reports/saved/{report.pk}/',data,format='json').status_code,400)
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=self.now)
        with self.assertRaises(CommandError):call_command('scheduled_reports')
        self.assertEqual(SavedReport.objects.count(),1)
