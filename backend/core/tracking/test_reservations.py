from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from core.models import PlanningPolicy,TaskReservation,CapacityDay,CapacityAllocation,WorkPlan,Task,BaselineChange,InstitutionMandate,TimeEntry,GovernanceEvent
from core.reservations import check
from . import test_tracking

class ReservationTests(TransactionTestCase):
    create=test_tracking.TrackingTests.create
    propose=test_tracking.TrackingTests.propose
    def setUp(self):
        test_tracking.TrackingTests.setUp(self)
        self.institution=self.service.site.campus.institution
        InstitutionMandate.objects.create(institution=self.institution,user=self.reviewer,approved_by=self.admin,starts=timezone.localdate()-timedelta(days=1),ends=date(2027,12,31),rationale='Synthetic mandate')
        self.policy=PlanningPolicy.objects.create(institution=self.institution,enforced=True,base_minutes=1000,reserve_minutes=200)
        WorkPlan.objects.create(institution=self.institution,weekdays=[0,1,2,3,4],holidays=[],confirmed_by=self.admin)
        self.day=CapacityDay.objects.create(institution=self.institution,person=self.author,day=date(2026,10,5),confirmed=True,minutes=240,etag=1)
        CapacityAllocation.objects.create(capacity=self.day,service=self.service,minutes=240)
        self.rows=[{'person':self.author.pk,'day':'2026-10-05','minutes':120}]
    def change(self,**extra):
        task=self.create();return self.propose(task,reservation_plan=self.rows,**extra)
    def decision(self,task):
        self.client.force_authenticate(self.reviewer)
        return self.client.post(f"/api/v1/tracking/changes/{task['changes'][0]['id']}/decision/",{'approve':True,'rationale':'Synthetic review'},format='json')
    def test_approval_reserves_and_simulation_rolls_back(self):
        task=self.change();self.client.force_authenticate(self.reviewer)
        response=self.client.post(f"/api/v1/tracking/changes/{task['changes'][0]['id']}/preview/",{},format='json')
        self.assertTrue(response.data['can_approve'],response.data)
        self.assertEqual(TaskReservation.objects.count(),0)
        self.assertFalse(Task.objects.get(pk=task['id']).committed)
        self.assertEqual(self.decision(task).status_code,200)
        self.assertEqual(TaskReservation.objects.get().minutes,120)
    def test_missing_capacity_and_incomplete_reservations_rejected_atomically(self):
        task=self.create();task=self.propose(task)
        self.assertEqual(self.decision(task).status_code,400)
        self.assertFalse(Task.objects.get(pk=task['id']).committed)
        BaselineChange.objects.all().delete()
        task=self.propose(task,reservation_plan=self.rows)
        self.day.confirmed=False;self.day.save()
        self.assertEqual(self.decision(task).status_code,400)
        self.assertEqual(TaskReservation.objects.count(),0)
    def test_absence_keeps_commitment_and_replan_resolves_conflict(self):
        task=self.change();self.assertEqual(self.decision(task).status_code,200)
        self.day.allocations.update(minutes=60);self.day.unavailable_minutes=180;self.day.etag=2;self.day.save()
        self.assertEqual(check(self.institution.pk)['issues'][0]['reason'],'over_capacity')
        task=self.client.get(f"/api/v1/tracking/tasks/{task['id']}/").data
        rows=[{**self.rows[0],'minutes':60}]
        task=self.propose(task,estimated_minutes=60,reservation_plan=rows)
        self.assertEqual(self.decision(task).status_code,200)
        self.assertEqual(check(self.institution.pk)['issues'],[])
    def test_concurrent_approvals_cannot_double_book(self):
        self.day.allocations.update(minutes=120)
        tasks=[self.change(),self.change()]
        def approve(task):
            try:
                client=APIClient();client.force_authenticate(self.reviewer)
                return client.post(f"/api/v1/tracking/changes/{task['changes'][0]['id']}/decision/",{'approve':True,'rationale':'Concurrent'},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(approve,tasks))
        self.assertEqual(sorted(codes),[200,400]);self.assertEqual(TaskReservation.objects.count(),1)
    def test_reserve_budget_actual_time_and_cancellation_history(self):
        task=self.change(budget_bucket='reserve');self.assertEqual(self.decision(task).status_code,200)
        self.client.force_authenticate(self.author)
        import uuid
        response=self.client.post(f"/api/v1/tracking/tasks/{task['id']}/time/",{'day':'2026-10-05','minutes':30,'note':'Reserve actual','client_key':str(uuid.uuid4())},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(check(self.institution.pk)['budgets']['reserve']['actual_minutes'],30)
        task=self.propose(response.data,cancel=True,reservation_plan=self.rows,budget_bucket='reserve')
        self.assertEqual(self.decision(task).status_code,200)
        self.assertEqual(TaskReservation.objects.count(),0)
        self.assertEqual(check(self.institution.pk)['budgets']['reserve']['actual_minutes'],30)
        self.assertEqual(check(self.institution.pk)['budgets']['reserve']['remaining_minutes'],170)
    def test_budget_limit_and_control_permissions(self):
        self.policy.reserve_minutes=100;self.policy.save()
        self.assertEqual(self.decision(self.change(budget_bucket='reserve')).status_code,400)
        url=f'/api/v1/capacity/institutions/{self.institution.pk}/planning/'
        self.client.force_authenticate(self.author);self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_authenticate(self.reviewer)
        response=self.client.post(url,{'version':0,'enforced':True,'base_minutes':1000,'reserve_minutes':200,'rationale':'Confirm synthetic budgets'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(GovernanceEvent.objects.filter(action='planning.control_changed').count(),1)
