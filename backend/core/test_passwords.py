from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase,override_settings
from rest_framework.test import APIClient
from .models import SecurityEvent

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class PasswordChangeTests(TestCase):
    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
        self.user=get_user_model().objects.create_user('colaborador',password='initial-short')
        self.other=get_user_model().objects.create_user('other',password='OtherOriginal123!')
        self.client=APIClient(enforce_csrf_checks=True);self.client.login(username='colaborador',password='initial-short')
        self.token=self.client.get('/api/v1/session/').data['csrf']
        self.data={'current_password':'initial-short','new_password':'NuevaClavePrivada2026!','confirm_password':'NuevaClavePrivada2026!'}
    def post(self,data=None):return self.client.post('/api/v1/security/password/',data or self.data,format='json',HTTP_X_CSRFTOKEN=self.token)
    def test_change_keeps_current_session_invalidates_other_sessions_and_old_password(self):
        second=APIClient();second.login(username='colaborador',password='initial-short')
        before=get_user_model().objects.filter(pk=self.other.pk).values().get()
        self.assertEqual(self.post().status_code,200)
        self.assertTrue(self.client.get('/api/v1/session/').data['authenticated'])
        self.assertFalse(second.get('/api/v1/session/').data['authenticated'])
        c=APIClient();self.assertFalse(c.login(username='colaborador',password='initial-short'))
        self.assertTrue(c.login(username='colaborador',password=self.data['new_password']))
        self.assertEqual(SecurityEvent.objects.filter(user=self.user,action='password.changed').count(),1)
        self.assertEqual(get_user_model().objects.filter(pk=self.other.pk).values().get(),before)
    def test_current_password_confirmation_strength_and_no_foreign_target(self):
        for extra in [{'current_password':'wrong'},{'confirm_password':'different'},{'new_password':'short','confirm_password':'short'},{'user_id':self.other.pk}]:
            self.assertEqual(self.post({**self.data,**extra}).status_code,400)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password('initial-short'))
    def test_csrf_and_authentication_required(self):
        self.assertEqual(self.client.post('/api/v1/security/password/',self.data,format='json').status_code,403)
        self.assertEqual(APIClient().post('/api/v1/security/password/',self.data,format='json').status_code,403)
    def test_failed_attempts_are_throttled(self):
        for _ in range(5):self.assertEqual(self.post({**self.data,'current_password':'wrong'}).status_code,400)
        self.assertEqual(self.post().status_code,429)
