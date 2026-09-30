import uuid
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .test_academic import AcademicTests
from .models import AcademicRubric,AcademicEvaluation,AcademicCycleReport,AcademicPlacement,AcademicPractice,AcademicCycle,AcademicCompetency,RoleAssignment

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class AssessmentTests(TestCase):
    setUp=AcademicTests.setUp
    post=AcademicTests.post
    payload=AcademicTests.payload
    create=AcademicTests.create

    def rubric(self,**changes):
        return {'cycle':self.cycle.pk,'service':self.dental.pk,'program':'','code':'COM-01','version':0,'title':'Comunicación','criterion':'Explica los pasos y comprueba comprensión.','levels':[{'label':'En desarrollo','description':'Requiere guía frecuente.'},{'label':'Lograda','description':'Explica y verifica comprensión.'},{'label':'Avanzada','description':'Adapta la explicación con autonomía.'}],'required_level':2,'required':True,'rationale':'Criterio sintético definido por Dirección.',**changes}

    def configure(self,**changes):
        r=self.post('rubrics/',self.rubric(**changes));self.assertEqual(r.status_code,201,r.data);return r.data

    def validated_practice(self,**changes):
        p=self.create(**changes)
        r=self.post(f"practices/{p['id']}/review/",{'version':1,'action':'validate','rationale':'Participación comprobada.'},self.supervisor)
        self.assertEqual(r.status_code,200,r.data);return r.data

    def evaluation(self,r,p,**changes):
        return {'rubric':r['id'],'version':0,'score':2,'rationale':'El alumno explica y verifica comprensión; evidencia revisada.','evidence':[{'practice':p['id'],'version':p['etag']}],**changes}

    def evaluate(self,r,p,**changes):
        response=self.post(f'placements/{self.placement.pk}/evaluations/',self.evaluation(r,p,**changes),self.supervisor)
        self.assertEqual(response.status_code,201,response.data);return response.data

    def end_cycle(self):
        self.cycle.ends=self.today;self.cycle.save(update_fields=['ends'])
        self.placement.ends=self.today;self.placement.save(update_fields=['ends'])

    def report(self):
        r=self.post(f'cycles/{self.cycle.pk}/reports/',{'client_key':str(uuid.uuid4())})
        self.assertEqual(r.status_code,201,r.data);return r.data

    def test_rubric_is_institutional_versioned_and_program_scoped(self):
        self.assertEqual(self.post('rubrics/',self.rubric(),self.supervisor).status_code,404)
        self.assertEqual(self.post('rubrics/',self.rubric(required_level=4)).status_code,400)
        r=self.configure();new=self.configure(version=1,required_level=3)
        self.assertEqual(new['version'],2);self.assertEqual(AcademicRubric.objects.get(pk=r['id']).required_level,2)
        self.assertEqual(self.post('rubrics/',self.rubric(version=1)).status_code,409)
        self.configure(code='OTRO',program='Otro programa')
        result=self.client.get('/api/v1/academic/rubrics/').data['results']
        self.assertEqual([x['id'] for x in result],[new['id']])
        user=APIClient();user.force_authenticate(self.stranger)
        self.assertEqual(user.get('/api/v1/academic/rubrics/').data['results'],[])

    def test_evaluation_requires_assigned_supervisor_current_validated_evidence_and_rubric(self):
        r=self.configure();p=self.create();url=f'placements/{self.placement.pk}/evaluations/'
        payload=self.evaluation(r,p)
        for who in [self.student_user,self.director]:self.assertEqual(self.post(url,payload,who).status_code,403)
        self.assertEqual(self.post(url,payload,self.supervisor).status_code,400)
        p=self.post(f"practices/{p['id']}/review/",{'version':1,'action':'validate','rationale':'Evidencia verificada.'},self.supervisor).data
        self.assertEqual(self.post(url,payload,self.supervisor).status_code,400)
        self.assertEqual(self.post(url,self.evaluation(r,p,score=4),self.supervisor).status_code,400)
        self.evaluate(r,p)
        self.assertEqual(self.post(url,self.evaluation(r,p),self.supervisor).status_code,409)

    def test_other_rotation_evidence_and_self_supervision_are_rejected(self):
        r=self.configure();p=self.validated_practice()
        other=AcademicPlacement.objects.create(student=self.other,cycle=self.cycle,service=self.dental,supervisor=self.supervisor,group='G2',starts=self.start,ends=self.end,created_by=self.director)
        self.assertEqual(self.post(f'placements/{other.pk}/evaluations/',self.evaluation(r,p),self.supervisor).status_code,400)
        self.assignment.revoked_at=timezone.now();self.assignment.save()
        self.assertEqual(self.post(f'placements/{self.placement.pk}/evaluations/',self.evaluation(r,p),self.supervisor).status_code,404)

    def test_evaluations_are_append_only_and_changed_evidence_or_rubric_requires_review(self):
        r=self.configure();p=self.validated_practice();first=self.evaluate(r,p,score=1)
        self.evaluate(r,p,version=1,score=3)
        current=self.client.get(f'/api/v1/academic/placements/{self.placement.pk}/evaluations/').data['results'][0]
        self.assertEqual(current['state'],'achieved');self.assertEqual(AcademicEvaluation.objects.get(pk=first['id']).score,1)
        new=self.configure(version=1,required_level=3)
        self.assertEqual(self.client.get(f'/api/v1/academic/placements/{self.placement.pk}/evaluations/').data['results'][0]['state'],'needs_review')
        self.evaluate(new,p,version=2,score=3)
        self.post(f"practices/{p['id']}/review/",{'version':p['etag'],'action':'void','rationale':'Registro de evidencia anulado.'})
        self.assertEqual(self.client.get(f'/api/v1/academic/placements/{self.placement.pk}/evaluations/').data['results'][0]['state'],'needs_review')
        history=self.client.get(f'/api/v1/academic/placements/{self.placement.pk}/evaluations/history/').data['results']
        self.assertEqual(len(history),3);self.assertEqual(history[-1]['rubric_snapshot']['required_level'],2)

    def test_snapshot_includes_all_students_services_pending_and_empty_rotations(self):
        self.validated_practice()
        AcademicPlacement.objects.create(student=self.other,cycle=self.cycle,service=self.physio,supervisor=self.supervisor,group='G2',starts=self.start,ends=self.end,created_by=self.director)
        r=self.report();s=r['snapshot']
        self.assertEqual(len(s['students']),2);self.assertEqual(len(s['services']),2)
        self.assertEqual(s['totals']['validated']['minutes'],60)
        self.assertTrue(any('Sin rúbricas' in i for i in s['issues']))
        self.assertFalse(s['automatic_accreditation'])
        self.assertEqual(s['students'][1]['placements'][0]['practices'],[])

    def test_snapshot_is_immutable_and_new_mutations_make_draft_stale(self):
        r=self.configure();p=self.validated_practice();self.evaluate(r,p)
        report=self.report();old=AcademicCycleReport.objects.get(pk=report['id']).snapshot
        self.create(minutes=30)
        self.assertEqual(AcademicCycleReport.objects.get(pk=report['id']).snapshot,old)
        self.assertEqual(self.post(f"reports/{report['id']}/close/",{'rationale':'Intento de cerrar corte anterior.','accept_pending':True}).status_code,409)
        director=APIClient();director.force_authenticate(self.director)
        self.assertTrue(director.get(f"/api/v1/academic/reports/{report['id']}/").data['stale'])

    def test_close_pending_requires_acknowledgement_and_end_date(self):
        report=self.report();v={'rationale':'Cierre con pendientes documentados.','accept_pending':True}
        self.assertEqual(self.post(f"reports/{report['id']}/close/",v).status_code,400)
        self.end_cycle()
        self.assertEqual(self.post(f"reports/{report['id']}/close/",{'rationale':'Cierre sin reconocer pendientes.'}).status_code,400)
        self.assertEqual(self.post(f"reports/{report['id']}/close/",v,self.supervisor).status_code,404)
        self.assertEqual(self.post(f"reports/{report['id']}/close/",v).status_code,200)

    def test_closed_cycle_blocks_all_academic_writes_until_explicit_reopen(self):
        self.end_cycle();r=self.configure();p=self.validated_practice();self.evaluate(r,p);report=self.report()
        result=self.post(f"reports/{report['id']}/close/",{'rationale':'Cierre documental del ciclo.','accept_pending':True});self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(self.post('practices/',self.payload(),self.student_user).status_code,400)
        self.assertEqual(self.post(f"practices/{p['id']}/review/",{'version':2,'action':'void','rationale':'Intento de editar cierre.'}).status_code,400)
        self.assertEqual(self.post('rubrics/',self.rubric(version=1)).status_code,400)
        self.assertEqual(self.post(f'placements/{self.placement.pk}/evaluations/',self.evaluation(r,p,version=1),self.supervisor).status_code,400)
        self.assertEqual(self.post(f'placements/{self.placement.pk}/revoke/',{'rationale':'Intento tras cierre.'}).status_code,400)
        self.assertEqual(self.post(f'cycles/{self.cycle.pk}/reopen/',{'report':report['id'],'rationale':'Corrección documental autorizada.'}).status_code,200)
        self.assertEqual(self.post('practices/',self.payload(),self.student_user).status_code,201)
        old=AcademicCycleReport.objects.get(pk=report['id']);self.assertIsNotNone(old.closed_at)
        next_report=self.report();self.assertEqual(next_report['sequence'],2)

    def test_students_only_see_their_closed_individual_reports_and_supervisors_not_consolidated(self):
        self.end_cycle();self.validated_practice()
        AcademicPlacement.objects.create(student=self.other,cycle=self.cycle,service=self.physio,supervisor=self.supervisor,group='G2',starts=self.start,ends=self.today,created_by=self.director)
        report=self.report();url=f"/api/v1/academic/reports/{report['id']}/"
        self.assertEqual(self.client.get(url).status_code,404)
        self.post(f"reports/{report['id']}/close/",{'rationale':'Cierre de revisión institucional.','accept_pending':True})
        personal=self.client.get(url).data
        self.assertEqual(personal['kind'],'individual');self.assertEqual([s['id'] for s in personal['snapshot']['students']],[self.student.pk])
        self.assertEqual(self.client.get(url+f'?student={self.other.pk}').status_code,403)
        supervisor=APIClient();supervisor.force_authenticate(self.supervisor);self.assertEqual(supervisor.get(url).status_code,404)
        director=APIClient();director.force_authenticate(self.director)
        self.assertEqual(len(director.get(url).data['snapshot']['students']),2)
        self.assertEqual(len(director.get(url+f'?student={self.other.pk}').data['snapshot']['students']),1)

    def test_reports_keep_all_records_beyond_page_boundary_and_retry_is_idempotent(self):
        for i in range(51):self.create(minutes=1,title=f'Práctica {i}')
        key=str(uuid.uuid4());url=f'cycles/{self.cycle.pk}/reports/'
        first=self.post(url,{'client_key':key});retry=self.post(url,{'client_key':key})
        self.assertEqual(first.status_code,201);self.assertEqual(retry.status_code,200)
        self.assertEqual(first.data['id'],retry.data['id'])
        self.assertEqual(len(first.data['snapshot']['students'][0]['placements'][0]['practices']),51)

    def test_snapshot_integrity_is_checked_before_read_and_close(self):
        self.end_cycle();report=self.report()
        AcademicCycleReport.objects.filter(pk=report['id']).update(snapshot={'broken':True})
        director=APIClient();director.force_authenticate(self.director)
        self.assertEqual(director.get(f"/api/v1/academic/reports/{report['id']}/").status_code,400)
        self.assertEqual(self.post(f"reports/{report['id']}/close/",{'rationale':'Cierre con contenido inconsistente.','accept_pending':True}).status_code,400)

    def test_supervisor_rubric_visibility_matches_cycle_and_service_together(self):
        first=self.configure()
        other_cycle=AcademicCycle.objects.create(institution=self.inst,code='OTRO',name='Otro ciclo',starts=self.start,ends=self.end,created_by=self.director)
        AcademicPlacement.objects.create(student=self.other,cycle=other_cycle,service=self.physio,supervisor=self.supervisor,group='G2',starts=self.start,ends=self.end,created_by=self.director)
        hidden=self.configure(service=self.physio.pk,code='NO-VISIBLE')
        c=APIClient();c.force_authenticate(self.supervisor)
        ids=[r['id'] for r in c.get('/api/v1/academic/rubrics/').data['results']]
        self.assertIn(first['id'],ids);self.assertNotIn(hidden['id'],ids)

    def test_student_report_redacts_institutional_closing_reason(self):
        self.end_cycle();report=self.report()
        self.post(f"reports/{report['id']}/close/",{'rationale':'A002 tiene un asunto privado documentado en Dirección.','accept_pending':True})
        personal=self.client.get(f"/api/v1/academic/reports/{report['id']}/").data
        self.assertNotIn('A002',str(personal))

    def test_new_student_after_reopening_does_not_receive_old_report_without_their_record(self):
        self.end_cycle();report=self.report()
        self.post(f"reports/{report['id']}/close/",{'rationale':'Cierre documental sintético.','accept_pending':True})
        self.post(f'cycles/{self.cycle.pk}/reopen/',{'report':report['id'],'rationale':'Incorporación posterior documentada.'})
        AcademicPlacement.objects.create(student=self.other,cycle=self.cycle,service=self.physio,supervisor=self.supervisor,group='G2',starts=self.start,ends=self.today,created_by=self.director)
        c=APIClient();c.force_authenticate(self.other_user)
        self.assertEqual(c.get(f'/api/v1/academic/cycles/{self.cycle.pk}/reports/').data['count'],0)
        self.assertEqual(c.get(f"/api/v1/academic/reports/{report['id']}/").status_code,404)

from django.test import TransactionTestCase
from django.db import close_old_connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class AcademicClosureConcurrencyTests(TransactionTestCase):
    setUp=AcademicTests.setUp
    post=AcademicTests.post
    payload=AcademicTests.payload
    end_cycle=AssessmentTests.end_cycle
    report=AssessmentTests.report

    def test_closure_and_late_practice_cannot_both_succeed_against_same_snapshot(self):
        self.end_cycle();report=self.report();barrier=Barrier(2)
        def run(which):
            close_old_connections()
            try:
                c=APIClient();c.force_authenticate(self.director if which=='close' else self.student_user)
                barrier.wait(timeout=10)
                if which=='close':return c.post(f"/api/v1/academic/reports/{report['id']}/close/",{'rationale':'Cierre en prueba concurrente.','accept_pending':True},format='json').status_code
                return c.post('/api/v1/academic/practices/',self.payload(),format='json').status_code
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            close,mutation=list(pool.map(run,['close','practice']))
        self.assertIn((close,mutation),[(200,400),(409,201)])
        if close==200:self.assertEqual(AcademicPractice.objects.count(),0)
