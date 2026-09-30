from django.test import TransactionTestCase
from core import test_saved_reports
from core.models import ReportDisposition,RoleAssignment,SavedReport

class ReportDispositionTests(TransactionTestCase):
    def setUp(self):test_saved_reports.SavedReportTests.setUp(self)
    save=test_saved_reports.SavedReportTests.save
    review=test_saved_reports.SavedReportTests.review
    def dispose(self,row,replacement=None,**kwargs):
        data={'content_hash':row['content_hash'],'expected_state':row['state'],'replacement':replacement['id'] if replacement else None,'replacement_hash':replacement['content_hash'] if replacement else None,'rationale':'Synthetic correction'}
        data.update(kwargs)
        return self.client.post(f"/api/v1/reports/saved/{row['id']}/disposition/",data,format='json')
    def test_author_withdraws_pending_and_prevents_review(self):
        row=self.save().data
        a=self.dispose(row);self.assertEqual(a.status_code,200,a.data)
        self.assertEqual(a.data['availability'],'withdrawn');self.assertEqual(a.data['content'],row['content'])
        self.assertEqual(self.dispose(row).status_code,200);self.assertEqual(ReportDisposition.objects.count(),1)
        self.assertEqual(self.dispose(row,rationale='Other').status_code,409)
        self.client.force_authenticate(self.reviewer);self.assertEqual(self.review(row).status_code,409)
    def test_approved_replacement_and_preserved_resolution(self):
        old=self.save().data;new=self.save().data
        self.client.force_authenticate(self.reviewer)
        old=self.review(old).data;new=self.review(new).data
        self.client.force_authenticate(self.author);self.assertEqual(self.dispose(old,new).status_code,403)
        self.client.force_authenticate(self.reviewer)
        result=self.dispose(old,new);self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(result.data['state'],'approved');self.assertEqual(result.data['availability'],'superseded')
        self.assertEqual(result.data['reviewed_by_id'],self.reviewer.pk)
        self.assertEqual(self.dispose(new,old).status_code,400)
        self.assertEqual(self.dispose(new).status_code,200)
        exported=self.client.get(f"/api/v1/reports/saved/{old['id']}/").data
        self.assertEqual(exported['disposition']['replacement_id'],new['id'])
    def test_invalid_targets_hashes_and_stale_state(self):
        old=self.save().data;new=self.save().data;different=self.save(start='2026-10-04').data
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.dispose(old,new).status_code,400)
        new=self.review(new).data;different=self.review(different).data
        self.assertEqual(self.dispose(old,different).status_code,400)
        self.assertEqual(self.dispose(new,new).status_code,400)
        self.assertEqual(self.dispose(old,new,replacement_hash='0'*64).status_code,409)
        self.assertEqual(self.dispose(old,content_hash='0'*64).status_code,409)
        self.review(old);self.assertEqual(self.dispose(old).status_code,409)
    def test_scope_revocation_and_tamper(self):
        row=self.save().data
        self.client.force_authenticate(self.other);self.assertEqual(self.dispose(row).status_code,404)
        self.client.force_authenticate(self.admin);self.assertEqual(self.dispose(row).status_code,404)
        self.client.force_authenticate(self.author)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=self.now)
        self.assertEqual(self.dispose(row).status_code,404)
        self.client.force_authenticate(self.reviewer)
        SavedReport.objects.filter(pk=row['id']).update(content={'altered':True})
        self.assertEqual(self.dispose(row).status_code,400)
    def test_concurrent_cross_replacements_cannot_form_cycle(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from rest_framework.test import APIClient
        a=self.save().data;b=self.save().data
        self.client.force_authenticate(self.reviewer);a=self.review(a).data;b=self.review(b).data
        def submit(pair):
            source,target=pair
            try:
                c=APIClient();c.force_authenticate(self.reviewer)
                return c.post(f"/api/v1/reports/saved/{source['id']}/disposition/",{'content_hash':source['content_hash'],'expected_state':source['state'],'replacement':target['id'],'replacement_hash':target['content_hash'],'rationale':'Concurrent'},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,[(a,b),(b,a)]))
        self.assertEqual(sorted(results),[200,400]);self.assertEqual(ReportDisposition.objects.count(),1)
    def test_replacement_in_another_service_is_hidden(self):
        from core.models import Service
        row=self.save().data;target=self.save().data
        foreign=Service.objects.create(site=self.service.site,name='Foreign synthetic service')
        SavedReport.objects.filter(pk=target['id']).update(service=foreign,state='approved')
        self.client.force_authenticate(self.reviewer)
        self.assertEqual(self.dispose(row,target).status_code,404)
        self.assertEqual(ReportDisposition.objects.count(),0)
    def test_review_racing_with_withdrawal_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from rest_framework.test import APIClient
        row=self.save().data
        def submit(withdraw):
            try:
                c=APIClient();c.force_authenticate(self.reviewer)
                payload=({'content_hash':row['content_hash'],'expected_state':'pending','replacement':None,'replacement_hash':None,'rationale':'Race'} if withdraw else {'content_hash':row['content_hash'],'approve':True,'rationale':'Race'})
                suffix='disposition/' if withdraw else ''
                return c.post(f"/api/v1/reports/saved/{row['id']}/{suffix}",payload,format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,[False,True]))
        self.assertEqual(sorted(results),[200,409])
