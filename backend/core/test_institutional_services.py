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
        result=self.load();self.assertEqual(len(result['created']),7);self.assertEqual(InstitutionalService.objects.count(),7)
        self.assertEqual(Service.objects.filter(pk=self.legacy.pk).values().get(),before[0])
        self.assertFalse(RoleAssignment.objects.exists())
        self.assertFalse(Service.objects.exclude(pk=self.legacy.pk).filter(confirmed=True).exists())
        self.assertFalse(Service.objects.exclude(pk=self.legacy.pk).exclude(public_slug=None).exists())
        self.assertEqual(self.load()['changed'],[])
        self.assertEqual(Service.objects.count(),8)
    def test_public_contacts_audience_and_source_are_explicit_without_enabling_requests(self):
        self.load();r=APIClient().get('/api/v1/public/services/');self.assertEqual(r.status_code,200)
        self.assertFalse(r.data['appointments_enabled']);self.assertTrue(all(not s['request_enabled'] for s in r.data['services']))
        rows=r.data['published_services'];self.assertEqual(len(rows),7)
        self.assertTrue(all(s['source_url']=='https://www.unimodelo.edu.mx/servicios' for s in rows))
        physio=next(s for s in rows if s['area']=='fisioterapia')
        self.assertEqual(physio['contacts'][0]['href'],'');self.assertIn('nueve dígitos',physio['notes'])
        unit=next(s for s in rows if s['audience']=='university');self.assertIsNone(unit['school']);self.assertEqual(unit['area'],'')
        psych=next(s for s in rows if s['area']=='psicologia')
        self.assertEqual(psych['school'],self.health.pk)
        self.assertEqual(psych['additional_areas'],[])
        self.assertIn('yucatan.gob.mx',psych['additional_sources'][0]['url'])
        self.assertEqual(psych['code'],'modelo-usc-casita')
    def test_existing_operational_decisions_and_publication_state_survive_reimport(self):
        self.load();row=InstitutionalService.objects.get(area='odontologia');row.service.name='Nombre operativo ajustado';row.service.confirmed=True;row.service.save();row.published=False;row.save()
        self.load();row.refresh_from_db();self.assertEqual(row.service.name,'Nombre operativo ajustado');self.assertTrue(row.service.confirmed);self.assertFalse(row.published)
        self.assertEqual(len(APIClient().get('/api/v1/public/services/').data['published_services']),6)
    def test_school_dashboard_contains_only_its_published_services(self):
        self.load();user=get_user_model().objects.create_user('health-director');today=timezone.localdate()
        SchoolMandate.objects.create(school=self.health,user=user,approved_by=self.actor,starts=today-timedelta(days=1),ends=today+timedelta(days=10),rationale='Prueba')
        client=APIClient();client.force_authenticate(user=user)
        r=client.get(f'/api/v1/schools/{self.health.pk}/');self.assertEqual(r.status_code,200);self.assertEqual(len(r.data['published_services']),5)
        self.assertTrue(all(s['school']==self.health.pk for s in r.data['published_services']))
        self.assertEqual(client.get(f'/api/v1/schools/{self.dental.pk}/').status_code,404)

    def test_existing_casita_identity_and_operational_decisions_preserved(self):
        self.load()
        row=InstitutionalService.objects.get(code='modelo-usc-casita')
        service=row.service
        service.name='USC Casita';service.public_slug='atencion-comunitaria';service.confirmed=True;service.save()
        row.public_name='USC Casita';row.area='atencion-comunitaria';row.additional_areas=[];row.additional_sources=[];row.published=False;row.save()
        before=(service.pk,service.site_id,service.school_id,service.etag,Service.objects.count())
        self.load(False);service.refresh_from_db();self.assertEqual(service.name,'USC Casita')
        result=self.load();service.refresh_from_db();row.refresh_from_db()
        self.assertEqual(result['created'],[]);self.assertEqual(result['renamed'],['modelo-usc-casita'])
        self.assertEqual((service.pk,service.site_id,service.school_id,Service.objects.count()),(before[0],before[1],before[2],before[4]))
        self.assertEqual(service.etag,before[3]+1);self.assertTrue(service.confirmed)
        self.assertEqual(service.public_slug,'atencion-comunitaria');self.assertFalse(row.published)
        self.assertEqual(row.area,'psicologia');self.assertEqual(row.additional_areas,[])
        self.assertEqual(self.load()['changed'],[]);self.assertEqual(self.load()['renamed'],[])
        service.name='Nombre decidido por el servicio';service.save();self.load();service.refresh_from_db()
        self.assertEqual(service.name,'Nombre decidido por el servicio')

    def test_distinct_services_share_site_without_copying_confirmation_or_assignments(self):
        self.load()
        psych=InstitutionalService.objects.get(code='modelo-usc-casita').service
        community=InstitutionalService.objects.get(code='modelo-atencion-comunitaria-casita').service
        self.assertNotEqual(psych.pk,community.pk)
        self.assertEqual(psych.site_id,community.site_id)
        self.assertEqual(community.site.name,'La Casita')
        self.assertEqual(community.school_id,self.health.pk)
        psych.confirmed=True;psych.save()
        self.load();community.refresh_from_db()
        self.assertFalse(community.confirmed);self.assertIsNone(community.public_slug)
        self.assertFalse(community.roleassignment_set.exists())
        custom=Site.objects.create(campus=psych.site.campus,name='Sede ajustada por Dirección')
        psych.site=custom;psych.save();self.load();psych.refresh_from_db()
        self.assertEqual(psych.site_id,custom.pk)

    def test_move_only_original_placeholder_preserves_other_services(self):
        self.load()
        psych=InstitutionalService.objects.get(code='modelo-usc-casita').service
        placeholder=Site.objects.get(name='Ubicación por confirmar con el servicio')
        psych.site=placeholder;psych.save()
        other_before=list(Service.objects.exclude(pk=psych.pk).values())
        self.load(False);psych.refresh_from_db();self.assertEqual(psych.site_id,placeholder.pk)
        self.load();psych.refresh_from_db();self.assertEqual(psych.site.name,'La Casita')
        self.assertEqual(list(Service.objects.exclude(pk=psych.pk).values()),other_before)
