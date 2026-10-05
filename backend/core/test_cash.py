import uuid
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Institution,Campus,Site,School,SchoolMember,SchoolMandate,InstitutionMandate,Service,CashShift,CashMovement,GovernanceEvent

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class CashTests(TestCase):
    def setUp(self):
        U=get_user_model();self.director=U.objects.create_user('health-director');self.other=U.objects.create_user('dental-director');self.admin=U.objects.create_user('institution-admin');self.cashier=U.objects.create_user('cashier');self.stranger=U.objects.create_user('stranger');self.approver=U.objects.create_user('approver')
        inst=Institution.objects.create(name='Modelo');campus=Campus.objects.create(institution=inst,name='Mérida');site=Site.objects.create(campus=campus,name='Prueba')
        self.health=School.objects.create(institution=inst,code='salud',name='Salud');self.dental=School.objects.create(institution=inst,code='odontologia',name='Odontología')
        self.service=Service.objects.create(school=self.health,site=site,name='Psicología');self.foreign=Service.objects.create(school=self.dental,site=site,name='Dental')
        self.now=timezone.now();self.start=self.now-timedelta(minutes=5);self.end=self.now+timedelta(hours=6)
        for s,u in [(self.health,self.director),(self.dental,self.other)]:SchoolMandate.objects.create(school=s,user=u,approved_by=self.approver,starts=self.now.date()-timedelta(days=1),ends=self.now.date()+timedelta(days=30),rationale='Prueba')
        SchoolMember.objects.create(school=self.health,user=self.cashier)
        InstitutionMandate.objects.create(institution=inst,user=self.admin,approved_by=self.approver,starts=self.now.date()-timedelta(days=1),ends=self.now.date()+timedelta(days=30),rationale='Prueba')
        self.c=APIClient();self.as_user(self.director)
    def as_user(self,u):self.c.force_authenticate(u)
    def assign(self):
        return self.c.post('/api/v1/cash/shifts/',{'service':self.service.pk,'responsible':self.cashier.pk,'label':'Matutino','starts':self.start.isoformat(),'ends':self.end.isoformat(),'client_key':str(uuid.uuid4())},format='json')
    def setup_shift(self):
        r=self.assign();self.assertEqual(r.status_code,201,r.data);self.pk=r.data['id'];self.url=f'/api/v1/cash/shifts/{self.pk}/';self.as_user(self.cashier)
        r=self.action('open','100.00');self.assertEqual(r.status_code,200,r.data)
    def revision(self):return CashShift.objects.get(pk=self.pk).revision
    def action(self,action,amount='0.00',reason=''):
        return self.c.post(self.url,{'action':action,'amount':amount,'reason':reason,'revision':self.revision()},format='json')
    def movement(self,kind='collection',amount='50.00',**extra):
        return self.c.post(self.url+'movements/',{'kind':kind,'amount':amount,'concept':'Prueba','revision':self.revision(),'client_key':str(uuid.uuid4()),**extra},format='json')
    def test_full_cash_cycle_and_immutable_close(self):
        self.setup_shift();r=self.movement();self.assertEqual(r.status_code,201,r.data)
        refund=self.movement('refund','10.00',related=r.data['id']);self.assertEqual(refund.status_code,201,refund.data)
        self.assertEqual(self.movement('withdrawal','20.00').status_code,201)
        self.assertEqual(self.movement('fund_in','5.00').status_code,201)
        r=self.action('close','125.00');self.assertEqual(r.status_code,200,r.data);self.assertEqual(r.data['difference'],'0.00');self.assertEqual(r.data['expected'],'125.00')
        self.assertEqual(self.movement().status_code,409);self.assertEqual(self.action('open','1.00').status_code,409)
        self.assertEqual(self.c.delete(self.url+'movements/').status_code,405)
        self.assertEqual(CashMovement.objects.count(),4)
        self.assertGreaterEqual(GovernanceEvent.objects.filter(action__startswith='cash.').count(),7)
    def test_school_and_institution_monitoring(self):
        self.setup_shift();self.movement()
        self.as_user(self.other)
        self.assertEqual(self.c.get(self.url).status_code,404)
        self.assertEqual(self.c.get(self.url+'movements/').status_code,404)
        self.assertEqual(self.c.get('/api/v1/cash/summary/').data['totals'],{})
        self.assertEqual(self.c.get('/api/v1/cash/summary/',{'service':self.service.pk}).status_code,404)
        self.assertEqual(self.c.get(f'/api/v1/cash/services/{self.service.pk}/responsibles/').status_code,404)
        self.as_user(self.director);self.assertEqual(self.c.get('/api/v1/cash/summary/').data['totals']['collection'],'50.00')
        self.assertEqual(self.action('close','150').status_code,403)
        self.as_user(self.admin);self.assertEqual(self.c.get('/api/v1/cash/services/').data['count'],2);self.assertEqual(self.c.get(self.url).status_code,200)
    def test_only_assigned_cashier_and_membership_revocation(self):
        self.setup_shift();self.as_user(self.stranger);self.assertEqual(self.c.get(self.url).status_code,404)
        self.as_user(self.cashier);SchoolMember.objects.filter(user=self.cashier).delete()
        self.assertEqual(self.c.get(self.url).status_code,404);self.assertEqual(self.movement().status_code,404)
    def test_idempotency_conflict_and_non_cash_rejected(self):
        self.setup_shift();key=str(uuid.uuid4());rev=self.revision()
        r=self.movement(client_key=key);self.assertEqual(r.status_code,201)
        repeat=self.movement(client_key=key,revision=rev);self.assertEqual(repeat.status_code,200);self.assertEqual(repeat.data['id'],r.data['id'])
        self.assertEqual(self.movement(amount='51.00',client_key=key).status_code,409)
        self.assertEqual(self.movement(method='card').status_code,400)
        self.assertEqual(self.movement(amount='1.001').status_code,400)
        self.assertEqual(self.movement(amount='-1.00').status_code,400)
        self.assertEqual(self.movement(revision=rev).status_code,409)
    def test_refunds_and_insufficient_cash(self):
        self.setup_shift();r=self.movement();pk=r.data['id']
        self.assertEqual(self.movement('refund','51.00',related=pk).status_code,400)
        self.assertEqual(self.movement('refund','40.00',related=pk).status_code,201)
        self.assertEqual(self.movement('refund','11.00',related=pk).status_code,400)
        self.assertEqual(self.movement('withdrawal','111.00').status_code,400)
        self.assertEqual(self.movement('collection',related=pk).status_code,400)
    def test_discrepancy_and_cancel_rules(self):
        self.setup_shift();self.assertEqual(self.action('close','90.00').status_code,400)
        r=self.action('close','90.00','Faltante por aclarar');self.assertEqual(r.status_code,200);self.assertEqual(r.data['difference'],'-10.00')
        self.as_user(self.director);self.assertEqual(self.c.get('/api/v1/cash/summary/').data['with_difference'],1)
        r=self.assign();self.assertEqual(r.status_code,201);self.pk=r.data['id'];self.url=f'/api/v1/cash/shifts/{self.pk}/'
        self.assertEqual(self.action('cancel',reason='Cambio de responsable').status_code,200)
        self.as_user(self.cashier);self.assertEqual(self.action('open','0').status_code,409)
    def test_overlapping_turns_and_foreign_responsible(self):
        r=self.assign();self.assertEqual(r.status_code,201);self.assertEqual(self.assign().status_code,409)
        CashShift.objects.all().delete();self.cashier=self.other
        self.assertEqual(self.assign().status_code,404)
    def test_filtered_summary_and_dates(self):
        self.setup_shift();self.movement();self.as_user(self.director)
        r=self.c.get('/api/v1/cash/summary/',{'date_from':(self.now.date()+timedelta(days=2)).isoformat()});self.assertEqual(r.data['totals'],{})
        self.assertEqual(self.c.get('/api/v1/cash/summary/',{'date_from':'2026-02-01','date_to':'2026-01-01'}).status_code,400)
        self.assertEqual(self.c.get('/api/v1/cash/shifts/',{'service':self.foreign.pk}).status_code,404)

