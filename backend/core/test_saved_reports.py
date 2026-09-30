import uuid
from core import test_reports
from django.test import TransactionTestCase
from core.models import SavedReport,RoleAssignment

class SavedReportTests(TransactionTestCase):
    def setUp(self):
        test_reports.WeeklyReportTests.setUp(self)
        self.url=f'/api/v1/reports/services/{self.service.pk}/saved/'
        RoleAssignment.objects.filter(user=self.reviewer).update(role='director')
    def save(self,key=None,start='2026-10-05'):
        return self.client.post(self.url,{'start':start,'client_key':str(key or uuid.uuid4())},format='json')
    def review(self,row,**kwargs):
        data={'approve':True,'content_hash':row['content_hash'],'rationale':'Independent review'};data.update(kwargs)
        return self.client.post(f"/api/v1/reports/saved/{row['id']}/",data,format='json')
    def test_frozen_snapshot_independent_approval_and_export(self):
        row=self.save();self.assertEqual(row.status_code,201,row.data);row=row.data
        test_reports.WeeklyReportTests.task(self,state='accepted')
        current=self.client.get(f'/api/v1/reports/services/{self.service.pk}/weekly/').data
        self.assertEqual(current['current']['accepted_tasks']['numerator'],1)
        self.assertEqual(row['content']['current']['accepted_tasks']['numerator'],0)
        self.assertEqual(self.review(row).status_code,403)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.review(row).status_code,200)
        self.assertEqual(self.review(row).status_code,200)
        self.assertEqual(self.review(row,approve=False).status_code,409)
        exported=self.client.get(f"/api/v1/reports/saved/{row['id']}/")
        self.assertEqual(exported.data['content'],row['content']);self.assertEqual(exported.data['state'],'approved')
        self.assertEqual(exported['Cache-Control'],'private, no-store')
        self.assertIn('attachment',exported['Content-Disposition'])
    def test_idempotence_and_payload_binding(self):
        key=uuid.uuid4();a=self.save(key);b=self.save(key)
        self.assertEqual(a.data['id'],b.data['id']);self.assertEqual(SavedReport.objects.count(),1)
        self.assertEqual(self.save(key,'2026-10-04').status_code,400)
    def test_scope_revocation_and_technical_user(self):
        row=self.save().data
        for user in [self.other,self.admin]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(f"/api/v1/reports/saved/{row['id']}/").status_code,404)
            self.assertEqual(self.save().status_code,403)
        self.client.force_authenticate(self.author)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=self.now)
        self.assertEqual(self.client.get(self.url).status_code,403)
    def test_hash_tampering_and_reviewer_self_approval(self):
        row=self.save().data
        RoleAssignment.objects.filter(user=self.author).update(role='director')
        self.assertEqual(self.review(row).status_code,400)
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.review(row,content_hash='0'*64).status_code,409)
        SavedReport.objects.filter(pk=row['id']).update(content={'altered':True})
        self.assertEqual(self.review(row).status_code,400)
        self.assertEqual(self.client.get(f"/api/v1/reports/saved/{row['id']}/").status_code,400)
    def test_rejection_and_invalid_input(self):
        self.assertEqual(self.save(start='2026-10-10').status_code,400)
        row=self.save().data;self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.review(row,rationale='').status_code,400)
        self.assertEqual(self.review(row,approve=False).data['state'],'rejected')
    def test_concurrent_conflicting_reviews_have_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from rest_framework.test import APIClient
        row=self.save().data
        def submit(approve):
            try:
                c=APIClient();c.force_authenticate(self.reviewer)
                return c.post(f"/api/v1/reports/saved/{row['id']}/",{'approve':approve,'content_hash':row['content_hash'],'rationale':'Concurrent review'},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,[True,False]))
        self.assertEqual(sorted(results),[200,409])
