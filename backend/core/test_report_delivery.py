from django.test import TransactionTestCase
from django.utils import timezone
from core import test_saved_reports
from core.models import ReportDelivery,RoleAssignment,ReportDisposition,SavedReport,AuditEvent

class ReportDeliveryTests(TransactionTestCase):
    save=test_saved_reports.SavedReportTests.save
    review=test_saved_reports.SavedReportTests.review
    def setUp(self):
        test_saved_reports.SavedReportTests.setUp(self)
        self.report=self.save().data
        self.client.force_authenticate(self.reviewer)
        self.report=self.review(self.report).data
        self.delivery_url=f"/api/v1/reports/saved/{self.report['id']}/distribution/"
    def deliver(self,**extra):return self.client.post(self.delivery_url,{'content_hash':self.report['content_hash'],'recipients':[self.author.pk],'rationale':'Synthetic internal distribution',**extra},format='json')
    def ack(self,pk,**extra):return self.client.post(f'/api/v1/reports/deliveries/{pk}/acknowledge/',{'content_hash':self.report['content_hash'],**extra},format='json')
    def test_explicit_delivery_personal_read_and_no_duplicates(self):
        self.assertEqual(self.deliver().data['created'],1);self.assertEqual(self.deliver().data['created'],0)
        delivery=ReportDelivery.objects.get();self.assertIsNone(delivery.acknowledged_at)
        self.assertEqual(self.ack(delivery.pk).status_code,404)
        self.client.force_authenticate(self.author)
        self.assertEqual(len(self.client.get('/api/v1/reports/inbox/').data['results']),1)
        self.assertEqual(self.ack(delivery.pk).status_code,200);self.assertEqual(self.ack(delivery.pk).status_code,200)
        self.assertEqual(AuditEvent.objects.filter(action='report.read_acknowledged').count(),1)
        self.assertEqual(self.client.get(f"/api/v1/reports/saved/{self.report['id']}/").data['distribution']['acknowledged'],1)
    def test_pending_retired_and_wrong_hash_rejected(self):
        self.assertEqual(self.deliver(content_hash='0'*64).status_code,409)
        SavedReport.objects.filter(pk=self.report['id']).update(state='pending');self.assertEqual(self.deliver().status_code,400)
        SavedReport.objects.filter(pk=self.report['id']).update(state='approved')
        ReportDisposition.objects.create(report_id=self.report['id'],actor=self.reviewer,rationale='Synthetic withdrawal',expected_state='approved')
        self.assertEqual(self.deliver().status_code,400);self.assertEqual(ReportDelivery.objects.count(),0)
    def test_invalid_recipient_batch_is_atomic_and_scope_is_enforced(self):
        self.assertEqual(self.deliver(recipients=[self.author.pk,self.other.pk]).status_code,400)
        self.assertEqual(self.deliver(recipients=[self.author.pk,self.author.pk]).status_code,400)
        self.assertEqual(ReportDelivery.objects.count(),0)
        self.client.force_authenticate(self.author);self.assertEqual(self.deliver().status_code,403)
        self.client.force_authenticate(self.admin);self.assertEqual(self.deliver().status_code,404)
    def test_role_revocation_hides_inbox_and_blocks_read(self):
        self.deliver();delivery=ReportDelivery.objects.get()
        self.client.force_authenticate(self.author)
        type(self.author).objects.filter(pk=self.author.pk).update(is_active=False)
        self.assertEqual(self.client.get('/api/v1/reports/inbox/').data['results'],[])
        self.assertEqual(self.ack(delivery.pk).status_code,404)
        type(self.author).objects.filter(pk=self.author.pk).update(is_active=True)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.get('/api/v1/reports/inbox/').data['results'],[]);self.assertEqual(self.ack(delivery.pk).status_code,404)
        self.assertEqual(ReportDelivery.objects.count(),1)
    def test_retirement_after_delivery_is_visible_but_cannot_acknowledge(self):
        self.deliver();delivery=ReportDelivery.objects.get()
        ReportDisposition.objects.create(report_id=self.report['id'],actor=self.reviewer,rationale='Synthetic retirement',expected_state='approved')
        self.client.force_authenticate(self.author)
        self.assertEqual(self.client.get('/api/v1/reports/inbox/').data['results'][0]['availability'],'withdrawn')
        self.assertEqual(self.ack(delivery.pk).status_code,400)
    def test_concurrent_distribution_creates_single_receipt(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from rest_framework.test import APIClient
        def send(_):
            try:
                c=APIClient();c.force_authenticate(self.reviewer)
                return c.post(self.delivery_url,{'content_hash':self.report['content_hash'],'recipients':[self.author.pk],'rationale':'Synthetic concurrent'},format='json').data['created']
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(send,range(2)))
        self.assertEqual(sorted(results),[0,1]);self.assertEqual(ReportDelivery.objects.count(),1)
    def test_inbox_past_500_stable_pages_and_current_permissions(self):
        import uuid
        template=SavedReport.objects.get(pk=self.report['id'])
        reports=SavedReport.objects.bulk_create([SavedReport(service=self.service,created_by=self.author,client_key=uuid.uuid4(),start=template.start,content=template.content,content_hash=template.content_hash,state='approved') for _ in range(505)])
        rows=ReportDelivery.objects.bulk_create([ReportDelivery(report=r,recipient=self.author,sender=self.reviewer,rationale='Synthetic page') for r in reports])
        self.client.force_authenticate(self.author)
        url='/api/v1/reports/inbox/'
        first=self.client.get(url,{'page_size':100})
        self.assertEqual(first.status_code,200)
        self.assertEqual(first['Cache-Control'],'private, no-store')
        seen=[r['id'] for r in first.data['results']];cursor=first.data['next_before']
        new=ReportDelivery.objects.create(report=template,recipient=self.author,sender=self.reviewer,rationale='Arrived during pagination')
        while cursor:
            page=self.client.get(url,{'page_size':100,'before':cursor}).data
            seen.extend(r['id'] for r in page['results']);cursor=page['next_before']
        self.assertEqual(seen,sorted([r.pk for r in rows],reverse=True))
        self.assertEqual(self.client.get(url).data['results'][0]['id'],new.pk)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url,{'before':seen[0]}).data['results'],[])
        self.client.force_authenticate(self.author)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(url,{'before':seen[0]}).data,{'results':[],'next_before':None})

    def test_distribution_pages_cover_all_people_and_deliveries(self):
        from django.contrib.auth import get_user_model
        from datetime import date
        users=get_user_model().objects.bulk_create([get_user_model()(username=f'page_{i}') for i in range(505)])
        RoleAssignment.objects.bulk_create([RoleAssignment(user=u,service=self.service,role='contributor',starts=date(2026,1,1),ends=date(2027,1,1),approved_by=self.reviewer) for u in users])
        ReportDelivery.objects.bulk_create([ReportDelivery(report_id=self.report['id'],recipient=u,sender=self.reviewer,rationale='Synthetic page') for u in users])
        from core.report_delivery import eligible
        expected=list(eligible(self.service.pk).values_list('user_id',flat=True))
        seen=[];delivered=[];people_cursor=None;delivery_cursor=None
        while True:
            params={'page_size':100}
            if people_cursor:params['people_after']=people_cursor
            if delivery_cursor:params['deliveries_before']=delivery_cursor
            response=self.client.get(self.delivery_url,params)
            self.assertEqual(response.status_code,200,response.data)
            data=response.data
            seen.extend(u['user_id'] for u in data['eligible_recipients'])
            delivered.extend(r['id'] for r in data['deliveries'])
            people_cursor=data['next_people_after'];delivery_cursor=data['next_deliveries_before']
            if not people_cursor and not delivery_cursor:break
        self.assertEqual(seen,expected)
        self.assertEqual(delivered,list(ReportDelivery.objects.order_by('-pk').values_list('pk',flat=True)))
        # A cursor is not authorization and does not constrain explicit selections to a page.
        self.assertEqual(self.deliver(recipients=[users[-1].pk]).data['already_delivered'],1)
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(self.delivery_url,{'people_after':users[1].pk}).status_code,404)

    def test_pagination_rejects_invalid_and_repeated_parameters(self):
        for suffix in ['page_size=0','page_size=101','page_size=abc','page_size=1&page_size=2','unknown=1']:
            for url in [self.delivery_url,'/api/v1/reports/inbox/']:
                self.assertEqual(self.client.get(url+'?'+suffix).status_code,400)
        self.assertEqual(self.client.get('/api/v1/reports/inbox/?before=-1').status_code,400)
        self.assertEqual(self.client.get(self.delivery_url+'?people_after=9223372036854775808').status_code,400)
