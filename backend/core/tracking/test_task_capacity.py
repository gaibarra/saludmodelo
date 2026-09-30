from datetime import date
from django.test import TransactionTestCase
from django.utils import timezone
from core.models import Task,WorkPlan,CapacityDay,CapacityAllocation,RoleAssignment
from . import test_tracking

class TaskCapacityTests(TransactionTestCase):
    create=test_tracking.TrackingTests.create
    def setUp(self):
        test_tracking.TrackingTests.setUp(self)
        self.task=self.create(starts='2026-10-05',due='2026-10-06',estimated_minutes=121)
        Task.objects.filter(pk=self.task['id']).update(committed=True)
        self.plan=WorkPlan.objects.create(institution=self.service.site.campus.institution,weekdays=[0,1,2,3,4],holidays=[],confirmed_by=self.admin,etag=1)
        self.url=f'/api/v1/tracking/services/{self.service.pk}/capacity/'
    def get(self):return self.client.get(self.url,{'start':'2026-10-05'})
    def capacity(self,minutes=100,unavailable=40,allocated=60):
        day=CapacityDay.objects.create(institution=self.service.site.campus.institution,person=self.author,day=date(2026,10,5),minutes=minutes,unavailable_minutes=unavailable,confirmed=True,etag=1)
        if allocated:CapacityAllocation.objects.create(capacity=day,service=self.service,minutes=allocated)
        return day
    def test_distribution_absence_overload_and_unknown(self):
        self.capacity()
        response=self.get();self.assertEqual(response.status_code,200,response.data)
        rows=response.data['rows'];self.assertEqual([r['planned_minutes'] for r in rows],[61,60])
        self.assertEqual((rows[0]['allocated_minutes'],rows[0]['overload_minutes'],rows[0]['has_unavailability']),(60,1,True))
        self.assertEqual(rows[1]['status'],'unconfirmed');self.assertIsNone(rows[1]['overload_minutes'])
        self.assertEqual(response['Cache-Control'],'private, no-store')
    def test_changed_approved_absence_is_reflected_without_task_mutation(self):
        day=self.capacity(minutes=100,unavailable=0,allocated=100)
        self.assertEqual(self.get().data['rows'][0]['status'],'within_capacity')
        day.unavailable_minutes=100;day.etag=2;day.save();day.allocations.all().delete()
        row=self.get().data['rows'][0]
        self.assertEqual((row['allocated_minutes'],row['overload_minutes'],row['capacity_version']),(0,61,2))
        task=Task.objects.get(pk=self.task['id']);self.assertEqual(task.estimated_minutes,121);self.assertEqual(task.owner_id,self.author.pk);self.assertEqual(task.etag,self.task['etag'])
    def test_unconfirmed_calendar_and_capacity_not_treated_as_zero(self):
        day=self.capacity();day.confirmed=False;day.save()
        self.assertEqual(self.get().data['rows'][0]['status'],'unconfirmed')
        self.plan.confirmed_by=None;self.plan.save()
        self.assertEqual(self.get().data['rows'],[]);self.assertFalse(self.get().data['calendar_confirmed'])
    def test_holidays_zero_estimate_and_closed_or_uncommitted(self):
        self.plan.holidays=['2026-10-05'];self.plan.save()
        self.assertEqual([r['planned_minutes'] for r in self.get().data['rows']],[121])
        Task.objects.filter(pk=self.task['id']).update(estimated_minutes=0)
        self.assertEqual(self.get().data['issues'][0]['reason'],'missing_estimate')
        for state in ['accepted','cancelled']:
            Task.objects.filter(pk=self.task['id']).update(state=state)
            self.assertEqual(self.get().data['issues'],[])
        Task.objects.filter(pk=self.task['id']).update(state='pending',committed=False)
        self.assertEqual(self.get().data['rows'],[])
    def test_read_scope_and_revoked_owner_assignment(self):
        self.capacity();RoleAssignment.objects.filter(user=self.author).update(role='auditor')
        row=self.get().data['rows'][0];self.assertEqual(row['status'],'assignment_review');self.assertIsNone(row['allocated_minutes'])
        for user in [self.other,self.admin]:
            self.client.force_authenticate(user);self.assertEqual(self.get().status_code,404)
        self.client.force_authenticate(self.author);RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.assertEqual(self.get().status_code,404)
    def test_dates_and_no_workdays(self):
        self.assertEqual(self.client.get(self.url).status_code,400)
        self.assertEqual(self.client.get(self.url,{'start':'2026-09-30'}).status_code,400)
        self.plan.holidays=['2026-10-05','2026-10-06'];self.plan.save()
        self.assertEqual(self.get().data['issues'][0]['reason'],'no_workdays')
    def test_combined_task_load_and_other_service_allocation_not_available(self):
        from core.models import Service
        day=self.capacity(minutes=200,unavailable=0,allocated=60)
        other=Service.objects.create(site=self.service.site,name='Other capacity service',confirmed=True)
        CapacityAllocation.objects.create(capacity=day,service=other,minutes=140)
        Task.objects.create(service=self.service,owner=self.author,title='Second task',deduplication_key='capacity-second',committed=True,starts=date(2026,10,5),due=date(2026,10,5),estimated_minutes=50)
        row=self.get().data['rows'][0]
        self.assertEqual((row['planned_minutes'],row['allocated_minutes'],row['overload_minutes']),(111,60,51))
        self.assertEqual(len(row['tasks']),2)
        self.assertNotIn('unavailable_minutes',row);self.assertNotIn('allocations',row)