from django.test import TransactionTestCase
from django.db import close_old_connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class CashConcurrencyTests(TransactionTestCase):
    def test_two_simultaneous_withdrawals_cannot_overdraw(self):
        # Use the same real PostgreSQL transaction/locking path as production.
        self.as_user=CashTests.as_user.__get__(self)
        CashTests.setUp(self)
        response=CashTests.assign(self);self.assertEqual(response.status_code,201,response.data)
        pk=response.data['id'];url=f'/api/v1/cash/shifts/{pk}/'
        self.c.force_authenticate(self.cashier)
        r=self.c.post(url,{'action':'open','amount':'100.00','revision':0},format='json');self.assertEqual(r.status_code,200,r.data)
        barrier=Barrier(2);user_id=self.cashier.pk
        def withdraw():
            close_old_connections()
            try:
                c=APIClient();c.force_authenticate(get_user_model().objects.get(pk=user_id));barrier.wait(timeout=10)
                return c.post(url+'movements/',{'kind':'withdrawal','amount':'80.00','concept':'Entrega de prueba','revision':1,'client_key':str(uuid.uuid4())},format='json').status_code
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:withdraw(),range(2)))
        self.assertEqual(sorted(results),[201,409]);self.assertEqual(CashMovement.objects.count(),1)
        self.assertEqual(self.c.get(url).data['balance'],'20.00')
