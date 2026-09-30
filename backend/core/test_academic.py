import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import (Institution, InstitutionMember, InstitutionMandate, Campus, Site, Service, RoleAssignment,
    AcademicStudent, AcademicCycle, AcademicPlacement, AcademicPractice, AcademicPracticeEvent)

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class AcademicTests(TestCase):
    def setUp(self):
        self.today=timezone.localdate();self.start=self.today-timedelta(days=20);self.end=self.today+timedelta(days=20)
        U=get_user_model()
        self.director=U.objects.create_user('academic-director');self.supervisor=U.objects.create_user('academic-supervisor')
        self.student_user=U.objects.create_user('academic-student');self.other_user=U.objects.create_user('other-student')
        self.stranger=U.objects.create_user('stranger');self.approver=U.objects.create_user('approver')
        self.inst=Institution.objects.create(name='Institución académica sintética');self.foreign=Institution.objects.create(name='Institución ajena')
        for u in [self.director,self.supervisor,self.student_user,self.other_user]:InstitutionMember.objects.create(institution=self.inst,user=u)
        InstitutionMandate.objects.create(institution=self.inst,user=self.director,approved_by=self.approver,starts=self.start,ends=self.end,rationale='Prueba')
        site=Site.objects.create(campus=Campus.objects.create(institution=self.inst,name='Campus'),name='Sede')
        self.dental=Service.objects.create(site=site,name='Odontología',confirmed=True)
        self.physio=Service.objects.create(site=site,name='Fisioterapia',confirmed=True)
        self.assignment=RoleAssignment.objects.create(user=self.supervisor,service=self.dental,role='clinical',starts=self.start,ends=self.end,approved_by=self.director)
        RoleAssignment.objects.create(user=self.supervisor,service=self.physio,role='clinical',starts=self.start,ends=self.end,approved_by=self.director)
        self.student=AcademicStudent.objects.create(institution=self.inst,user=self.student_user,enrollment='A001',program='Salud')
        self.other=AcademicStudent.objects.create(institution=self.inst,user=self.other_user,enrollment='A002',program='Salud')
        self.cycle=AcademicCycle.objects.create(institution=self.inst,code='2026',name='Ciclo de prueba',starts=self.start,ends=self.end,created_by=self.director)
        self.placement=AcademicPlacement.objects.create(student=self.student,cycle=self.cycle,service=self.dental,supervisor=self.supervisor,group='G1',starts=self.start,ends=self.end,target_minutes=600,created_by=self.director)
        self.client=APIClient();self.client.force_authenticate(self.student_user)

    def post(self,path,payload,user=None):
        client=APIClient();client.force_authenticate(user or self.director)
        return client.post('/api/v1/academic/'+path,payload,format='json')

    def payload(self,**kwargs):
        return {'placement':self.placement.pk,'client_key':str(uuid.uuid4()),'title':'Práctica sintética','performed_on':str(self.today),'minutes':60,'competency':'Comunicación profesional','evidence_reference':'Bitácora sintética 01','activity_reference':'Jornada-001',**kwargs}

    def create(self,**kwargs):
        result=self.client.post('/api/v1/academic/practices/',self.payload(**kwargs),format='json')
        self.assertEqual(result.status_code,201,result.data);return result.data

    def test_registration_and_cycles_require_institutional_authority(self):
        payload={'institution':self.inst.pk,'code':'nuevo','name':'Nuevo ciclo','starts':str(self.start),'ends':str(self.end)}
        self.assertEqual(self.post('cycles/',payload,self.supervisor).status_code,403)
        self.assertEqual(self.post('cycles/',{**payload,'institution':self.foreign.pk}).status_code,403)
        self.assertEqual(self.post('cycles/',{**payload,'starts':str(self.end),'ends':str(self.start)}).status_code,400)
        self.assertEqual(self.post('cycles/',payload).status_code,201)
        self.assertEqual(self.post('cycles/',payload).status_code,400)
        u=get_user_model().objects.create_user('new-student');InstitutionMember.objects.create(user=u,institution=self.inst)
        profile={'institution':self.inst.pk,'user':u.pk,'enrollment':'x002','program':'Nutrición'}
        self.assertEqual(self.post('students/',profile).status_code,201)
        self.assertEqual(self.post('students/',profile).status_code,400)
        self.assertEqual(self.post('students/',{**profile,'user':self.stranger.pk}).status_code,404)

    def test_placements_require_same_institution_dates_and_real_supervisor(self):
        v={'student':self.other.pk,'cycle':self.cycle.pk,'service':self.physio.pk,'supervisor':self.supervisor.pk,'group':'G2','starts':str(self.start),'ends':str(self.end)}
        self.assertEqual(self.post('placements/',v,self.student_user).status_code,404)
        self.assertEqual(self.post('placements/',{**v,'supervisor':self.other_user.pk}).status_code,400)
        self.assertEqual(self.post('placements/',{**v,'starts':str(self.start-timedelta(days=1))}).status_code,400)
        foreign_cycle=AcademicCycle.objects.create(institution=self.foreign,code='F',name='Otro',starts=self.start,ends=self.end,created_by=self.director)
        self.assertEqual(self.post('placements/',{**v,'cycle':foreign_cycle.pk}).status_code,404)
        self.assertEqual(self.post('placements/',v).status_code,201)
        self.assertEqual(self.post('placements/',v).status_code,400)

    def test_only_student_records_own_participation_and_requests_are_idempotent(self):
        v=self.payload()
        self.assertEqual(self.post('practices/',v,self.supervisor).status_code,404)
        self.assertEqual(self.post('practices/',v,self.other_user).status_code,404)
        self.assertEqual(self.post('practices/',v,self.student_user).status_code,201)
        self.assertEqual(self.post('practices/',v,self.student_user).status_code,200)
        self.assertEqual(self.post('practices/',{**v,'minutes':61},self.student_user).status_code,400)
        self.assertEqual(AcademicPractice.objects.count(),1)
        self.assertEqual(AcademicPracticeEvent.objects.count(),1)

    def test_return_correction_validation_preserve_history_and_only_validated_minutes(self):
        row=self.create();url=f"practices/{row['id']}/review/"
        decision={'version':1,'action':'return','rationale':'Falta precisar la evidencia.'}
        self.assertEqual(self.post(url,decision,self.student_user).status_code,403)
        self.assertEqual(self.post(url,decision,self.director).status_code,403)
        self.assertEqual(self.post(url,decision,self.supervisor).status_code,200)
        self.assertEqual(self.post(url,decision,self.supervisor).status_code,409)
        patch={k:v for k,v in self.payload(minutes=90).items() if k not in {'placement','client_key'}}
        patch.update(version=2,rationale='Se precisó evidencia y duración real.')
        self.assertEqual(self.post(f"practices/{row['id']}/resubmit/",patch,self.student_user).status_code,200)
        self.assertEqual(self.post(url,{'version':3,'action':'validate','rationale':'Evidencia y participación verificadas.'},self.supervisor).status_code,200)
        self.assertEqual(self.post(f"practices/{row['id']}/resubmit/",{**patch,'version':4},self.student_user).status_code,400)
        events=self.client.get(f"/api/v1/academic/practices/{row['id']}/history/").data['results']
        self.assertEqual([e['version'] for e in events],[1,2,3,4]);self.assertEqual(events[0]['snapshot']['minutes'],60)
        self.assertEqual(events[2]['snapshot']['minutes'],90)
        summary=self.client.get('/api/v1/academic/summary/').data
        self.assertEqual(summary['states'],[{'status':'validated','participations':1,'minutes':90}]);self.assertFalse(summary['academic_accreditation'])

    def test_revoked_supervisor_cannot_view_or_validate(self):
        row=self.create();self.assignment.revoked_at=timezone.now();self.assignment.save()
        c=APIClient();c.force_authenticate(self.supervisor)
        self.assertEqual(c.get('/api/v1/academic/practices/').data['count'],0)
        self.assertEqual(self.post(f"practices/{row['id']}/review/",{'version':1,'action':'validate','rationale':'No debe pasar.'},self.supervisor).status_code,404)
        self.assertEqual(self.client.get('/api/v1/academic/practices/').data['count'],1)

    def test_unauthorized_and_other_students_see_no_academic_records(self):
        row=self.create()
        for user in [self.stranger,self.other_user]:
            c=APIClient();c.force_authenticate(user)
            self.assertEqual(c.get('/api/v1/academic/practices/').data['count'],0)
            self.assertEqual(c.get(f"/api/v1/academic/practices/{row['id']}/history/").status_code,404)
            self.assertEqual(c.get('/api/v1/academic/summary/').data['states'],[])
            self.assertEqual(c.get('/api/v1/academic/options/').data['users'],[])
        anonymous=APIClient();self.assertEqual(anonymous.get('/api/v1/academic/practices/').status_code,403)

    def test_no_future_outside_dates_or_empty_evidence(self):
        for patch in [{'performed_on':str(self.today+timedelta(days=1))},{'performed_on':str(self.start-timedelta(days=1))},{'evidence_reference':''},{'minutes':0}]:
            self.assertEqual(self.post('practices/',self.payload(**patch),self.student_user).status_code,400)

    def test_daily_limit_is_shared_across_services(self):
        self.create(minutes=1000)
        other=AcademicPlacement.objects.create(student=self.student,cycle=self.cycle,service=self.physio,supervisor=self.supervisor,group='G1',starts=self.start,ends=self.end,created_by=self.director)
        self.assertEqual(self.post('practices/',self.payload(placement=other.pk,minutes=441),self.student_user).status_code,400)
        self.assertEqual(self.post('practices/',self.payload(placement=other.pk,minutes=440),self.student_user).status_code,201)

    def test_revoking_placement_stops_capture_but_preserves_history(self):
        row=self.create()
        self.assertEqual(self.post(f'placements/{self.placement.pk}/revoke/',{'rationale':'Fin de asignación sintética.'}).status_code,200)
        self.assertEqual(self.post('practices/',self.payload(),self.student_user).status_code,400)
        self.assertEqual(self.post(f"practices/{row['id']}/review/",{'version':1,'action':'validate','rationale':'Ya revocada.'},self.supervisor).status_code,403)
        self.assertEqual(self.client.get(f"/api/v1/academic/practices/{row['id']}/history/").status_code,200)

    def test_void_preserves_validated_record_and_removes_it_from_validated_totals(self):
        row=self.create();url=f"practices/{row['id']}/review/"
        self.assertEqual(self.post(url,{'version':1,'action':'validate','rationale':'Supervisión realizada.'},self.supervisor).status_code,200)
        self.assertEqual(self.post(url,{'version':2,'action':'void','rationale':'Registro duplicado documentado.'}).status_code,200)
        self.assertEqual(AcademicPractice.objects.get().minutes,60)
        self.assertEqual(AcademicPracticeEvent.objects.count(),3)
        self.assertEqual(self.client.get('/api/v1/academic/summary/').data['states'][0]['status'],'void')

    def test_paginated_history_and_filtered_summary_cover_all_records(self):
        for i in range(51):self.create(minutes=1,title=f'Participación {i}')
        page=self.client.get('/api/v1/academic/practices/').data
        self.assertEqual(page['count'],51);self.assertEqual(len(page['results']),50);self.assertIsNotNone(page['next'])
        summary=self.client.get(f'/api/v1/academic/summary/?cycle={self.cycle.pk}&service={self.dental.pk}').data
        self.assertEqual(summary['states'][0]['participations'],51)
        self.assertEqual(self.client.get(f'/api/v1/academic/summary/?service={self.physio.pk}').data['states'],[])
        self.assertEqual(self.client.get('/api/v1/academic/summary/?student=nope').status_code,400)
        self.assertEqual(self.client.get('/api/v1/academic/summary/?cycle=1&cycle=2').status_code,400)

    def test_csrf_required_for_session_mutation(self):
        c=APIClient(enforce_csrf_checks=True);c.force_login(self.student_user)
        self.assertEqual(c.post('/api/v1/academic/practices/',self.payload(),format='json').status_code,403)

    @override_settings(MFA_REQUIRE_PRIVILEGED=True)
    def test_privileged_academic_access_keeps_mfa_enforcement(self):
        client=APIClient();client.force_login(self.supervisor)
        self.assertEqual(client.get('/api/v1/academic/practices/').status_code,403)
        self.assertEqual(client.get('/api/v1/academic/options/').status_code,403)

    def test_institutional_view_covers_arbitrary_services_without_odontology_filter(self):
        for service in [self.dental,self.physio]:
            placement=self.placement if service==self.dental else AcademicPlacement.objects.create(student=self.student,cycle=self.cycle,service=service,supervisor=self.supervisor,group='G2',starts=self.start,ends=self.end,created_by=self.director)
            self.create(placement=placement.pk)
        c=APIClient();c.force_authenticate(self.director)
        self.assertEqual(c.get('/api/v1/academic/practices/').data['count'],2)
        self.assertEqual(c.get('/api/v1/academic/summary/?group=G2').data['states'][0]['participations'],1)
        # A clinical role in the service is not sufficient without personal supervision assignment.
        RoleAssignment.objects.create(user=self.stranger,service=self.dental,role='clinical',starts=self.start,ends=self.end,approved_by=self.director)
        c.force_authenticate(self.stranger)
        self.assertEqual(c.get('/api/v1/academic/practices/').data['count'],0)

from django.db import close_old_connections
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class AcademicConcurrencyTests(TransactionTestCase):
    setUp=AcademicTests.setUp
    payload=AcademicTests.payload

    def test_parallel_submissions_cannot_exceed_the_same_student_daily_limit(self):
        barrier=Barrier(2)
        def submit():
            close_old_connections()
            try:
                client=APIClient();client.force_authenticate(self.student_user)
                barrier.wait(timeout=10)
                return client.post('/api/v1/academic/practices/',self.payload(minutes=800),format='json').status_code
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:submit(),range(2)))
        self.assertEqual(sorted(results),[201,400])
        self.assertEqual(AcademicPractice.objects.count(),1)
        self.assertEqual(AcademicPracticeEvent.objects.count(),1)
