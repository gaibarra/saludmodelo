import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .test_academic import AcademicTests
from .models import *
from .school_access import managed_schools
from .governance import managed_institutions,managed_services
from .access import scopes
from .academic_assessment import build_snapshot,digest

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class SchoolTests(TestCase):
    def setUp(self):
        AcademicTests.setUp(self)
        self.health=School.objects.create(institution=self.inst,code='salud',name='Escuela de Salud')
        self.dent=School.objects.create(institution=self.inst,code='odontologia',name='Escuela de Odontología')
        self.health_director=get_user_model().objects.create_user('health-director')
        InstitutionMember.objects.create(institution=self.inst,user=self.health_director)
        # Deliberately leave obsolete broad authority and foreign roles: they must not expand scope.
        InstitutionMandate.objects.create(institution=self.inst,user=self.health_director,approved_by=self.approver,starts=self.start,ends=self.end,rationale='Legacy')
        for school,user in [(self.dent,self.director),(self.health,self.health_director)]:
            SchoolMandate.objects.create(school=school,user=user,approved_by=self.approver,starts=self.start,ends=self.end,rationale='School direction')
            SchoolMember.objects.create(school=school,user=user)
        self.dental.school=self.dent;self.dental.save()
        self.physio.school=self.health;self.physio.save()
        self.cycle.school=self.dent;self.cycle.save()
        self.student.school=self.dent;self.student.save()
        for u in (self.student_user,self.supervisor):SchoolMember.objects.create(school=self.dent,user=u)
        RoleAssignment.objects.create(user=self.health_director,service=self.dental,role='director',starts=self.start,ends=self.end,approved_by=self.approver)
        self.grant=SchoolAcademicGrant.objects.create(school=self.dent,reader_school=self.health,approved_by=self.director,starts=self.start,ends=self.end,rationale='Consulta de prácticas')
        self.practice=AcademicPractice.objects.create(placement=self.placement,client_key=uuid.uuid4(),title='Práctica',performed_on=self.today,minutes=60,competency='Comunicación',evidence_reference='Bitácora',status='validated')
        snap=build_snapshot(self.cycle)
        self.report=AcademicCycleReport.objects.create(cycle=self.cycle,sequence=1,source_revision=self.cycle.revision,snapshot=snap,digest=digest(snap),client_key=uuid.uuid4(),created_by=self.director)
    def client_for(self,user):
        c=APIClient();c.force_authenticate(user);return c
    def test_school_directors_have_no_legacy_global_or_foreign_service_authority(self):
        self.assertEqual(list(managed_institutions(self.director)),[])
        self.assertEqual(list(managed_institutions(self.health_director)),[])
        self.assertEqual(set(scopes(self.health_director)),{self.physio.pk})
        self.assertEqual(set(managed_services(self.director).values_list('id',flat=True)),{self.dental.pk})
        c=self.client_for(self.health_director)
        self.assertEqual(c.get(f'/api/v1/schools/{self.dent.pk}/management/').status_code,404)
        self.assertEqual(c.get(f'/api/v1/tracking/services/{self.dental.pk}/').status_code,404)
        self.assertEqual(c.post(f'/api/v1/administration/services/{self.dental.pk}/confirm/',{'version':0,'rationale':'Prueba'},format='json').status_code,404)
    def test_historical_grant_never_allows_read_or_write(self):
        c=self.client_for(self.health_director)
        self.assertEqual(c.get(f'/api/v1/schools/{self.dent.pk}/').status_code,404)
        self.assertEqual(c.get('/api/v1/academic/placements/').data['count'],0)
        self.assertEqual(c.get(f'/api/v1/academic/reports/{self.report.pk}/').status_code,404)
        for path,payload in [(f'placements/{self.placement.pk}/revoke/',{'rationale':'Intento ajeno'}),(f'practices/{self.practice.pk}/review/',{'version':1,'action':'void','rationale':'Intento ajeno'}),(f'reports/{self.report.pk}/close/',{'rationale':'Intento ajeno','accept_pending':True}),(f'cycles/{self.cycle.pk}/reopen/',{'rationale':'Intento ajeno','report':self.report.pk}),(f'cycles/{self.cycle.pk}/reports/',{'client_key':str(uuid.uuid4())})]:
            result=c.post('/api/v1/academic/'+path,payload,format='json');self.assertIn(result.status_code,(403,404),(path,result.data))
    def test_revocation_removes_direct_lookup_and_listing_immediately(self):
        c=self.client_for(self.health_director);self.grant.revoked_at=timezone.now();self.grant.save()
        self.assertEqual(c.get(f'/api/v1/academic/reports/{self.report.pk}/').status_code,404)
        self.assertEqual(c.get('/api/v1/academic/practices/').data['count'],0)
        self.assertEqual(c.get(f'/api/v1/schools/{self.dent.pk}/').status_code,404)
    def test_expired_direction_loses_shared_and_own_scope_without_legacy_fallback(self):
        SchoolMandate.objects.filter(user=self.health_director).update(ends=self.today-timedelta(days=1))
        self.assertEqual(list(scopes(self.health_director)),[])
        self.assertEqual(self.client_for(self.health_director).get('/api/v1/schools/').data['count'],0)
    def test_own_cycle_creation_and_cross_school_payload_rejected(self):
        c=self.client_for(self.director);payload={'institution':self.inst.pk,'school':self.dent.pk,'code':'NEW','name':'Nuevo','starts':str(self.start),'ends':str(self.end)}
        r=c.post('/api/v1/academic/cycles/',payload,format='json');self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(c.post('/api/v1/academic/cycles/',{**payload,'school':self.health.pk},format='json').status_code,403)
        self.assertEqual(c.post('/api/v1/academic/cycles/',{k:v for k,v in payload.items() if k!='school'},format='json').status_code,403)
    def test_placement_and_rubric_cannot_mix_schools(self):
        c=self.client_for(self.director)
        r=c.post('/api/v1/academic/placements/',{'student':self.student.pk,'cycle':self.cycle.pk,'service':self.physio.pk,'supervisor':self.supervisor.pk,'group':'X','starts':str(self.start),'ends':str(self.end)},format='json')
        self.assertEqual(r.status_code,404)
    def test_own_service_and_user_creation_no_foreign_members(self):
        c=self.client_for(self.director)
        r=c.post(f'/api/v1/schools/{self.dent.pk}/services/',{'site':self.dental.site_id,'name':'Clínica nueva'},format='json');self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(Service.objects.get(pk=r.data['id']).school_id,self.dent.pk)
        r=c.post(f'/api/v1/schools/{self.health.pk}/services/',{'site':self.physio.site_id,'name':'Ajeno'},format='json');self.assertEqual(r.status_code,404)
        members=c.get(f'/api/v1/schools/{self.dent.pk}/management/').data['users'];self.assertNotIn(self.health_director.pk,[m['id'] for m in members])
    def test_shared_access_is_not_reciprocal_or_institution_wide(self):
        c=self.client_for(self.director);self.assertEqual(c.get(f'/api/v1/schools/{self.health.pk}/').status_code,404)
        third=School.objects.create(institution=self.inst,code='tercera',name='Tercera escuela')
        self.assertEqual(self.client_for(self.health_director).get(f'/api/v1/schools/{third.pk}/').status_code,404)
    def test_only_source_school_can_grant_and_revoke(self):
        c=self.client_for(self.health_director)
        url=f'/api/v1/schools/{self.dent.pk}/academic-grants/{self.grant.pk}/revoke/'
        self.assertEqual(c.post(url,{'rationale':'Retirar acceso'},format='json').status_code,404)
        self.assertEqual(self.client_for(self.director).post(url,{'rationale':'Retirar acceso'},format='json').status_code,200)
    def test_existing_snapshot_is_not_rewritten(self):
        original=self.report.snapshot.copy();digest_before=self.report.digest
        self.dent.name='Escuela de Odontología actualizada';self.dent.save()
        self.report.refresh_from_db();self.assertEqual(self.report.snapshot,original);self.assertEqual(self.report.digest,digest_before)
    @override_settings(MFA_REQUIRE_PRIVILEGED=True)
    def test_school_direction_requires_mfa_without_institutional_mandate(self):
        from .mfa import required
        InstitutionMandate.objects.filter(user=self.director).delete()
        self.assertTrue(required(self.director))

    def test_configuration_plan_is_dry_run_then_preserves_history(self):
        import tempfile,json,io
        from pathlib import Path
        from django.core.management import call_command
        self.dental.school=None;self.dental.save();self.cycle.school=None;self.cycle.save();self.student.school=None;self.student.save()
        prior_digest=self.report.digest
        plan={'institution':self.inst.pk,'approved_by':self.approver.username,'starts':str(self.start),'ends':str(self.end),'rationale':'Clasificación institucional revisada','schools':[{'code':'odontologia','name':self.dent.name,'director':self.director.username,'members':[self.director.username,self.supervisor.username,self.student_user.username],'services':[self.dental.pk],'cycles':[self.cycle.pk],'students':[self.student.pk]}]}
        with tempfile.TemporaryDirectory(prefix='salud-school-plan-') as folder:
            path=Path(folder)/'plan.json';path.write_text(json.dumps(plan))
            call_command('configure_schools',plan=str(path),stdout=io.StringIO())
            self.cycle.refresh_from_db();self.assertIsNone(self.cycle.school_id)
            call_command('configure_schools',plan=str(path),apply=True,stdout=io.StringIO())
        self.cycle.refresh_from_db();self.report.refresh_from_db()
        self.assertEqual(self.cycle.school_id,self.dent.pk);self.assertEqual(self.report.digest,prior_digest)
        self.assertGreater(self.cycle.revision,self.report.source_revision)

    def test_configuration_rejects_mixed_ownership_atomically(self):
        import tempfile,json,io
        from pathlib import Path
        from django.core.management import call_command,CommandError
        self.dental.school=None;self.dental.save()
        plan={'institution':self.inst.pk,'approved_by':self.approver.username,'starts':str(self.start),'ends':str(self.end),'rationale':'Plan incompatible de prueba','schools':[{'code':'salud','name':self.health.name,'director':self.health_director.username,'members':[self.health_director.username],'services':[self.dental.pk]}]}
        with tempfile.TemporaryDirectory(prefix='salud-school-plan-') as folder:
            path=Path(folder)/'plan.json';path.write_text(json.dumps(plan))
            with self.assertRaises(CommandError):call_command('configure_schools',plan=str(path),apply=True,stdout=io.StringIO())
        self.dental.refresh_from_db();self.assertIsNone(self.dental.school_id)

    def test_no_school_can_enable_sharing(self):
        for user,school,target in [(self.director,self.dent,self.health),(self.health_director,self.health,self.dent)]:
            c=self.client_for(user)
            self.assertEqual([r['id'] for r in c.get('/api/v1/schools/').data['results']],[school.pk])
            url=f'/api/v1/schools/{school.pk}/academic-grants/'
            self.assertEqual(c.get(url).data,{'schools':[],'grants':[],'sharing_enabled':False})
            self.assertEqual(c.post(url,{'reader_school':target.pk,'starts':str(self.start),'ends':str(self.end),'rationale':'No permitido'},format='json').status_code,403)

    def test_institutional_administrator_keeps_both_schools(self):
        admin=get_user_model().objects.create_superuser('institution-admin','admin@example.test','test-only')
        InstitutionMandate.objects.create(institution=self.inst,user=admin,approved_by=self.approver,starts=self.start,ends=self.end,rationale='Institutional administration')
        self.assertEqual({r['id'] for r in self.client_for(admin).get('/api/v1/schools/').data['results']},{self.health.pk,self.dent.pk})
