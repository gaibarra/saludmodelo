import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timezone as dt_timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from core.models import AdministrativeTimeCorrection,TimeEntry,TimeCorrection,RoleAssignment,Task,TaskEvent
from core.time_accounting import total
from . import test_tracking

class AdministrativeTimeTests(TransactionTestCase):
    create=test_tracking.TrackingTests.create
    def setUp(self):
        test_tracking.TrackingTests.setUp(self)
        self.task=self.create()
        self.entry=TimeEntry.objects.create(task_id=self.task['id'],actor=self.author,day=date(2026,10,6),minutes=60,note='Original',client_key=uuid.uuid4())
        self.director=get_user_model().objects.create_user('independent-director')
        RoleAssignment.objects.create(user=self.director,service=self.service,role='director',starts=timezone.localdate(),ends=date(2027,12,31),approved_by=self.admin)
        self.url_request=f'/api/v1/tracking/time/{self.entry.pk}/administrative/'
        self.url_list=f"/api/v1/tracking/tasks/{self.task['id']}/time-requests/"
        self.payload={'version':0,'minutes':30,'rationale':'Correction supported by verified attendance','client_key':str(uuid.uuid4())}
    def request(self,user=None,**extra):
        self.client.force_authenticate(user or self.reviewer)
        return self.client.post(self.url_request,{**self.payload,**extra},format='json')
    def decide(self,pk,user=None,approve=True,reason='Independent review'):
        self.client.force_authenticate(user or self.director)
        return self.client.post(f'/api/v1/tracking/time-requests/{pk}/decision/',{'approve':approve,'rationale':reason},format='json')
    def test_approval_original_totals_history_and_idempotency(self):
        r=self.request();self.assertEqual(r.status_code,201,r.data);pk=r.data['id']
        self.assertEqual(total(TimeEntry.objects.all()),60)
        self.assertEqual(self.request().data['id'],pk)
        self.assertEqual(self.request(minutes=20).status_code,409)
        response=self.decide(pk);self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(total(TimeEntry.objects.all()),30)
        self.entry.refresh_from_db();self.assertEqual(self.entry.minutes,60)
        self.assertEqual(self.decide(pk).status_code,200)
        self.assertEqual(self.decide(pk,approve=False).status_code,409)
        self.assertEqual(TimeCorrection.objects.count(),1)
        correction=TimeCorrection.objects.get();self.assertEqual(correction.actor_id,self.director.pk)
        self.assertEqual(correction.administrative_request.pk,pk)
        self.assertEqual(TaskEvent.objects.filter(kind='time.admin_approved').count(),1)
    def test_no_self_review_or_approval_by_hours_author(self):
        pk=self.request().data['id']
        self.assertEqual(self.decide(pk,user=self.reviewer).status_code,400)
        RoleAssignment.objects.filter(user=self.author).update(role='director')
        self.assertEqual(self.decide(pk,user=self.author).status_code,400)
        self.assertEqual(self.request(user=self.author).status_code,400)
        self.assertEqual(TimeCorrection.objects.count(),0)
    def test_permissions_scope_inactive_and_invalid_input(self):
        for user in [self.author,self.sub,self.admin,self.other]:
            self.assertIn(self.request(user=user).status_code,[403,404])
        for values in [{'minutes':1441},{'minutes':-1},{'minutes':60},{'rationale':''},{'version':-1}]:
            self.assertEqual(self.request(**values).status_code,400)
        self.assertEqual(self.request(version=1).status_code,409)
        get_user_model().objects.filter(pk=self.reviewer.pk).update(is_active=False)
        self.assertIn(self.request().status_code,[403,404])
    def test_revalidate_both_authorities_and_allow_rejection(self):
        pk=self.request().data['id']
        RoleAssignment.objects.filter(user=self.reviewer).update(revoked_at=timezone.now())
        self.assertEqual(self.decide(pk).status_code,403)
        self.assertEqual(self.decide(pk,approve=False).status_code,200)
        self.assertEqual(total(TimeEntry.objects.all()),60)
        self.assertEqual(self.decide(pk,approve=False).status_code,200)
    def test_stale_proposal_does_not_override_author_correction(self):
        pk=self.request().data['id'];self.client.force_authenticate(self.author)
        response=self.client.post(f'/api/v1/tracking/time/{self.entry.pk}/correct/',{'version':0,'minutes':45,'rationale':'Author correction'},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.decide(pk).status_code,409)
        self.assertEqual(self.decide(pk,approve=False).status_code,200)
        self.assertEqual(total(TimeEntry.objects.all()),45)
    def test_inactive_original_author_can_be_corrected_and_daily_limit(self):
        get_user_model().objects.filter(pk=self.author.pk).update(is_active=False)
        other_task=Task.objects.create(service=self.foreign,owner=self.author,title='Historical work in another service',deduplication_key='admin-other-service')
        TimeEntry.objects.create(task=other_task,actor=self.author,day=self.entry.day,minutes=1400,note='Other work',client_key=uuid.uuid4())
        pk=self.request(minutes=41).data['id'];self.assertEqual(self.decide(pk).status_code,400)
        self.assertEqual(TimeCorrection.objects.count(),0)
        self.assertEqual(self.decide(pk,approve=False).status_code,200)
        pk=self.request(minutes=40,client_key=str(uuid.uuid4())).data['id'];self.assertEqual(self.decide(pk).status_code,200)
        self.assertEqual(total(TimeEntry.objects.all()),1440)
    def test_two_concurrent_approvals_do_not_double_apply(self):
        first=self.request().data['id'];second=self.request(minutes=20,client_key=str(uuid.uuid4())).data['id']
        def send(pk):
            try:
                client=APIClient();client.force_authenticate(self.director)
                return client.post(f'/api/v1/tracking/time-requests/{pk}/decision/',{'approve':True,'rationale':'Independent concurrent review'},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(send,[first,second]))
        self.assertEqual(sorted(codes),[200,409]);self.assertEqual(TimeCorrection.objects.count(),1)
    def test_list_pagination_and_scope_revalidation(self):
        for i in range(52):
            AdministrativeTimeCorrection.objects.create(entry=self.entry,requested_by=self.reviewer,client_key=uuid.uuid4(),expected_version=0,previous_minutes=60,minutes=30,rationale=f'Historic {i}')
        self.client.force_authenticate(self.director)
        first=self.client.get(self.url_list);self.assertEqual(first.status_code,200)
        self.assertEqual(len(first.data['results']),50);self.assertTrue(first.data['results'][0]['can_review'])
        second=self.client.get(self.url_list,{'before':first.data['next_before']});self.assertEqual(len(second.data['results']),2)
        RoleAssignment.objects.filter(user=self.director).update(revoked_at=timezone.now())
        self.assertEqual(self.client.get(self.url_list).status_code,404)
    def test_self_correction_retry_does_not_claim_admin_action(self):
        pk=self.request().data['id'];self.assertEqual(self.decide(pk).status_code,200)
        self.client.force_authenticate(self.author)
        response=self.client.post(f'/api/v1/tracking/time/{self.entry.pk}/correct/',{'version':0,'minutes':30,'rationale':self.payload['rationale']},format='json')
        self.assertEqual(response.status_code,409)
    def test_cancelled_task_and_revoked_reviewer(self):
        Task.objects.filter(pk=self.task['id']).update(state='cancelled')
        pk=self.request(minutes=0).data['id']
        RoleAssignment.objects.filter(user=self.director).update(revoked_at=timezone.now())
        self.assertIn(self.decide(pk).status_code,[403,404])
        RoleAssignment.objects.filter(user=self.director).update(revoked_at=None)
        self.assertEqual(self.decide(pk).status_code,200)
        self.assertEqual(Task.objects.get(pk=self.task['id']).state,'cancelled')
        self.assertEqual(total(TimeEntry.objects.all()),0)

    def test_saved_reports_stay_immutable_after_administrative_approval(self):
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,9,18,tzinfo=dt_timezone.utc)):
            self.client.force_authenticate(self.author)
            url=f"/api/v1/reports/services/{self.service.pk}/saved/"
            first=self.client.post(url,{'start':'2026-10-05','client_key':str(uuid.uuid4())},format='json')
            self.assertEqual(first.status_code,201,first.data)
            pk=self.request().data['id'];self.assertEqual(self.decide(pk).status_code,200)
            second=self.client.post(url,{'start':'2026-10-05','client_key':str(uuid.uuid4())},format='json')
            self.assertEqual(second.status_code,201,second.data)
            self.assertEqual(second.data['content']['period_activity']['minutes'],30)
            old=self.client.get(f"/api/v1/reports/saved/{first.data['id']}/").data
            self.assertEqual(old['content'],first.data['content'])
            self.assertEqual(old['content_hash'],first.data['content_hash'])
            self.assertEqual(old['content']['period_activity']['minutes'],60)

    def test_author_and_admin_concurrent_changes_have_one_winner(self):
        pk=self.request().data['id']
        def send(administrative):
            try:
                client=APIClient();client.force_authenticate(self.director if administrative else self.author)
                url=f'/api/v1/tracking/time-requests/{pk}/decision/' if administrative else f'/api/v1/tracking/time/{self.entry.pk}/correct/'
                payload={'approve':True,'rationale':'Concurrent approval'} if administrative else {'version':0,'minutes':45,'rationale':'Concurrent self correction'}
                return client.post(url,payload,format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(send,[True,False]))
        self.assertEqual(sorted(codes),[200,409]);self.assertEqual(TimeCorrection.objects.count(),1)
