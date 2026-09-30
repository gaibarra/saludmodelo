import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
import pyotp
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connections
from django.test import TransactionTestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Institution,InstitutionMember,InstitutionMandate,MFADevice,ExceptionalMFARecovery,GovernanceEvent
from .mfa import cipher

@override_settings(EXCEPTIONAL_MFA_RECOVERY_ENABLED=True,MFA_REQUIRE_PRIVILEGED=True,MFA_ENCRYPTION_KEY=Fernet.generate_key().decode(),PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ExceptionalMFATests(TransactionTestCase):
    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
        self.now=timezone.now();self.clock=patch('django.utils.timezone.now',return_value=self.now);self.clock.start();self.addCleanup(self.clock.stop)
        self.institution=Institution.objects.create(name='Recovery institution')
        self.requester=get_user_model().objects.create_user('requester',password='synthetic-only')
        self.reviewer=get_user_model().objects.create_user('reviewer',password='synthetic-only')
        self.target=get_user_model().objects.create_user('target',password='synthetic-only')
        for user in [self.requester,self.reviewer,self.target]:
            InstitutionMember.objects.create(user=user,institution=self.institution)
            MFADevice.objects.create(user=user,enabled=True,generation=1,secret=cipher().encrypt(pyotp.random_base32().encode()).decode(),recovery_hashes=[hashlib.sha256(b'old-code').hexdigest()])
        for user in [self.requester,self.reviewer]:
            InstitutionMandate.objects.create(user=user,institution=self.institution,approved_by=self.target,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=10),rationale='Synthetic mandate')
        self.a=self.client_for(self.requester,True);self.b=self.client_for(self.reviewer,True);self.c=self.client_for(self.target)
        self.payload={'institution':self.institution.pk,'username':'target','rationale':'Lost authenticator and recovery codes','verification_reference':'IDENT-SYNTH-01','client_key':str(uuid.uuid4())}
    def client_for(self,user,verified=False):
        client=APIClient();response=client.post('/api/v1/session/',{'username':user.username,'password':'synthetic-only'},format='json');self.assertEqual(response.status_code,200)
        if verified:
            session=client.session;session['mfa_generation']=MFADevice.objects.get(user=user).generation;session['mfa_verified_at']=self.now.timestamp();session.save()
        return client
    def propose(self,client=None,**extra):
        return (client or self.a).post('/api/v1/security/recoveries/',{**self.payload,**extra},format='json')
    def review(self,pk,decision='approve',client=None):
        return (client or self.b).post(f'/api/v1/security/recoveries/{pk}/review/',{'decision':decision,'rationale':'Independent identity check','verification_reference':'IDENT-SYNTH-02'},format='json')
    def approve(self):
        proposal=self.propose();self.assertEqual(proposal.status_code,201,proposal.data)
        response=self.review(proposal.data['id']);self.assertEqual(response.status_code,200,response.data)
        return response.data
    def redeem(self,token,client=None,password='synthetic-only'):
        return (client or self.c).post('/api/v1/mfa/',{'action':'recover','password':password,'code':token},format='json')
    def test_full_recovery_requires_new_enrollment_and_revokes_old_sessions(self):
        old=self.client_for(self.target,True)
        data=self.approve();token=data['recovery_token']
        self.assertEqual(old.get('/api/v1/services/').status_code,403)
        self.assertEqual(self.c.post('/api/v1/mfa/',{'action':'verify','code':'old-code'},format='json').status_code,403)
        value=ExceptionalMFARecovery.objects.get();self.assertNotIn(token,str(value.__dict__))
        response=self.redeem(token);self.assertEqual(response.status_code,200,response.data)
        self.assertFalse(response.data['authenticated']);self.assertTrue(response.data['recovery_enrollment_allowed'])
        self.assertEqual(self.c.get('/api/v1/services/').status_code,403)
        outsider=self.client_for(self.target)
        self.assertEqual(outsider.post('/api/v1/mfa/',{'action':'begin','password':'synthetic-only'},format='json').status_code,403)
        self.assertEqual(self.redeem(token,outsider).status_code,400)
        started=self.c.post('/api/v1/mfa/',{'action':'begin','password':'synthetic-only'},format='json');self.assertEqual(started.status_code,200,started.data)
        finished=self.c.post('/api/v1/mfa/',{'action':'confirm','code':pyotp.TOTP(started.data['setup_secret']).at(self.now)},format='json')
        self.assertEqual(finished.status_code,200,finished.data);self.assertTrue(finished.data['authenticated'])
        self.assertFalse(finished.data['recovery_pending']);self.assertEqual(len(finished.data['recovery_codes']),8)
        value.refresh_from_db();self.assertEqual(value.state,'completed');self.assertIsNotNone(value.completed_at)
        self.assertEqual(old.get('/api/v1/services/').status_code,403)
        self.assertEqual(self.c.get('/api/v1/services/').status_code,200)
    def test_independent_decision_and_self_request_forbidden(self):
        self.assertEqual(self.propose(username='requester').status_code,400)
        pk=self.propose().data['id'];self.assertEqual(self.review(pk,client=self.a).status_code,403)
        self.assertEqual(self.review(pk,client=self.c).status_code,403)
        self.assertEqual(MFADevice.objects.get(user=self.target).generation,1)
    def test_ineligible_staff_inactive_and_multi_institution_accounts(self):
        for field in ['is_staff','is_superuser']:
            get_user_model().objects.filter(pk=self.target.pk).update(**{field:True})
            self.assertEqual(self.propose().status_code,403)
            get_user_model().objects.filter(pk=self.target.pk).update(**{field:False})
        get_user_model().objects.filter(pk=self.target.pk).update(is_active=False)
        self.assertEqual(self.propose().status_code,403)
        get_user_model().objects.filter(pk=self.target.pk).update(is_active=True)
        from .models import Campus,Site,Service,RoleAssignment
        campus=Campus.objects.create(institution=self.institution,name='Technical campus')
        site=Site.objects.create(campus=campus,name='Technical site')
        service=Service.objects.create(site=site,name='Technical service')
        role=RoleAssignment.objects.create(user=self.target,service=service,role='technical',starts=timezone.localdate(),ends=timezone.localdate(),approved_by=self.requester)
        self.assertEqual(self.propose().status_code,403)
        role.delete()
        InstitutionMember.objects.create(user=self.target,institution=Institution.objects.create(name='Other institution'))
        self.assertEqual(self.propose().status_code,403)
    def test_expired_pending_and_expired_token(self):
        pk=self.propose().data['id'];ExceptionalMFARecovery.objects.filter(pk=pk).update(expires_at=self.now-timedelta(seconds=1))
        self.assertEqual(self.review(pk).status_code,400)
        self.assertEqual(self.review(pk,'reject').status_code,200)
        self.payload['client_key']=str(uuid.uuid4());data=self.approve()
        ExceptionalMFARecovery.objects.filter(pk=data['id']).update(expires_at=self.now-timedelta(seconds=1))
        self.assertEqual(self.redeem(data['recovery_token']).status_code,400)
    def test_revoked_authority_before_approval_and_redemption(self):
        pk=self.propose().data['id'];mandate=InstitutionMandate.objects.get(user=self.requester);mandate.ends=timezone.localdate()-timedelta(days=1);mandate.save()
        self.assertEqual(self.review(pk).status_code,403)
        self.assertEqual(self.review(pk,'reject').status_code,200)
        mandate.ends=timezone.localdate()+timedelta(days=10);mandate.save();self.payload['client_key']=str(uuid.uuid4());data=self.approve()
        InstitutionMandate.objects.filter(user=self.reviewer).delete()
        self.assertEqual(self.redeem(data['recovery_token']).status_code,403)
        self.assertEqual(ExceptionalMFARecovery.objects.get(pk=data['id']).state,'approved')
    def test_stale_target_generation_and_recent_mfa(self):
        session=self.a.session;session['mfa_verified_at']=(self.now-timedelta(minutes=11)).timestamp();session.save()
        self.assertEqual(self.propose().status_code,403)
        session=self.a.session;session['mfa_verified_at']=self.now.timestamp();session.save()
        pk=self.propose().data['id'];MFADevice.objects.filter(user=self.target).update(generation=2)
        self.assertEqual(self.review(pk).status_code,409)
    def test_feature_disabled_has_no_effect(self):
        with override_settings(EXCEPTIONAL_MFA_RECOVERY_ENABLED=False):
            self.assertEqual(self.propose().status_code,403)
            self.assertEqual(self.redeem('1.invalid').status_code,403)
        self.assertEqual(ExceptionalMFARecovery.objects.count(),0)
    def test_bad_tokens_are_rate_limited_and_password_required(self):
        data=self.approve()
        self.assertEqual(self.redeem(data['recovery_token'],password='wrong').status_code,400)
        for i in range(4):self.assertEqual(self.redeem('1.bad').status_code,400)
        self.assertEqual(self.redeem(data['recovery_token']).status_code,429)
        self.assertEqual(ExceptionalMFARecovery.objects.get().state,'approved')
    def test_rejection_and_revocation(self):
        pk=self.propose().data['id'];self.assertEqual(self.review(pk,'reject').status_code,200)
        self.assertEqual(MFADevice.objects.get(user=self.target).generation,1)
        self.payload['client_key']=str(uuid.uuid4());data=self.approve()
        self.assertEqual(self.review(data['id'],'revoke',client=self.a).status_code,200)
        self.assertEqual(self.redeem(data['recovery_token']).status_code,400)
        self.assertTrue(MFADevice.objects.get(user=self.target).recovery_required)
        self.assertTrue(GovernanceEvent.objects.filter(action='mfa.recovery_revoked').exists())
    def test_idempotency_no_secret_in_list_and_scope(self):
        first=self.propose();second=self.propose();self.assertEqual(first.data['id'],second.data['id'])
        self.assertEqual(self.propose(rationale='Changed reason').status_code,409)
        result=self.review(first.data['id']);token=result.data['recovery_token']
        listed=self.a.get('/api/v1/security/recoveries/');self.assertEqual(listed.status_code,200)
        self.assertNotIn(token,str(listed.data));self.assertNotIn('token_hash',str(listed.data))
        self.assertEqual(self.review(first.data['id']).status_code,409)
        InstitutionMandate.objects.filter(user=self.requester).delete()
        self.assertEqual(self.a.get('/api/v1/security/recoveries/').data['results'],[])
    def test_concurrent_redemption_is_single_use(self):
        data=self.approve();other=self.client_for(self.target)
        def send(client):
            try:return self.redeem(data['recovery_token'],client).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(send,[self.c,other]))
        self.assertEqual(sorted(codes),[200,400])
    def test_mfa_change_of_requester_prevents_approval(self):
        pk=self.propose().data['id'];MFADevice.objects.filter(user=self.requester).update(generation=2)
        self.assertEqual(self.review(pk).status_code,403)

    def test_revocation_after_redemption_blocks_pending_enrollment(self):
        data=self.approve();self.assertEqual(self.redeem(data['recovery_token']).status_code,200)
        self.assertEqual(self.review(data['id'],'revoke',client=self.a).status_code,200)
        self.assertEqual(self.c.post('/api/v1/mfa/',{'action':'begin','password':'synthetic-only'},format='json').status_code,403)
        self.assertEqual(self.c.get('/api/v1/services/').status_code,403)
    def test_other_account_and_new_institution_cannot_redeem(self):
        data=self.approve()
        self.assertEqual(self.redeem(data['recovery_token'],client=self.a).status_code,400)
        InstitutionMember.objects.create(user=self.target,institution=Institution.objects.create(name='New institution'))
        self.assertEqual(self.redeem(data['recovery_token']).status_code,403)
    def test_password_only_authority_session_cannot_propose(self):
        partial=self.client_for(self.requester)
        self.assertEqual(self.propose(client=partial).status_code,403)
        self.assertEqual(ExceptionalMFARecovery.objects.count(),0)
    def test_concurrent_reviews_generate_one_grant(self):
        pk=self.propose().data['id']
        other=self.client_for(self.reviewer,True)
        def send(client):
            try:return self.review(pk,client=client).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(send,[self.b,other]))
        self.assertEqual(sorted(codes),[200,409]);self.assertEqual(MFADevice.objects.get(user=self.target).generation,2)
    def test_history_pagination_and_revoked_scope(self):
        for i in range(52):
            self.assertEqual(self.propose(client_key=str(uuid.uuid4())).status_code,201)
        first=self.a.get('/api/v1/security/recoveries/');self.assertEqual(len(first.data['results']),50)
        second=self.a.get('/api/v1/security/recoveries/',{'before':first.data['next_before']});self.assertEqual(len(second.data['results']),2)
        InstitutionMandate.objects.filter(user=self.requester).delete()
        self.assertEqual(self.a.get('/api/v1/security/recoveries/',{'before':first.data['next_before']}).data['results'],[])

    def test_authority_revoked_during_enrollment_prevents_completion(self):
        data=self.approve();self.assertEqual(self.redeem(data['recovery_token']).status_code,200)
        started=self.c.post('/api/v1/mfa/',{'action':'begin','password':'synthetic-only'},format='json')
        self.assertEqual(started.status_code,200)
        InstitutionMandate.objects.filter(user=self.reviewer).delete()
        finished=self.c.post('/api/v1/mfa/',{'action':'confirm','code':pyotp.TOTP(started.data['setup_secret']).at(self.now)},format='json')
        self.assertEqual(finished.status_code,403)
        self.assertEqual(ExceptionalMFARecovery.objects.get().state,'consumed')
        self.assertEqual(self.c.get('/api/v1/services/').status_code,403)
