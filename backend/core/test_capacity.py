import uuid
from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
from django.db import connections
from django.test import TestCase,TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from core.tracking import test_tracking as fixtures
from core.models import InstitutionMandate,CapacityDay,CapacityChange,RoleAssignment,Service,Institution,Campus,Site

class CapacityTests(TestCase):
    def setUp(self):
        fixtures.TrackingTests.setUp(self)
        self.institution=self.service.site.campus.institution
        for person in [self.author,self.reviewer]:InstitutionMandate.objects.create(institution=self.institution,user=person,approved_by=self.admin,starts=timezone.localdate()-timedelta(days=1),ends=date(2027,12,31),rationale='Synthetic institutional capacity authority')
        self.url=f'/api/v1/capacity/institutions/{self.institution.pk}/'
        self.payload={'person':self.author.pk,'day':'2026-10-05','version':0,'minutes':480,'unavailable_minutes':60,'allocations':[{'service':self.service.pk,'minutes':300}],'rationale':'Synthetic planning, no medical reason','client_key':str(uuid.uuid4())}
    def propose(self):
        r=self.client.post(self.url,self.payload,format='json');self.assertEqual(r.status_code,201,r.data);return r.data
    def review(self,c,approve=True):
        self.client.force_authenticate(self.reviewer)
        return self.client.post(f"/api/v1/capacity/changes/{c['id']}/review/",{'approve':approve,'rationale':'Independent synthetic review'},format='json')
    def board(self):return self.client.get(self.url,{'start':'2026-10-01'})
    def test_pending_independent_approval_and_day_math(self):
        c=self.propose();data=self.board().data;self.assertIsNone(data['days'][0]['available_minutes'])
        self.assertEqual(self.client.post(f"/api/v1/capacity/changes/{c['id']}/review/",{'approve':True,'rationale':'Self'},format='json').status_code,400)
        self.assertEqual(self.review(c).status_code,200)
        day=self.board().data['days'][0];self.assertEqual(day['available_minutes'],420);self.assertEqual(day['unallocated_minutes'],120);self.assertEqual(day['etag'],1)
        self.assertEqual(self.review(c).status_code,200);self.assertEqual(CapacityDay.objects.get().etag,1)
    def test_idempotent_proposal_and_changed_key_rejected(self):
        c=self.propose();self.assertEqual(self.propose()['id'],c['id']);self.assertEqual(CapacityChange.objects.count(),1)
        self.payload['minutes']=500;self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
    def test_daily_bounds_duplicate_services_and_cross_institution(self):
        for change in [{'unavailable_minutes':481},{'minutes':1441},{'allocations':[{'service':self.service.pk,'minutes':421}]},{'allocations':[{'service':self.service.pk,'minutes':100}]*2},{'allocations':[{'service':self.foreign.pk,'minutes':100}]},{'day':'2026-09-30'}]:
            self.assertEqual(self.client.post(self.url,{**self.payload,**change},format='json').status_code,400)
        self.assertEqual(CapacityChange.objects.count(),0)
        outside=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=Institution.objects.create(name='Outside'),name='Outside'),name='Outside'),name='Outside')
        RoleAssignment.objects.create(service=outside,user=self.author,role='manager',starts=date(2026,10,1),ends=date(2026,10,31),approved_by=self.admin)
        self.assertEqual(self.client.post(self.url,{**self.payload,'allocations':[{'service':outside.pk,'minutes':10}]},format='json').status_code,400)
    def test_services_share_one_capacity_pool(self):
        second=Service.objects.create(site=self.service.site,name='Second planning service')
        RoleAssignment.objects.create(service=second,user=self.author,role='contributor',starts=date(2026,10,1),ends=date(2026,10,31),approved_by=self.admin)
        self.payload['allocations']=[{'service':self.service.pk,'minutes':250},{'service':second.pk,'minutes':171}]
        self.assertEqual(self.client.post(self.url,self.payload,format='json').status_code,400)
        self.payload['allocations'][1]['minutes']=170;c=self.propose();self.assertEqual(self.review(c).status_code,200)
        self.assertEqual(self.board().data['days'][0]['unallocated_minutes'],0)
    def test_stale_proposals_preserve_approved_history(self):
        first=self.propose();self.payload.update(client_key=str(uuid.uuid4()),unavailable_minutes=120);second=self.propose()
        self.assertEqual(self.review(first).status_code,200);self.assertEqual(self.review(second).status_code,409)
        self.assertEqual(self.review(second,False).status_code,200)
        self.client.force_authenticate(self.author);self.payload.update(client_key=str(uuid.uuid4()),version=1,allocations=[],minutes=0,unavailable_minutes=0);third=self.propose();self.assertEqual(self.review(third).status_code,200)
        self.assertEqual(CapacityChange.objects.get(pk=first['id']).proposal['allocations'][0]['minutes'],300)
        self.assertEqual(CapacityChange.objects.get(pk=third['id']).previous['allocations'][0]['minutes'],300)
        self.assertEqual(CapacityDay.objects.get().etag,2)
    def test_authority_and_person_assignment_revalidated(self):
        c=self.propose();self.client.force_authenticate(self.other);self.assertEqual(self.board().status_code,403)
        self.client.force_authenticate(self.admin);self.assertEqual(self.board().status_code,403)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now());self.assertEqual(self.review(c).status_code,400)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=None);self.assertEqual(self.review(c).status_code,200)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        day=self.board().data['days'][0];self.assertTrue(day['needs_review']);self.assertEqual(day['allocations'][0]['minutes'],300)
        InstitutionMandate.objects.filter(user=self.reviewer).update(ends=timezone.localdate()-timedelta(days=1));self.assertEqual(self.board().status_code,403)
    def test_expired_assignment_can_be_cleared_only_by_new_zero_proposal(self):
        c=self.propose();self.assertEqual(self.review(c).status_code,200)
        RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.client.force_authenticate(self.author)
        self.payload.update(client_key=str(uuid.uuid4()),version=1,minutes=0,unavailable_minutes=0,allocations=[])
        clearing=self.propose();self.assertEqual(self.review(clearing).status_code,200)
        day=self.board().data['days'][0];self.assertEqual(day['available_minutes'],0);self.assertEqual(day['allocations'],[]);self.assertFalse(day['needs_review'])
        self.assertEqual(CapacityChange.objects.filter(state='approved').count(),2)
    def test_corrupt_proposal_and_period_rejected(self):
        c=self.propose();CapacityChange.objects.filter(pk=c['id']).update(proposal={'minutes':480,'unavailable_minutes':0,'allocations':[{'service':self.service.pk,'minutes':481}]})
        self.assertEqual(self.review(c).status_code,400)
        self.assertEqual(self.client.get(self.url,{'start':'9999-12-31'}).status_code,400)

class CapacityConcurrencyTests(TransactionTestCase):
    setUp=CapacityTests.setUp
    propose=CapacityTests.propose
    def test_competing_approvals_cannot_overallocate_or_overwrite(self):
        first=self.propose();self.payload.update(client_key=str(uuid.uuid4()),minutes=500);second=self.propose()
        def send(c):
            try:
                client=APIClient();client.force_authenticate(self.reviewer)
                return client.post(f"/api/v1/capacity/changes/{c['id']}/review/",{'approve':True,'rationale':'Concurrent synthetic review'},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(send,[first,second]))
        self.assertEqual(sorted(results),[200,409]);self.assertEqual(CapacityDay.objects.get().etag,1);self.assertEqual(CapacityChange.objects.filter(state='approved').count(),1)
