from datetime import date
from django.test import TransactionTestCase
from core.models import Task,Service,RoleAssignment,TaskEvent
from . import test_tracking

class PlanningClosureTests(TransactionTestCase):
    create=test_tracking.TrackingTests.create
    propose=test_tracking.TrackingTests.propose
    approve=test_tracking.TrackingTests.approve
    def setUp(self):test_tracking.TrackingTests.setUp(self)
    def test_cross_service_authority_and_dependency_invalidation(self):
        other=Service.objects.create(site=self.service.site,name='Other same institution',confirmed=True)
        for user,role in [(self.author,'manager'),(self.reviewer,'director')]:
            RoleAssignment.objects.create(user=user,service=other,role=role,starts=date(2026,1,1),ends=date(2027,12,31),approved_by=self.admin)
        parent=Task.objects.create(service=other,owner=self.author,title='Parent',deduplication_key='crossparent',starts=date(2026,10,1),due=date(2026,10,2),committed=True,state='accepted')
        task=self.create(predecessors=[parent.pk]);task=self.propose(task,predecessors=[parent.pk])
        grant=RoleAssignment.objects.get(user=self.reviewer,service=other);grant.role='auditor';grant.save()
        self.client.force_authenticate(self.reviewer)
        url=f"/api/v1/tracking/changes/{task['changes'][0]['id']}/decision/"
        self.assertEqual(self.client.post(url,{'approve':True,'rationale':'Needs both scopes'},format='json').status_code,403)
        grant.role='director';grant.save();task=self.approve(task)
        self.assertTrue(task['committed'])
        Task.objects.filter(pk=task['id']).update(state='accepted')
        self.client.force_authenticate(self.author)
        parent_data=self.client.get(f'/api/v1/tracking/tasks/{parent.pk}/').data
        proposed=self.client.post(f'/api/v1/tracking/tasks/{parent.pk}/change/',{**self.body,'version':parent_data['etag'],'title':'Parent changed','substitute':None,'coordinator':None,'starts':'2026-10-01','due':'2026-10-02','rationale':'Reopen predecessor'},format='json')
        self.assertEqual(proposed.status_code,200,proposed.data)
        self.approve(proposed.data)
        self.assertEqual(Task.objects.get(pk=task['id']).state,'returned')
    def test_history_beyond_100_and_cursor_scope(self):
        task=self.create();TaskEvent.objects.bulk_create([TaskEvent(task_id=task['id'],actor=self.author,kind='synthetic',note=f'Event {n}') for n in range(105)])
        url=f"/api/v1/tracking/tasks/{task['id']}/history/"
        seen=[];cursor=None
        while True:
            page=self.client.get(url,{'kind':'events',**({'before':cursor} if cursor else {})})
            self.assertEqual(page.status_code,200,page.data)
            seen.extend(r['id'] for r in page.data['results']);cursor=page.data['next_before']
            if cursor is None:break
        self.assertEqual(len(seen),106);self.assertEqual(len(set(seen)),106)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url,{'kind':'events','before':seen[0]}).status_code,404)
