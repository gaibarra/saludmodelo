from datetime import date
from unittest.mock import patch
from django.test import TestCase,TransactionTestCase
from django.utils import timezone
from core import test_decisions
from core.models import WorkPlan,DecisionNoticeReceipt,RoleAssignment,Decision,AuditEvent

class DecisionNoticeTests(TestCase):
    def setUp(self):
        test_decisions.DecisionTests.setUp(self)
        self.plan=WorkPlan.objects.create(institution=self.service.site.campus.institution,etag=1,weekdays=[0,1,2,3,4],holidays=['2026-10-12'],confirmed_by=self.admin)
    create=test_decisions.DecisionTests.create
    act=test_decisions.DecisionTests.act
    def notices(self):return self.client.get(self.url).data['notices']['items']
    def ack(self,n):return self.client.post(f"/api/v1/decisions/{n['decision_id']}/acknowledge/",{k:n[k] for k in ['decision_version','calendar_version','stage']},format='json')
    def test_ack_is_personal_idempotent_and_does_not_resolve(self):
        d=self.create();n=self.notices()[0];self.assertEqual(n['stage'],0)
        self.assertEqual(self.ack(n).status_code,200);self.assertEqual(self.ack(n).status_code,200)
        self.assertEqual(DecisionNoticeReceipt.objects.count(),1)
        self.assertEqual(AuditEvent.objects.filter(action='decision.notice_acknowledged').count(),1)
        self.assertIsNotNone(self.notices()[0]['acknowledged_at'])
        self.client.force_authenticate(self.reviewer);self.assertIsNone(self.notices()[0]['acknowledged_at'])
        self.assertEqual(Decision.objects.get(pk=d['id']).state,'pending')
    def test_weekends_holidays_and_escalation(self):
        self.create();initial=self.notices()[0];self.ack(initial)
        for day in [date(2026,10,10),date(2026,10,12)]:
            with patch('core.tracking.workflow.today',return_value=day):self.assertEqual(self.notices(),[])
        with patch('core.tracking.workflow.today',return_value=date(2026,10,14)):
            n=self.notices()[0];self.assertEqual(n['working_days_late'],2);self.assertEqual(n['stage'],2)
            self.assertIsNone(n['acknowledged_at']);self.assertEqual(self.ack(initial).status_code,409);self.ack(n)
        with patch('core.tracking.workflow.today',return_value=date(2026,10,15)):
            self.assertEqual(self.notices()[0]['stage'],3);self.assertIsNone(self.notices()[0]['acknowledged_at'])
    def test_no_confirmed_calendar_future_due_or_closed_decision(self):
        d=self.create();self.plan.confirmed_by=None;self.plan.save()
        self.assertEqual(self.notices(),[])
        self.plan.confirmed_by=self.admin;self.plan.save()
        with patch('core.tracking.workflow.today',return_value=date(2026,10,8)):self.assertEqual(self.notices(),[])
        n=self.notices()[0];self.client.force_authenticate(self.reviewer);self.act(d)
        self.assertEqual(self.notices(),[]);self.assertEqual(self.ack(n).status_code,409)
    def test_reopen_and_calendar_change_require_fresh_receipt(self):
        d=self.create();n=self.notices()[0];self.ack(n)
        self.plan.etag+=1;self.plan.save();self.assertEqual(self.ack(n).status_code,409)
        self.assertIsNone(self.notices()[0]['acknowledged_at'])
        self.client.force_authenticate(self.reviewer);closed=self.act(d).data;self.act(closed,'reopen')
        self.client.force_authenticate(self.author);self.assertIsNone(self.notices()[0]['acknowledged_at'])
        self.assertEqual(DecisionNoticeReceipt.objects.count(),1)
    def test_scope_and_nonrecipient(self):
        self.create();n=self.notices()[0]
        self.client.force_authenticate(self.sub);self.assertEqual(self.notices(),[]);self.assertEqual(self.ack(n).status_code,409)
        for user in [self.other,self.admin]:
            self.client.force_authenticate(user);self.assertEqual(self.ack(n).status_code,404)
        self.client.force_authenticate(self.author);RoleAssignment.objects.filter(user=self.author).update(revoked_at=timezone.now())
        self.assertEqual(self.ack(n).status_code,404)

class ConcurrentDecisionNoticeTests(TransactionTestCase):
    def test_duplicate_acknowledgements_have_one_receipt(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        from rest_framework.test import APIClient
        DecisionNoticeTests.setUp(self)
        d=test_decisions.DecisionTests.create(self)
        def ack(_):
            try:
                c=APIClient();c.force_authenticate(self.author)
                return c.post(f"/api/v1/decisions/{d['id']}/acknowledge/",{'decision_version':1,'calendar_version':1,'stage':0},format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(ack,range(2)))
        self.assertEqual(results,[200,200]);self.assertEqual(DecisionNoticeReceipt.objects.count(),1)
