import uuid
from datetime import date
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from core.tracking import test_tracking as fixtures
from core.tracking import workflow
from core.models import RoleAssignment,Task,WorkPlan,OutboxEvent,Notification,Decision,DecisionNoticeReceipt

class TaskCoverageTests(TestCase):
    def setUp(self):
        fixtures.TrackingTests.setUp(self)
        self.source=RoleAssignment.objects.get(user=self.author,role='manager')
        self.source.role='contributor';self.source.save()
        self.grant=RoleAssignment.objects.get(user=self.sub)
        self.grant.substitutes=self.source;self.grant.save()
        self.task=Task.objects.create(service=self.service,owner=self.author,title='Covered task',deduplication_key='coverage-test',committed=True,starts=date(2026,10,1),due=date(2026,10,5))
        WorkPlan.objects.create(institution=self.service.site.campus.institution,weekdays=list(range(5)),holidays=[],confirmed_by=self.admin,etag=1)
    def transition(self,target,user=None):
        self.task.refresh_from_db();self.client.force_authenticate(user or self.sub)
        return self.client.post(f'/api/v1/tracking/tasks/{self.task.pk}/state/',{'version':self.task.etag,'target':target,'note':'Synthetic coverage work'},format='json')
    def test_work_without_reassignment_and_real_actor_in_history(self):
        self.assertEqual(self.transition('in_progress').status_code,200)
        self.assertEqual(self.transition('submitted').status_code,200)
        self.task.refresh_from_db();self.assertEqual(self.task.owner_id,self.author.pk);self.assertEqual(self.task.submitted_by_id,self.sub.pk)
        event=self.task.events.latest('pk');self.assertEqual(event.actor_id,self.sub.pk);self.assertEqual(event.snapshot['actor_coverage_ids'],[self.grant.pk])
        self.assertEqual(self.transition('accepted',self.reviewer).status_code,200)
    def test_expired_or_revoked_coverage_does_not_use_other_role_as_coverage(self):
        self.grant.revoked_at=timezone.now();self.grant.save()
        RoleAssignment.objects.create(user=self.sub,service=self.service,role='contributor',starts=self.grant.starts,ends=self.grant.ends,approved_by=self.admin)
        self.assertEqual(self.transition('in_progress').status_code,403)
        self.grant.revoked_at=None;self.grant.ends=timezone.localdate().replace(year=2025);self.grant.starts=self.grant.ends;self.grant.save()
        self.assertEqual(self.transition('in_progress').status_code,403)
    def test_supplementary_manager_role_cannot_self_review_covered_task(self):
        RoleAssignment.objects.create(user=self.sub,service=self.service,role='manager',starts=self.grant.starts,ends=self.grant.ends,approved_by=self.admin)
        self.assertEqual(self.transition('submitted',self.author).status_code,200)
        self.assertEqual(self.transition('accepted').status_code,400)
    def test_reminder_deduplication_and_delivery(self):
        self.assertEqual(workflow.reminders(),2);self.assertEqual(workflow.reminders(),0)
        queued=OutboxEvent.objects.get(coverage=self.grant);self.assertEqual(queued.recipient_id,self.sub.pk)
        call_command('worker');self.assertTrue(Notification.objects.filter(event=queued,recipient=self.sub).exists())
        self.client.force_authenticate(self.sub)
        board=self.client.get(f'/api/v1/tracking/services/{self.service.pk}/').data
        self.assertEqual(board['tasks'][0]['active_substitutions'][0]['id'],self.grant.pk)
        self.assertEqual(len(board['notifications']),1)
    def test_revocation_before_delivery_and_after_delivery_hides_notice(self):
        workflow.reminders();self.grant.revoked_at=timezone.now();self.grant.save()
        RoleAssignment.objects.create(user=self.sub,service=self.service,role='contributor',starts=self.grant.starts,ends=self.grant.ends,approved_by=self.admin)
        call_command('worker');self.assertFalse(Notification.objects.filter(recipient=self.sub).exists())
        self.grant.revoked_at=None;self.grant.save();self.task.etag+=1;self.task.save();workflow.reminders();call_command('worker')
        self.assertTrue(Notification.objects.filter(recipient=self.sub).exists())
        self.grant.revoked_at=timezone.now();self.grant.save();self.client.force_authenticate(self.sub)
        self.assertEqual(self.client.get(f'/api/v1/tracking/services/{self.service.pk}/').data['notifications'],[])
    def test_decision_notice_for_covered_requester_and_personal_ack(self):
        d=Decision.objects.create(service=self.service,requested_by=self.author,title='Coverage decision',question='Which?',alternatives='A/B',due=date(2026,10,5))
        self.client.force_authenticate(self.sub)
        url=f'/api/v1/decisions/services/{self.service.pk}/'
        n=self.client.get(url).data['notices']['items'][0];self.assertEqual(n['coverage_ids'],[self.grant.pk])
        payload={k:n[k] for k in ['decision_version','calendar_version','stage']}
        self.assertEqual(self.client.post(f'/api/v1/decisions/{d.pk}/acknowledge/',payload,format='json').status_code,200)
        self.assertEqual(DecisionNoticeReceipt.objects.get().coverage_ids,[self.grant.pk])
        self.grant.revoked_at=timezone.now();self.grant.save()
        RoleAssignment.objects.create(user=self.sub,service=self.service,role='contributor',starts=self.grant.starts,ends=self.grant.ends,approved_by=self.admin)
        self.assertEqual(self.client.get(url).data['notices']['items'],[])
        self.assertEqual(self.client.post(f'/api/v1/decisions/{d.pk}/acknowledge/',payload,format='json').status_code,409)
    def test_notice_starts_at_second_workday_and_skips_explicit_duplicate(self):
        with patch('core.tracking.workflow.today',return_value=date(2026,10,5)):workflow.reminders()
        self.assertFalse(OutboxEvent.objects.filter(coverage=self.grant).exists())
        self.task.substitute=self.sub;self.task.save();workflow.reminders()
        self.assertFalse(OutboxEvent.objects.filter(coverage=self.grant).exists())
        self.assertEqual(OutboxEvent.objects.filter(recipient=self.sub).count(),1)
    def test_dependency_changes_notify_coverage_without_changing_owner(self):
        from types import SimpleNamespace
        from core.models import TaskDependency
        predecessor=Task.objects.create(service=self.service,owner=self.author,title='Predecessor',deduplication_key='predecessor-coverage',committed=True)
        TaskDependency.objects.create(task=self.task,predecessor=predecessor)
        self.task.state='in_progress';self.task.save()
        workflow.invalidate_successors(self.reviewer,predecessor,SimpleNamespace(pk=123))
        queued=OutboxEvent.objects.get(coverage=self.grant)
        self.assertIn('dependency',queued.key);call_command('worker')
        self.assertTrue(Notification.objects.filter(event=queued).exists())
        self.task.refresh_from_db();self.assertEqual(self.task.owner_id,self.author.pk)
