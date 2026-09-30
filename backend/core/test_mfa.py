from datetime import timedelta
from unittest.mock import patch
import pyotp
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import MFADevice,SecurityEvent


@override_settings(MFA_REQUIRE_PRIVILEGED=True,MFA_ENCRYPTION_KEY=Fernet.generate_key().decode())
class MFATests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user=get_user_model().objects.create_user('privileged',password='synthetic-only',is_staff=True)
        self.client=APIClient()
        self.now=timezone.now()
        self.clock=patch('core.mfa.timezone.now',return_value=self.now)
        self.clock.start();self.addCleanup(self.clock.stop)
        self.signin(self.client)

    def signin(self,client):
        response=client.post('/api/v1/session/',{'username':self.user.username,'password':'synthetic-only'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        return response

    def post(self,action,client=None,**data):
        return (client or self.client).post('/api/v1/mfa/',{'action':action,**data},format='json')

    def enroll(self):
        response=self.post('begin',password='synthetic-only')
        self.assertEqual(response.status_code,200,response.data)
        secret=response.data['setup_secret']
        response=self.post('confirm',code=pyotp.TOTP(secret).at(self.now))
        self.assertEqual(response.status_code,200,response.data)
        return secret,response.data['recovery_codes']

    def test_required_enrollment_blocks_all_business_endpoints(self):
        self.assertFalse(self.client.get('/api/v1/session/').data['authenticated'])
        for url in ['/api/v1/services/','/api/v1/answers/','/api/v1/dashboard/','/api/v1/administration/setup/','/api/v1/schema/']:
            self.assertEqual(self.client.get(url).status_code,403,url)
        self.enroll()
        self.assertEqual(self.client.get('/api/v1/services/').status_code,200)
        self.assertTrue(self.client.get('/api/v1/session/').data['authenticated'])

    def test_encrypted_secret_one_time_codes_and_no_secret_in_session_or_events(self):
        secret,codes=self.enroll();device=MFADevice.objects.get(user=self.user)
        self.assertNotEqual(device.secret,secret)
        self.assertEqual(Fernet(__import__('django.conf',fromlist=['settings']).settings.MFA_ENCRYPTION_KEY).decrypt(device.secret.encode()).decode(),secret)
        self.assertEqual(len(codes),8)
        self.assertNotIn(codes[0].replace('-',''),str(device.recovery_hashes))
        self.assertNotIn(secret,str(dict(self.client.session)))
        self.assertNotIn(secret,str(list(SecurityEvent.objects.values())))
        response=self.client.get('/api/v1/mfa/')
        self.assertNotIn('setup_secret',response.data);self.assertNotIn('recovery_codes',response.data)
        self.assertEqual(response['Cache-Control'],'no-store')

    def test_totp_replay_and_new_session(self):
        secret,_=self.enroll()
        second=APIClient();self.signin(second)
        self.assertEqual(self.post('verify',client=second,code=pyotp.TOTP(secret).at(self.now)).status_code,400)
        with patch('core.mfa.timezone.now',return_value=self.now+timedelta(seconds=30)):
            self.assertEqual(self.post('verify',client=second,code=pyotp.TOTP(secret).at(self.now+timedelta(seconds=30))).status_code,200)
            self.assertEqual(second.get('/api/v1/services/').status_code,200)

    def test_recovery_consumed_and_other_session_revoked(self):
        _,codes=self.enroll();second=APIClient();self.signin(second)
        self.assertEqual(self.post('verify',client=second,code=codes[0]).status_code,200)
        self.assertEqual(self.client.get('/api/v1/services/').status_code,403)
        self.assertEqual(self.post('verify',code=codes[0]).status_code,400)
        self.assertEqual(MFADevice.objects.get(user=self.user).recovery_hashes.__len__(),7)

    def test_account_lock_persists_across_sessions(self):
        self.enroll()
        for _ in range(5):self.assertEqual(self.post('verify',code='invalid').status_code,400)
        second=APIClient();self.signin(second)
        self.assertEqual(self.post('verify',client=second,code='invalid').status_code,429)
        self.assertEqual(SecurityEvent.objects.filter(action='mfa.failed').count(),5)
        with patch('core.mfa.timezone.now',return_value=self.now+timedelta(minutes=6)):
            self.assertEqual(self.post('verify',client=second,code='invalid').status_code,400)

    def test_pending_expiration_and_session_binding(self):
        response=self.post('begin',password='synthetic-only');secret=response.data['setup_secret']
        second=APIClient();self.signin(second)
        self.assertEqual(self.post('confirm',client=second,code=pyotp.TOTP(secret).at(self.now)).status_code,400)
        with patch('core.mfa.timezone.now',return_value=self.now+timedelta(minutes=11)):
            self.assertEqual(self.post('confirm',code=pyotp.TOTP(secret).at(self.now)).status_code,403)
        self.assertFalse(MFADevice.objects.get().enabled)

    def test_missing_key_fails_closed(self):
        with override_settings(MFA_ENCRYPTION_KEY=''):
            self.assertEqual(self.post('begin',password='synthetic-only').status_code,403)
            self.assertEqual(self.client.get('/api/v1/services/').status_code,403)

    def test_replacement_requires_password_and_factor_preserves_until_confirmation(self):
        secret,codes=self.enroll()
        self.assertEqual(self.post('begin',password='synthetic-only',code='bad').status_code,400)
        response=self.post('begin',password='synthetic-only',code=codes[0])
        self.assertEqual(response.status_code,200,response.data)
        device=MFADevice.objects.get()
        self.assertTrue(device.enabled)
        self.assertNotEqual(device.secret,device.pending_secret)
        replacement=response.data['setup_secret']
        self.assertNotEqual(secret,replacement)
        self.assertEqual(self.post('confirm',code=pyotp.TOTP(replacement).at(self.now)).status_code,200)
        self.assertEqual(self.post('verify',code=codes[1]).status_code,400)

    def test_new_codes_invalidate_old_and_revoke_other_sessions(self):
        _,codes=self.enroll()
        response=self.post('codes',password='synthetic-only',code=codes[0])
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.data['recovery_codes']),8)
        self.assertEqual(self.post('verify',code=codes[1]).status_code,400)

    def test_optional_account_and_later_privilege_enforcement(self):
        self.user.is_staff=False;self.user.save()
        self.assertTrue(self.client.get('/api/v1/session/').data['authenticated'])
        self.assertEqual(self.client.get('/api/v1/services/').status_code,200)
        self.user.is_staff=True;self.user.save()
        self.assertEqual(self.client.get('/api/v1/services/').status_code,403)
        self.enroll()
        self.user.is_staff=False;self.user.save()
        second=APIClient();self.signin(second)
        self.assertEqual(second.get('/api/v1/services/').status_code,403)

    def test_csrf_and_verification_expiry(self):
        self.enroll()
        with patch('core.mfa.timezone.now',return_value=self.now+timedelta(hours=13)):
            self.assertEqual(self.client.get('/api/v1/services/').status_code,403)
        c=APIClient(enforce_csrf_checks=True)
        c.force_login(self.user)
        self.assertEqual(c.post('/api/v1/mfa/',{'action':'begin','password':'synthetic-only'},format='json').status_code,403)

    def test_deploy_checks_reject_missing_key_or_disabled_enforcement(self):
        from .checks import mfa_configuration
        with override_settings(MFA_ENCRYPTION_KEY='',MFA_REQUIRE_PRIVILEGED=False):
            self.assertEqual({e.id for e in mfa_configuration(None)},{'core.E001','core.E002'})
        self.assertEqual(mfa_configuration(None),[])

    def test_relogin_does_not_inherit_verified_stamp(self):
        self.enroll();self.signin(self.client)
        self.assertFalse(self.client.get('/api/v1/session/').data['authenticated'])
        self.assertEqual(self.client.get('/api/v1/services/').status_code,403)

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections,connections
from django.test import TransactionTestCase

