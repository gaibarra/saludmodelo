import io,json
from datetime import timedelta
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Institution,InstitutionMandate,School,Campus,Site,Service,InstitutionalService,SchoolMandate,RoleAssignment

@override_settings(MFA_REQUIRE_PRIVILEGED=False,PATIENT_PORTAL_ENABLED=False)
class InstitutionalServiceTests(TestCase):
    def setUp(self):
        self.institution=Institution.objects.create(name='Universidad sintética')
        U=get_user_model();self.actor=U.objects.create_user('catalog-operator',is_superuser=True)
        self.approver=U.objects.create_user('catalog-approver')
        today=timezone.localdate()
        InstitutionMandate.objects.create(institution=self.institution,user=self.actor,approved_by=self.approver,starts=today-timedelta(days=1),ends=today+timedelta(days=10),rationale='Prueba')
        self.health=School.objects.create(institution=self.institution,code='salud',name='Salud')
        self.dental=School.objects.create(institution=self.institution,code='odontologia',name='Odontología')
        site=Site.objects.create(campus=Campus.objects.create(institution=self.institution,name='Campus sintético'),name='Sede sintética')
        self.legacy=Service.objects.create(site=site,school=self.dental,name='Odontología · DEMO',public_slug='odontologia',confirmed=True)
    def load(self,apply=True):
        out=io.StringIO();call_command('import_institutional_services',institution=self.institution.pk,actor=self.actor.username,apply=apply,stdout=out)
        return json.loads(out.getvalue())
    def test_preview_rollback_idempotency_and_legacy_preservation(self):
        before=list(Service.objects.values());self.load(False)
        self.assertEqual(list(Service.objects.values()),before);self.assertFalse(InstitutionalService.objects.exists())
        result=self.load();self.assertEqual(len(result['created']),6);self.assertEqual(InstitutionalService.objects.count(),6)
        self.assertEqual(Service.objects.filter(pk=self.legacy.pk).values().get(),before[0])
        self.assertFalse(RoleAssignment.objects.exists())
        self.assertFalse(Service.objects.exclude(pk=self.legacy.pk).filter(confirmed=True).exists())
        self.assertFalse(Service.objects.exclude(pk=self.legacy.pk).exclude(public_slug=None).exists())
        self.assertEqual(self.load()['changed'],[])
        self.assertEqual(Service.objects.count(),7)
    def test_public_contacts_audience_and_source_are_explicit_without_enabling_requests(self):
        self.load();r=APIClient().get('/api/v1/public/services/');self.assertEqual(r.status_code,200)
        self.assertFalse(r.data['appointments_enabled']);self.assertTrue(all(not s['request_enabled'] for s in r.data['services']))
        rows=r.data['published_services'];self.assertEqual(len(rows),6)
        self.assertTrue(all(s['source_url']=='https://www.unimodelo.edu.mx/servicios' for s in rows))
        physio=next(s for s in rows if s['area']=='fisioterapia')
        self.assertEqual(physio['contacts'][0]['href'],'');self.assertIn('nueve dígitos',physio['notes'])
        unit=next(s for s in rows if s['audience']=='university');self.assertIsNone(unit['school']);self.assertEqual(unit['area'],'')
        self.assertFalse(any(s['area']=='psicologia' for s in rows))
    def test_existing_operational_decisions_and_publication_state_survive_reimport(self):
        self.load();row=InstitutionalService.objects.get(area='odontologia');row.service.name='Nombre operativo ajustado';row.service.confirmed=True;row.service.save();row.published=False;row.save()
        self.load();row.refresh_from_db();self.assertEqual(row.service.name,'Nombre operativo ajustado');self.assertTrue(row.service.confirmed);self.assertFalse(row.published)
        self.assertEqual(len(APIClient().get('/api/v1/public/services/').data['published_services']),5)
    def test_school_dashboard_contains_only_its_published_services(self):
        self.load();user=get_user_model().objects.create_user('health-director');today=timezone.localdate()
        SchoolMandate.objects.create(school=self.health,user=user,approved_by=self.actor,starts=today-timedelta(days=1),ends=today+timedelta(days=10),rationale='Prueba')
        client=APIClient();client.force_authenticate(user=user)
        r=client.get(f'/api/v1/schools/{self.health.pk}/');self.assertEqual(r.status_code,200);self.assertEqual(len(r.data['published_services']),4)
        self.assertTrue(all(s['school']==self.health.pk for s in r.data['published_services']))
        self.assertEqual(client.get(f'/api/v1/schools/{self.dental.pk}/').status_code,404)
