from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase,override_settings
from rest_framework.test import APIClient
from .person_names import person_name
from .models import PatientProfile

@override_settings(PATIENT_PORTAL_ENABLED=True,MFA_REQUIRE_PRIVILEGED=False)
class PersonNameTests(TestCase):
    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
    def test_compound_surname_and_legacy_name_preserve_stored_values(self):
        User=get_user_model()
        user=User(username='personal',first_name='Flor Georgina',last_name='San Roman Campos')
        self.assertEqual(person_name(user),'San Roman Campos Flor Georgina')
        self.assertEqual(user.first_name,'Flor Georgina')
        self.assertEqual(person_name(User(username='legacy',first_name='Nombre completo sin separar')),'Nombre completo sin separar')
        self.assertEqual(person_name(User(username='sin_nombre')),'sin_nombre')
    def test_portal_separate_names_and_legacy_input(self):
        for extra,expected in [({'first_name':'Ana María','last_name':'Pérez López'},'Pérez López Ana María'),({'name':'Nombre antiguo completo'},'Nombre antiguo completo')]:
            c=APIClient(enforce_csrf_checks=True);token=c.get('/api/v1/public/session/').data['csrf']
            response=c.post('/api/v1/public/register/',{**extra,'email':str(PatientProfile.objects.count())+'@example.org','phone':'9991234567','password':'VeryPrivatePass2026!'},format='json',HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code,201,response.data)
            self.assertEqual(response.data['name'],expected)
            self.assertEqual(c.get('/api/v1/public/session/').data['name'],expected)