@override_settings(MFA_REQUIRE_PRIVILEGED=True,MFA_ENCRYPTION_KEY=Fernet.generate_key().decode())
class MFAConcurrencyTests(TransactionTestCase):
    def test_concurrent_recovery_code_can_only_be_used_once(self):
        cache.clear()
        user=get_user_model().objects.create_user('concurrent-mfa',password='synthetic-only',is_staff=True)
        def signin():
            client=APIClient()
            response=client.post('/api/v1/session/',{'username':user.username,'password':'synthetic-only'},format='json')
            self.assertEqual(response.status_code,200)
            return client
        initial=signin()
        begin=initial.post('/api/v1/mfa/',{'action':'begin','password':'synthetic-only'},format='json')
        confirmed=initial.post('/api/v1/mfa/',{'action':'confirm','code':pyotp.TOTP(begin.data['setup_secret']).now()},format='json')
        code=confirmed.data['recovery_codes'][0]
        clients=[signin(),signin()];barrier=Barrier(2)
        def attempt(client):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return client.post('/api/v1/mfa/',{'action':'verify','code':code},format='json').status_code
            finally:connections.close_all()
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                results=list(executor.map(attempt,clients))
            self.assertEqual(sorted(results),[200,400])
            self.assertEqual(len(MFADevice.objects.get(user=user).recovery_hashes),7)
        finally:cache.clear()

