import uuid
from datetime import date,timedelta
from django.test import override_settings,TransactionTestCase
from . import test_saved_reports
from .models import SavedReport,ReportDisposition,ReportSchedule,ScheduledReportRun,RoleAssignment
from .saved_reports import digest

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReportHistoryTests(TransactionTestCase):
    setUp=test_saved_reports.SavedReportTests.setUp
    def batch(self,count=505):
        content={'fixture':'history-only synthetic metadata'}
        return SavedReport.objects.bulk_create([SavedReport(service=self.service,created_by=self.author,client_key=uuid.uuid4(),start=date(2026,10,5),content=content,content_hash=digest(content),state='approved') for _ in range(count)])
    def test_archive_beyond_500_and_insert_between_pages(self):
        rows=self.batch();first=self.client.get(self.url);self.assertEqual(first.status_code,200)
        self.assertEqual(len(first.data['results']),50);self.assertEqual(first.data['results'][0]['id'],rows[-1].pk)
        self.assertEqual(first['Cache-Control'],'private, no-store')
        newest=self.batch(1)[0];seen=[r['id'] for r in first.data['results']];cursor=first.data['next_before']
        while cursor:
            response=self.client.get(self.url,{'before':cursor,'page_size':100});seen.extend(r['id'] for r in response.data['results']);cursor=response.data['next_before']
        self.assertEqual(len(seen),505);self.assertEqual(len(set(seen)),505);self.assertNotIn(newest.pk,seen)
        self.assertEqual(self.client.get(self.url).data['results'][0]['id'],newest.pk)
    def test_approved_replacements_are_filtered_before_paging(self):
        rows=self.batch(105);oldest=rows[0]
        SavedReport.objects.filter(pk=rows[-1].pk).update(state='rejected')
        SavedReport.objects.filter(pk=rows[-2].pk).update(start=date(2026,10,12))
        ReportDisposition.objects.create(report=rows[-3],actor=self.author,rationale='Withdrawal',expected_state='approved')
        params={'start':'2026-10-05','state':'approved','retained_only':'true','exclude':rows[-4].pk,'page_size':100}
        first=self.client.get(self.url,params);self.assertEqual(len(first.data['results']),100)
        second=self.client.get(self.url,{**params,'before':first.data['next_before']});self.assertEqual([r['id'] for r in second.data['results']],[oldest.pk])
        self.client.force_authenticate(self.reviewer)
        response=self.client.post(f'/api/v1/reports/saved/{rows[-4].pk}/disposition/',{'content_hash':rows[-4].content_hash,'expected_state':'approved','replacement':oldest.pk,'replacement_hash':oldest.content_hash,'rationale':'Old replacement from later page'},format='json')
        self.assertEqual(response.status_code,200,response.data)
    def test_page_validation_and_scope_revalidation(self):
        self.batch(2)
        for params in ['?before=0','?before=9223372036854775808','?page_size=101','?page_size=0','?before=1&before=2','?unexpected=1','?start=bad','?state=unknown']:
            self.assertEqual(self.client.get(self.url+params).status_code,400,params)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=self.now)
        self.assertEqual(self.client.get(self.url,{'before':999}).status_code,403)
        self.client.force_authenticate(self.other);self.assertEqual(self.client.get(self.url).status_code,403)
    def test_history_reaches_beyond_twenty_and_uses_creation_order(self):
        reports=self.batch(56);schedule=ReportSchedule.objects.create(service=self.service,authorized_by=self.reviewer,first_period=date(2026,10,5),rationale='Synthetic')
        runs=ScheduledReportRun.objects.bulk_create([ScheduledReportRun(schedule=schedule,period=date(2026,10,5)+timedelta(weeks=i),schedule_version=1,report=r,generation_mode='backfill' if i==0 else 'scheduled',rationale='Synthetic origin') for i,r in enumerate(reports)])
        # Backfilled older period is inserted later: keyset order must still reach all rows.
        ScheduledReportRun.objects.filter(pk=runs[-1].pk).update(period=date(2026,9,28),generation_mode='backfill')
        url=f'/api/v1/reports/services/{self.service.pk}/schedule/runs/'
        first=self.client.get(url);self.assertEqual(first.status_code,200);self.assertEqual(len(first.data['results']),50)
        self.assertEqual(first.data['results'][0]['id'],runs[-1].pk)
        second=self.client.get(url,{'before':first.data['next_before']});self.assertEqual(len(second.data['results']),6)
        self.assertEqual(second.data['results'][-1]['generation_mode'],'backfill')
        self.assertNotIn('content',second.data['results'][-1]['report'])
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=self.now)
        self.assertEqual(self.client.get(url,{'before':first.data['next_before']}).status_code,404)
    def test_empty_history_without_configuration_and_invalid_cursor(self):
        url=f'/api/v1/reports/services/{self.service.pk}/schedule/runs/'
        self.assertEqual(self.client.get(url).data,{'results':[],'next_before':None})
        self.assertEqual(self.client.get(url+'?before=-1').status_code,400)
        self.assertEqual(self.client.get(url+'?page_size=1&page_size=2').status_code,400)
    def test_withdrawn_replacement_revalidated_at_commit(self):
        source,candidate=self.batch(2);self.client.force_authenticate(self.reviewer)
        listed=self.client.get(self.url,{'state':'approved','retained_only':'true'});self.assertEqual(len(listed.data['results']),2)
        ReportDisposition.objects.create(report=candidate,actor=self.reviewer,rationale='Withdrawn after selection',expected_state='approved')
        response=self.client.post(f'/api/v1/reports/saved/{source.pk}/disposition/',{'content_hash':source.content_hash,'expected_state':'approved','replacement':candidate.pk,'replacement_hash':candidate.content_hash,'rationale':'Attempt stale selection'},format='json')
        self.assertEqual(response.status_code,400);self.assertFalse(ReportDisposition.objects.filter(report=source).exists())
