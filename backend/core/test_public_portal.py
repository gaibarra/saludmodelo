import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Institution,Campus,Site,Service,RoleAssignment,PatientProfile,AppointmentRequest

@override_settings(PATIENT_PORTAL_ENABLED=True)
class PatientPortalTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.institution=Institution.objects.create(name='Institución sintética')
        site=Site.objects.create(campus=Campus.objects.create(institution=self.institution,name='Campus ficticio'),name='Sede ficticia')
        self.dental=Service.objects.create(site=site,name='Odontología ficticia',confirmed=True,public_slug='odontologia')
        self.psych=Service.objects.create(site=site,name='Psicología ficticia',confirmed=True,public_slug='psicologia')
        self.staff=User.objects.create_user('staff-dental',password='TestPassword123!')
        self.other_staff=User.objects.create_user('staff-psych',password='TestPassword123!')
        for user,service in [(self.staff,self.dental),(self.other_staff,self.psych)]:
            RoleAssignment.objects.create(user=user,service=service,role='manager',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=30),approved_by=self.staff if user==self.other_staff else self.other_staff)
        self.client=APIClient(enforce_csrf_checks=True)

    def register(self,client,email):
        session=client.get('/api/v1/public/session/')
        token=session.data['csrf']
        result=client.post('/api/v1/public/register/',{'name':'Persona de prueba','email':email,'phone':'999 123 4567','password':'TestPassword123!'},format='json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code,201,result.data)
        return result

    def request(self,client,service='odontologia',key=None):
        token=client.get('/api/v1/public/session/').data['csrf']
        return client.post('/api/v1/public/appointments/',{'service':service,'site_preference':'cholul','preferred_day':str(timezone.localdate()+timedelta(days=3)),'client_key':str(key or uuid.uuid4())},format='json',HTTP_X_CSRFTOKEN=token)

    def test_catalog_and_account_need_csrf_and_keep_patient_out_of_staff(self):
        catalog=self.client.get('/api/v1/public/services/').data
        self.assertEqual(len(catalog['services']),6)
        self.assertTrue(catalog['appointments_enabled'])
        payload={'name':'Persona de prueba','email':'patient@example.org','phone':'999 123 4567','password':'TestPassword123!'}
        self.assertEqual(self.client.post('/api/v1/public/register/',payload,format='json').status_code,403)
        self.register(self.client,'PATIENT@example.org')
        self.assertTrue(self.client.get('/api/v1/public/session/').data['authenticated'])
        self.assertEqual(PatientProfile.objects.get().email_normalized,'patient@example.org')
        self.assertEqual(self.client.get('/api/v1/services/').data['results'],[])
        self.assertEqual(self.client.get('/api/v1/staff/appointments/').data['results'],[])
        self.assertEqual(self.client.get('/api/v1/public/appointments/').data['results'],[])

    def test_patient_request_confirmation_is_service_scoped_and_visible_in_account(self):
        self.register(self.client,'first@example.org')
        key=uuid.uuid4()
        created=self.request(self.client,key=key)
        self.assertEqual(created.status_code,201,created.data)
        self.assertEqual(self.request(self.client,key=key).status_code,200)
        self.assertEqual(self.request(self.client).status_code,400)
        second=APIClient(enforce_csrf_checks=True);self.register(second,'second@example.org')
        self.assertEqual(second.get('/api/v1/public/appointments/').data['results'],[])
        self.assertEqual(second.post(f"/api/v1/public/appointments/{created.data['id']}/withdraw/",{'version':1},format='json',HTTP_X_CSRFTOKEN=second.get('/api/v1/public/session/').data['csrf']).status_code,404)
        staff=APIClient();staff.force_authenticate(self.staff)
        other=APIClient();other.force_authenticate(self.other_staff)
        self.assertEqual(len(staff.get('/api/v1/staff/appointments/').data['results']),1)
        self.assertEqual(other.get('/api/v1/staff/appointments/').data['results'],[])
        url=f"/api/v1/staff/appointments/{created.data['id']}/decision/"
        decision={'version':1,'action':'confirm','confirmed_start':(timezone.now()+timedelta(days=4)).isoformat(),'confirmed_site':'cholul'}
        self.assertEqual(other.post(url,decision,format='json').status_code,403)
        self.assertEqual(staff.post(url,{**decision,'confirmed_start':None},format='json').status_code,400)
        approved=staff.post(url,decision,format='json')
        self.assertEqual(approved.status_code,200,approved.data)
        self.assertEqual(approved.data['status'],'confirmed')
        self.assertEqual(staff.post(url,decision,format='json').status_code,409)
        self.assertEqual(self.client.get('/api/v1/public/appointments/').data['results'][0]['status'],'confirmed')
        self.assertEqual(AppointmentRequest.objects.count(),1)

    def test_six_tabs_accept_requests_but_only_mapped_staff_can_confirm(self):
        self.register(self.client,'third@example.org')
        self.assertEqual(self.request(self.client,'nutricion').status_code,400)
        self.assertFalse(next(s for s in self.client.get('/api/v1/public/services/').data['services'] if s['slug']=='nutricion')['request_enabled'])
        staff=APIClient();staff.force_authenticate(self.staff)
        self.assertEqual(staff.get('/api/v1/staff/appointments/').data['results'],[])
        self.assertEqual(staff.get('/api/v1/staff/appointments/?service=nutricion').status_code,403)

    @override_settings(PATIENT_PORTAL_ENABLED=False)
    def test_default_off_prevents_real_intake(self):
        self.assertFalse(self.client.get('/api/v1/public/services/').data['appointments_enabled'])
        self.assertEqual(self.client.post('/api/v1/public/register/',{'name':'Prueba','email':'off@example.org','phone':'9991234567','password':'TestPassword123!'},format='json').status_code,403)
        self.assertEqual(PatientProfile.objects.count(),0)