@override_settings(MFA_REQUIRE_PRIVILEGED=True,MFA_ENCRYPTION_KEY=Fernet.generate_key().decode(),MFA_DEMO_PASSWORD_ONLY=True,PATIENT_PORTAL_ENABLED=False)
class DemoPasswordOnlyTests(TestCase):
    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
        self.user=get_user_model().objects.create_user('demo-admin',password='synthetic-only',is_staff=True,is_superuser=True)
        self.client=APIClient()

    def login(self):
        return self.client.post('/api/v1/session/',{'username':self.user.username,'password':'synthetic-only'},format='json')

    def test_password_still_required_and_privileged_user_can_work(self):
        self.assertTrue(self.client.get('/api/v1/session/').data['password_only_demo'])
        self.assertEqual(self.client.get('/api/v1/schools/').status_code,403)
        self.assertEqual(self.client.post('/api/v1/session/',{'username':self.user.username,'password':'incorrect'},format='json').status_code,400)
        response=self.login()
        self.assertTrue(response.data['authenticated']);self.assertFalse(response.data['mfa_required'])
        self.assertEqual(self.client.get('/api/v1/schools/').status_code,200)
        with override_settings(MFA_DEMO_PASSWORD_ONLY=False):
            self.assertFalse(self.client.get('/api/v1/session/').data['authenticated'])
            self.assertEqual(self.client.get('/api/v1/schools/').status_code,403)

    def test_enrolled_device_retained_and_same_session_blocked_when_reenabled(self):
        from .mfa import cipher
        device=MFADevice.objects.create(user=self.user,enabled=True,generation=3,secret=cipher().encrypt(pyotp.random_base32().encode()).decode())
        before=MFADevice.objects.filter(pk=device.pk).values().get()
        self.assertTrue(self.login().data['authenticated'])
        self.assertEqual(self.client.get('/api/v1/services/').status_code,200)
        self.assertEqual(MFADevice.objects.filter(pk=device.pk).values().get(),before)
        with override_settings(MFA_DEMO_PASSWORD_ONLY=False):
            self.assertTrue(self.client.get('/api/v1/session/').data['mfa_required'])
            self.assertEqual(self.client.get('/api/v1/services/').status_code,403)
        self.assertNotIn('mfa_verified_at',self.client.session)

    @override_settings(PATIENT_PORTAL_ENABLED=True)
    def test_patient_intake_forces_mfa_even_if_demo_flag_was_left_on(self):
        response=self.login()
        self.assertFalse(response.data['password_only_demo'])
        self.assertFalse(response.data['authenticated'])
        self.assertTrue(response.data['mfa_required'])
        self.assertEqual(self.client.get('/api/v1/services/').status_code,403)
