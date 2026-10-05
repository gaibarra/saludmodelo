from datetime import timedelta
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Institution,School,SchoolMember,InstitutionMember,SchoolMandate,SchoolAcademicGrant,GovernanceEvent,AcademicStudent

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class SchoolAccountTests(TestCase):
    def setUp(self):
        U=get_user_model();self.inst=Institution.objects.create(name='Prueba')
        self.school=School.objects.create(institution=self.inst,code='salud',name='Salud')
        self.other=School.objects.create(institution=self.inst,code='odontologia',name='Odontología')
        self.actor=U.objects.create_user('director');self.approver=U.objects.create_user('aprobador')
        self.user=U.objects.create_user('colaborador',first_name='Ana',last_name='Prueba',email='ana@example.invalid')
        SchoolMember.objects.create(school=self.school,user=self.user)
        InstitutionMember.objects.create(institution=self.inst,user=self.user)
        self.today=timezone.localdate()
        SchoolMandate.objects.create(school=self.school,user=self.actor,approved_by=self.approver,starts=self.today-timedelta(days=1),ends=self.today+timedelta(days=5),rationale='Prueba')
        self.client=APIClient();self.client.force_authenticate(self.actor)
        self.base=f'/api/v1/schools/{self.school.pk}/accounts/'
        self.url=self.base+f'{self.user.pk}/'
    def value(self):
        response=self.client.get(self.url);self.assertEqual(response.status_code,200);return response.data
    def edit(self,**extra):
        v=self.value();return {k:v[k] for k in ('username','first_name','last_name','email','version')}|{'rationale':'Corrección verificada'}|extra
    def test_search_filters_and_no_passwords(self):
        for query in ['Ana','Ana Prueba','colaborador','ana@example.invalid']:
            r=self.client.get(self.base,{'q':query});self.assertEqual(r.status_code,200);self.assertEqual(r.data['count'],1)
            self.assertNotIn('password',r.data['results'][0])
        self.assertEqual(self.client.get(self.base,{'q':'inexistente'}).data['count'],0)
        self.assertEqual(self.client.get(self.base,{'state':'inactive'}).data['count'],0)
        self.assertEqual(self.client.get(self.base,{'state':'invalid'}).status_code,400)
    def test_edit_conflict_audit_and_no_privilege_changes(self):
        payload=self.edit(first_name='Ana actualizada')
        r=self.client.patch(self.url,payload,format='json');self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(self.client.patch(self.url,payload,format='json').status_code,409)
        self.user.refresh_from_db();self.assertEqual(self.user.first_name,'Ana actualizada');self.assertFalse(self.user.is_staff)
        self.assertTrue(GovernanceEvent.objects.filter(action='school.user.updated',object_id=self.user.pk).exists())
        self.assertEqual(self.client.patch(self.url,self.edit(is_superuser=True),format='json').status_code,400)
    def test_deactivate_preserves_history_membership_and_invalidates_sessions(self):
        student=AcademicStudent.objects.create(institution=self.inst,school=self.school,user=self.user,enrollment='001',program='Prueba')
        session=SessionStore();session['_auth_user_id']=str(self.user.pk);session.save();key=session.session_key
        r=self.client.delete(self.url,{'version':self.value()['version'],'rationale':'Fin de colaboración'},format='json');self.assertEqual(r.status_code,200,r.data)
        self.user.refresh_from_db();self.assertFalse(self.user.is_active)
        self.assertTrue(AcademicStudent.objects.filter(pk=student.pk).exists());self.assertTrue(SchoolMember.objects.filter(user=self.user).exists())
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        self.assertEqual(self.client.get(self.base,{'state':'inactive'}).data['count'],1)
        r=self.client.post(self.url+'reactivate/',{'version':r.data['version'],'rationale':'Retoma colaboración'},format='json');self.assertEqual(r.status_code,200)
        self.assertTrue(r.data['is_active']);self.assertFalse(Session.objects.filter(session_key=key).exists())
    def test_protected_shared_authority_self_and_superuser(self):
        for mode in ['shared','authority','self','superuser']:
            with self.subTest(mode=mode):
                u=get_user_model().objects.create_user('protected-'+mode,is_superuser=mode=='superuser') if mode!='self' else self.actor
                SchoolMember.objects.get_or_create(school=self.school,user=u)
                if mode=='shared':SchoolMember.objects.create(school=self.other,user=u)
                if mode=='authority':SchoolMandate.objects.create(school=self.school,user=u,approved_by=self.approver,starts=self.today,ends=self.today+timedelta(days=1),rationale='Prueba')
                url=self.base+f'{u.pk}/';v=self.client.get(url).data;self.assertFalse(v['can_manage'])
                self.assertEqual(self.client.delete(url,{'version':v['version'],'rationale':'Intento de baja'},format='json').status_code,403)
    def test_other_school_and_readonly_grant_do_not_allow_directory(self):
        SchoolAcademicGrant.objects.create(school=self.other,reader_school=self.school,approved_by=self.approver,starts=self.today,ends=self.today+timedelta(days=1),rationale='Sólo consulta académica')
        self.assertEqual(self.client.get(f'/api/v1/schools/{self.other.pk}/accounts/').status_code,404)
        foreign=get_user_model().objects.create_user('ajeno');SchoolMember.objects.create(school=self.other,user=foreign)
        self.assertEqual(self.client.get(self.base+f'{foreign.pk}/').status_code,404)
        self.assertEqual(self.client.delete(self.base+f'{foreign.pk}/',{'version':'x','rationale':'Intento ajeno'},format='json').status_code,404)
        self.client.force_authenticate(self.user);self.assertEqual(self.client.get(self.base).status_code,404)
    def test_invalid_edit_and_stale_delete(self):
        get_user_model().objects.create_user('ocupado')
        self.assertEqual(self.client.patch(self.url,self.edit(username='ocupado'),format='json').status_code,400)
        self.assertEqual(self.client.patch(self.url,self.edit(email='invalido'),format='json').status_code,400)
        self.assertEqual(self.client.delete(self.url,{'version':'stale','rationale':'Intento obsoleto'},format='json').status_code,409)
        self.assertEqual(self.client.delete(self.url,{'version':self.value()['version'],'rationale':''},format='json').status_code,400)
    def test_create_visible_and_pagination(self):
        r=self.client.post(f'/api/v1/schools/{self.school.pk}/users/',{'institution':self.inst.pk,'username':'nuevo','first_name':'Nuevo','last_name':'Registro','password':'Cuenta-prueba-987!'},format='json')
        self.assertEqual(r.status_code,201,r.data);self.assertEqual(self.client.get(self.base,{'q':'nuevo'}).data['count'],1)
        for i in range(53):
            u=get_user_model().objects.create_user('pagina'+str(i));SchoolMember.objects.create(school=self.school,user=u)
        r=self.client.get(self.base);self.assertTrue(r.data['next']);self.assertEqual(r.data['count'],55)

    def test_name_correction_of_own_director_keeps_access_fields(self):
        SchoolMember.objects.create(school=self.school,user=self.actor)
        url=self.base+f'{self.actor.pk}/'
        original=(self.actor.username,self.actor.password,self.actor.email,self.actor.is_active,self.actor.is_superuser)
        v=self.client.get(url).data;self.assertFalse(v['can_manage']);self.assertTrue(v['can_edit_name'])
        payload={'version':v['version'],'first_name':'Nombre corregido','last_name':'Apellido corregido','rationale':'Corrección de captura'}
        r=self.client.patch(url+'name/',payload,format='json');self.assertEqual(r.status_code,200,r.data)
        self.actor.refresh_from_db();self.assertEqual((self.actor.username,self.actor.password,self.actor.email,self.actor.is_active,self.actor.is_superuser),original)
        self.assertEqual(self.actor.first_name,'Nombre corregido')
        self.assertEqual(self.client.patch(url+'name/',payload,format='json').status_code,409)
        payload['version']=r.data['version'];self.assertEqual(self.client.patch(url+'name/',{**payload,'username':'otro'},format='json').status_code,400)
        self.assertEqual(self.client.delete(url,{'version':payload['version'],'rationale':'No permitido'},format='json').status_code,403)
        self.assertTrue(GovernanceEvent.objects.filter(action='school.user.name_corrected',object_id=str(self.actor.pk),rationale__contains='Nombre corregido').exists())

    def test_institutional_name_correction_and_foreign_school_block(self):
        from .models import InstitutionMandate
        from datetime import timedelta
        admin=get_user_model().objects.create_superuser('name-admin','admin@example.invalid','test-only')
        InstitutionMandate.objects.create(institution=self.inst,user=admin,approved_by=self.approver,starts=self.today,ends=self.today+timedelta(days=5),rationale='Prueba')
        SchoolMember.objects.create(school=self.school,user=self.actor)
        url=self.base+f'{self.actor.pk}/';self.client.force_authenticate(admin)
        v=self.client.get(url).data;self.assertTrue(v['can_edit_name'])
        r=self.client.patch(url+'name/',{'version':v['version'],'first_name':'Dirección','last_name':'Corregida','rationale':'Corrección institucional'},format='json');self.assertEqual(r.status_code,200,r.data)
        self.client.force_authenticate(self.actor)
        SchoolMember.objects.create(school=self.other,user=self.user)
        v=self.client.get(self.url).data;self.assertFalse(v['can_edit_name'])
        self.assertEqual(self.client.patch(self.url+'name/',{'version':v['version'],'first_name':'Ajeno','last_name':'','rationale':'No permitido'},format='json').status_code,403)
        foreign=f'/api/v1/schools/{self.other.pk}/accounts/{self.user.pk}/name/'
        self.assertEqual(self.client.patch(foreign,{'version':v['version'],'first_name':'Ajeno','last_name':'','rationale':'No permitido'},format='json').status_code,404)
