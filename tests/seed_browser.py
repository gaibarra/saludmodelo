"""Synthetic data only, guarded to the ephemeral browser-test cluster."""
import os
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Institution, InstitutionMember, InstitutionMandate, ImportBatch, CatalogAccess, SourceRecord, Question, QuestionVersion

sandbox = Path(os.environ['E2E_WORKDIR']).resolve()
if not sandbox.name.startswith('salud-e2e-') or settings.DATABASES['default']['HOST'] != str(sandbox / 'socket') or settings.DATABASES['default']['NAME'] != 'salud_e2e':
    raise RuntimeError('Fixture disabled outside isolated browser-test database')
User = get_user_model()
operator = User.objects.create_superuser('e2e_operator', password=os.environ['E2E_PASSWORD'])
director = User.objects.create_user('e2e_director', password=os.environ['E2E_PASSWORD'])
institution = Institution.objects.create(name='Institución sintética de pruebas')
InstitutionMember.objects.create(institution=institution, user=director)
InstitutionMandate.objects.create(institution=institution, user=director, approved_by=operator, starts=timezone.localdate()-timedelta(days=1), ends=timezone.localdate()+timedelta(days=30), rationale='Nombramiento sintético exclusivo de pruebas')
# Preserved source text; institutions, accounts and decisions remain synthetic.
import json
root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/'imports/help-drafts-v1.json').read_text())
records={r['stable_id']:r for r in json.loads((root/'imports/source-inventory.json').read_text())}
key='Unidad de odontología::6'
batch=ImportBatch.objects.create(digest=catalog['source_sha256'],filename='source-fixture-for-isolated-test.docx')
CatalogAccess.objects.create(institution=institution,batch=batch,granted_by=operator)
for ref in catalog['questions'][key]['references']:
    record=records[ref['stable_id']]
    source=SourceRecord.objects.create(batch=batch,**{k:record[k] for k in ('stable_id','locator','text','section','kind','links')})
    if source.stable_id==key:
        question=Question.objects.create(stable_id=key)
        QuestionVersion.objects.create(question=question,source=source,version=1)

# Separate institution and roles: this matrix fixture cannot alter the administration scenario.
from core.models import Campus,Site,Service,RoleAssignment,QuestionnaireInstance,Answer,AnswerRevision,EvidenceDocument,EvidenceReview,NormativeEntry
from core.compliance_catalog import table_entries
from django.core.files.base import ContentFile
import hashlib
ci=Institution.objects.create(name='Institución sintética de cumplimiento')
cs=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=ci,name='Campus matriz'),name='Sede matriz'),name='Servicio matriz sintética',confirmed=True)
ca=User.objects.create_user('e2e_matrix_author',password=os.environ['E2E_PASSWORD']);cr=User.objects.create_user('e2e_matrix_reviewer',password=os.environ['E2E_PASSWORD'])
for person,role in [(ca,'manager'),(cr,'compliance')]:RoleAssignment.objects.create(user=person,service=cs,role=role,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=30),approved_by=operator)
CatalogAccess.objects.create(institution=ci,batch=batch,granted_by=operator)
for original in records.values():
    if original['kind']=='regulation' and original['text']=='N01' or original['kind']=='annex' and original['text'].startswith('C01 '):
        SourceRecord.objects.get_or_create(batch=batch,stable_id=original['stable_id'],defaults={k:original[k] for k in ('locator','text','section','kind','links')})
entry=table_entries(root/'Plan_Trabajo_Escuela_Salud_Modelo.docx')[0]
NormativeEntry.objects.create(source=SourceRecord.objects.get(batch=batch,kind='regulation',text='N01'),**entry)
from core.publication import save_help,review_help,publish,HELP_FIELDS
from core.workflow import save_answer,transition
instance=QuestionnaireInstance.objects.create(service=cs,question_version=QuestionVersion.objects.get(question__stable_id=key))
help_draft=save_help(ca,instance.pk,0,{k:'Guía sintética del ensayo de matriz.' for k in HELP_FIELDS})
help_draft=review_help(cr,instance.pk,help_draft.etag,'approved','Revisión sintética de ayuda')
publish(cr,instance.pk,help_draft.etag)
answer=Answer.objects.get(instance=instance)
answer=save_answer(ca,answer.pk,answer.etag,'Declaración sintética para matriz; no son hechos institucionales.','known')
answer=transition(ca,answer.pk,answer.etag,'submitted','')
answer=transition(cr,answer.pk,answer.etag,'validated','Revisión sintética de respuesta')
revision=answer.revisions.get(version=answer.version)
raw=b'Synthetic matrix evidence only.'
doc=EvidenceDocument(answer=answer,revision=revision,original_name='Evidencia sintética matriz.txt',sha256=hashlib.sha256(raw).hexdigest(),uploader=ca,format='txt',state='accepted')
doc.file.save('matrix-synthetic.txt',ContentFile(raw),save=True)
EvidenceReview.objects.create(document=doc,reviewer=cr,decision='accepted',rationale='Revisión sintética',valid_until=timezone.localdate()+timedelta(days=30))

# Task/plan scenario isolated from both earlier institutions.
ti=Institution.objects.create(name='Institución sintética de seguimiento')
ts=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=ti,name='Campus seguimiento'),name='Sede seguimiento'),name='Servicio seguimiento sintético',confirmed=True)
tm=User.objects.create_user('e2e_task_manager',password=os.environ['E2E_PASSWORD']);td=User.objects.create_user('e2e_task_director',password=os.environ['E2E_PASSWORD'])
for person,role in [(tm,'manager'),(td,'director')]:RoleAssignment.objects.create(user=person,service=ts,role=role,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),approved_by=operator)
InstitutionMandate.objects.create(institution=ti,user=td,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),rationale='Mandato sintético exclusivo del ensayo de seguimiento')
CatalogAccess.objects.create(institution=ti,batch=batch,granted_by=operator)

User.objects.create_user('e2e_mfa',password=os.environ['E2E_PASSWORD'])

# Independent interview scenario; no existing institutional answers are reused.
iservice=Service.objects.create(site=cs.site,name='Servicio entrevista sintética',confirmed=True)
iu=User.objects.create_user('e2e_interview',password=os.environ['E2E_PASSWORD'])
for person,role in [(iu,'contributor'),(cr,'manager')]:RoleAssignment.objects.create(user=person,service=iservice,role=role,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),approved_by=operator)
ii=QuestionnaireInstance.objects.create(service=iservice,question_version=QuestionVersion.objects.get(question__stable_id=key))
guide={k:'Guía sintética de entrevista.' for k in HELP_FIELDS};guide['steps']='1. Indique responsable.\n2. Indique sede.\n3. Indique excepción.'
ih=save_help(iu,ii.pk,0,guide);ih=review_help(cr,ii.pk,ih.etag,'approved','Revisión sintética de entrevista');publish(cr,ii.pk,ih.etag)

# Institution exclusively for capacity planning; do not expand other test accounts' mandates.
capacity_institution=Institution.objects.create(name='Institución sintética de capacidad')
capacity_service=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=capacity_institution,name='Campus capacidad'),name='Sede capacidad'),name='Servicio capacidad sintético',confirmed=True)
capacity_person=User.objects.create_user('e2e_capacity_worker',password=os.environ['E2E_PASSWORD'])
RoleAssignment.objects.create(service=capacity_service,user=capacity_person,role='contributor',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),approved_by=operator)
for username in ['e2e_capacity_proposer','e2e_capacity_reviewer']:
    capacity_director=User.objects.create_user(username,password=os.environ['E2E_PASSWORD'])
    InstitutionMandate.objects.create(institution=capacity_institution,user=capacity_director,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),rationale='Mandato sintético exclusivo para capacidad')

# Independent institution for substitution tests; no broader privileges in other fixtures.
coverage_institution=Institution.objects.create(name='Institución suplencias sintéticas')
coverage_service=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=coverage_institution,name='Campus suplencias'),name='Sede suplencias'),name='Servicio suplencias',confirmed=True)
coverage_director=User.objects.create_user('e2e_coverage_director',password=os.environ['E2E_PASSWORD'])
coverage_holder=User.objects.create_user('e2e_coverage_holder',password=os.environ['E2E_PASSWORD'])
coverage_sub=User.objects.create_user('e2e_coverage_sub',password=os.environ['E2E_PASSWORD'])
for person in [coverage_director,coverage_holder,coverage_sub]:InstitutionMember.objects.create(institution=coverage_institution,user=person)
InstitutionMandate.objects.create(institution=coverage_institution,user=coverage_director,approved_by=operator,starts=timezone.localdate()-timedelta(days=3),ends=timezone.localdate()+timedelta(days=60),rationale='Mandato sintético para suplencias')
RoleAssignment.objects.create(service=coverage_service,user=coverage_holder,role='contributor',starts=timezone.localdate()-timedelta(days=3),ends=timezone.localdate()+timedelta(days=60),approved_by=coverage_director)

# Complete task coverage scenario, independent of appointment-form fixtures.
from core.models import Task,WorkPlan
from core.tracking import workflow as task_workflow
from django.core.management import call_command
from unittest.mock import patch
from datetime import date
cti=Institution.objects.create(name='Institución integración de suplencias')
cts=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=cti,name='Campus cobertura'),name='Sede cobertura'),name='Servicio cobertura de tareas',confirmed=True)
cth=User.objects.create_user('e2e_covered_owner',password=os.environ['E2E_PASSWORD'])
ctu=User.objects.create_user('e2e_task_coverage',password=os.environ['E2E_PASSWORD'])
ctr=RoleAssignment.objects.create(user=cth,service=cts,role='contributor',starts=timezone.localdate()-timedelta(days=3),ends=timezone.localdate()+timedelta(days=60),approved_by=operator)
RoleAssignment.objects.create(user=ctu,service=cts,role='contributor',substitutes=ctr,starts=ctr.starts,ends=ctr.ends,approved_by=operator)
Task.objects.create(service=cts,owner=cth,title='Tarea sintética cubierta',deduplication_key='browser-covered-task',committed=True,starts=date(2026,10,1),due=date(2026,10,5))
WorkPlan.objects.create(institution=cti,weekdays=list(range(5)),holidays=[],confirmed_by=operator,etag=1)
with patch('core.tracking.workflow.today',return_value=date(2026,10,15)):task_workflow.reminders()
call_command('worker')

# Separate correction fixture; synthetic plan-day entry, never institutional data.
from core.models import TimeEntry
import uuid
hours_institution=Institution.objects.create(name='Institución corrección de horas')
hours_service=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=hours_institution,name='Campus horas'),name='Sede horas'),name='Servicio corrección de horas',confirmed=True)
hours_user=User.objects.create_user('e2e_time_author',password=os.environ['E2E_PASSWORD'])
RoleAssignment.objects.create(user=hours_user,service=hours_service,role='contributor',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=60),approved_by=operator)
hours_task=Task.objects.create(service=hours_service,owner=hours_user,title='Tarea sintética de horas',deduplication_key='browser-time-correction',committed=True,starts=date(2026,10,1),due=date(2026,10,5))
TimeEntry.objects.create(task=hours_task,actor=hours_user,day=date(2026,10,1),minutes=60,note='Registro original sintético',client_key=uuid.uuid4())

# Approved planning projections for the independent hours service.
from core.models import CapacityDay,CapacityAllocation
hours_task.estimated_minutes=120;hours_task.save()
WorkPlan.objects.create(institution=hours_institution,weekdays=[0,1,2,3,4],holidays=[],confirmed_by=operator,etag=1)
hours_day=CapacityDay.objects.create(institution=hours_institution,person=hours_user,day=date(2026,10,1),minutes=60,unavailable_minutes=30,confirmed=True,etag=1)
CapacityAllocation.objects.create(capacity=hours_day,service=hours_service,minutes=30)

# Reservation approval scenario independent of other browser flows.
from core.models import PlanningPolicy
reservation_i=Institution.objects.create(name='Institución reservas sintéticas')
reservation_s=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=reservation_i,name='Campus reservas'),name='Sede reservas'),name='Servicio reservas',confirmed=True)
reservation_manager=User.objects.create_user('e2e_reservation_manager',password=os.environ['E2E_PASSWORD'])
reservation_director=User.objects.create_user('e2e_reservation_director',password=os.environ['E2E_PASSWORD'])
for u,role in [(reservation_manager,'manager'),(reservation_director,'director')]:RoleAssignment.objects.create(user=u,service=reservation_s,role=role,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),approved_by=operator)
InstitutionMandate.objects.create(institution=reservation_i,user=reservation_director,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),rationale='Synthetic reservation mandate')
PlanningPolicy.objects.create(institution=reservation_i,enforced=True,base_minutes=1000,reserve_minutes=200)
WorkPlan.objects.create(institution=reservation_i,weekdays=[0,1,2,3,4],holidays=[],confirmed_by=operator,etag=1)
reservation_day=CapacityDay.objects.create(institution=reservation_i,person=reservation_manager,day=date(2026,10,5),confirmed=True,minutes=120,etag=1)
CapacityAllocation.objects.create(capacity=reservation_day,service=reservation_s,minutes=120)
reservation_fields={'title':'Tarea con reserva sintética','owner':reservation_manager.pk,'substitute':None,'coordinator':None,'starts':date(2026,10,5),'due':date(2026,10,5),'priority':'normal','estimated_minutes':120,'acceptance_criteria':'Synthetic acceptance','predecessors':[],'reservation_plan':[{'person':reservation_manager.pk,'day':'2026-10-05','minutes':120}],'budget_bucket':'reserve'}
reservation_task=task_workflow.create(reservation_manager,reservation_s,reservation_fields)
task_workflow.propose(reservation_manager,reservation_task.pk,reservation_task.etag,reservation_fields,'Synthetic proposed reservation')

# Dedicated source upgrade; original global catalog remains unchanged.
from core.models import ImportBatch,SourceRecord,Question,QuestionVersion,QuestionnaireInstance,InstitutionMember
source_batch=ImportBatch.objects.create(digest='e'*64,filename='synthetic-source-upgrade')
CatalogAccess.objects.create(institution=reservation_i,batch=source_batch,granted_by=operator)
source_question=Question.objects.create(stable_id='SOURCE-UPGRADE-SYNTHETIC')
source_versions=[]
for version in [1,2]:
    record=SourceRecord.objects.create(batch=source_batch,stable_id=f'synthetic-v{version}',locator=f'paragraph {version}',section='Synthetic source',kind='question_original',text=f'Pregunta sintética fuente {version}')
    source_versions.append(QuestionVersion.objects.create(question=source_question,source=record,version=version))
QuestionnaireInstance.objects.create(service=reservation_s,question_version=source_versions[0])
InstitutionMandate.objects.create(institution=reservation_i,user=reservation_manager,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),rationale='Synthetic source proposer mandate')
for user in [reservation_manager,reservation_director]:InstitutionMember.objects.get_or_create(institution=reservation_i,user=user)

# Administrative corrections use their own service and accounts, never live data.
admin_hours_service=Service.objects.create(site=hours_service.site,name='Servicio ajustes administrativos',confirmed=True)
admin_hours_author=User.objects.create_user('e2e_admin_hours_author',password=os.environ['E2E_PASSWORD'])
for username in ['e2e_admin_hours_requester','e2e_admin_hours_reviewer']:
    person=User.objects.create_user(username,password=os.environ['E2E_PASSWORD'])
    RoleAssignment.objects.create(user=person,service=admin_hours_service,role='director',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=60),approved_by=operator)
RoleAssignment.objects.create(user=admin_hours_author,service=admin_hours_service,role='contributor',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=60),approved_by=operator)
admin_hours_task=Task.objects.create(service=admin_hours_service,owner=admin_hours_author,title='Tarea de ajuste administrativo',deduplication_key='browser-admin-time-correction',committed=True,starts=date(2026,10,1),due=date(2026,10,5))
TimeEntry.objects.create(task=admin_hours_task,actor=admin_hours_author,day=date(2026,10,1),minutes=60,note='Registro administrativo sintético',client_key=uuid.uuid4())

# Isolated MFA recovery fixture; credentials exist only inside the disposable workdir.
from core.models import MFADevice
from core.mfa import cipher,recovery_codes
import pyotp
recovery_institution=Institution.objects.create(name='Institución recuperación sintética')
recovery_fixture={}
recovery_people=[]
for name in ['e2e_recovery_requester','e2e_recovery_reviewer','e2e_recovery_target']:
    person=User.objects.create_user(name,password=os.environ['E2E_PASSWORD'])
    InstitutionMember.objects.create(user=person,institution=recovery_institution)
    device=MFADevice(user=person,enabled=True,generation=1,secret=cipher().encrypt(pyotp.random_base32().encode()).decode())
    recovery_fixture[name]=recovery_codes(device)[0];device.save();recovery_people.append(person)
for person in recovery_people[:2]:
    InstitutionMandate.objects.create(user=person,institution=recovery_institution,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=30),rationale='Synthetic recovery mandate')
from pathlib import Path
import json
Path(os.environ['E2E_WORKDIR'],'exceptional-recovery.json').write_text(json.dumps(recovery_fixture))

# Large synthetic archive for cursor navigation; no historical institutional claim.
from copy import deepcopy
from datetime import datetime,time,timezone as dtz
from core.models import SavedReport,ReportSchedule,ScheduledReportRun
from core.reports import snapshot
from core.saved_reports import digest
from rest_framework.renderers import JSONRenderer
archive_institution=Institution.objects.create(name='Institución archivo sintético')
archive_service=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=archive_institution,name='Campus archivo'),name='Sede archivo'),name='Servicio archivo sintético',confirmed=True)
archive_author=User.objects.create_user('e2e_archive_author',password=os.environ['E2E_PASSWORD'])
archive_reviewer=User.objects.create_user('e2e_archive_director',password=os.environ['E2E_PASSWORD'])
for person,role in [(archive_author,'manager'),(archive_reviewer,'director')]:
    RoleAssignment.objects.create(user=person,service=archive_service,role=role,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=180),approved_by=operator)
archive_start=date(2026,9,21)
archive_content=json.loads(JSONRenderer().render(snapshot(archive_author,archive_service.pk,archive_start,timezone.now())))
archive_reports=SavedReport.objects.bulk_create([SavedReport(service=archive_service,created_by=archive_author,client_key=uuid.uuid4(),start=archive_start,content=archive_content,content_hash=digest(archive_content),state='approved',reviewed_by=archive_reviewer,rationale='Revisión sintética del archivo',reviewed_at=timezone.now()) for _ in range(73)])
archive_schedule=ReportSchedule.objects.create(service=archive_service,authorized_by=archive_reviewer,first_period=date(2026,10,5),enabled=False,rationale='Programación sintética pausada')
archive_runs=[]
for index in range(55):
    period=date(2026,10,5)+timedelta(weeks=index)
    content=deepcopy(archive_content);content['period']['start']=str(period);content['period']['end_exclusive']=str(period+timedelta(days=7))
    report=SavedReport.objects.create(service=archive_service,created_by=archive_author,client_key=uuid.uuid4(),start=period,content=content,content_hash=digest(content))
    archive_runs.append(ScheduledReportRun.objects.create(schedule=archive_schedule,period=period,schedule_version=1,report=report,generation_mode='backfill' if index%2 else 'scheduled',rationale='Archivo generado únicamente para probar navegación'))
archive_source=SavedReport.objects.create(service=archive_service,created_by=archive_author,client_key=uuid.uuid4(),start=archive_start,content=archive_content,content_hash=digest(archive_content),state='approved',reviewed_by=archive_reviewer,rationale='Fuente sintética',reviewed_at=timezone.now())
Path(os.environ['E2E_WORKDIR'],'report-history.json').write_text(json.dumps({'oldest':archive_reports[0].pk,'source':archive_source.pk,'oldest_run_report':archive_runs[0].report_id}))

# Academic core: accounts and service appointments only; UI creates the academic records.
ai=Institution.objects.create(name='Escuela académica sintética')
asite=Site.objects.create(campus=Campus.objects.create(institution=ai,name='Campus académico'),name='Sede académica')
ad=User.objects.create_user('e2e_academic_director',password=os.environ['E2E_PASSWORD'],first_name='Directora académica')
auser=User.objects.create_user('e2e_academic_student',password=os.environ['E2E_PASSWORD'],first_name='Alumna sintética')
asupervisor=User.objects.create_user('e2e_academic_supervisor',password=os.environ['E2E_PASSWORD'],first_name='Supervisor sintético')
for person in (ad,auser,asupervisor):InstitutionMember.objects.create(institution=ai,user=person)
InstitutionMandate.objects.create(institution=ai,user=ad,approved_by=operator,starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate()+timedelta(days=60),rationale='Mandato académico sintético')
for name in ('Odontología académica','Nutrición académica'):
    s=Service.objects.create(site=asite,name=name,confirmed=True)
    RoleAssignment.objects.create(user=asupervisor,service=s,role='clinical',starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate()+timedelta(days=60),approved_by=ad)

# Isolated ended academic cycle for rubric/evaluation/report acceptance.
from core.models import AcademicCycle,AcademicStudent,AcademicPlacement,AcademicPractice
from core.academic import event as academic_event
aci=Institution.objects.create(name='Escuela sintética de cierre académico')
acsite=Site.objects.create(campus=Campus.objects.create(institution=aci,name='Campus cierre'),name='Sede cierre')
acd=User.objects.create_user('e2e_closure_director',password=os.environ['E2E_PASSWORD'],first_name='Directora cierre')
acs=User.objects.create_user('e2e_closure_supervisor',password=os.environ['E2E_PASSWORD'],first_name='Supervisor cierre')
acu=User.objects.create_user('e2e_closure_student',password=os.environ['E2E_PASSWORD'],first_name='Alumna cierre uno')
acu2=User.objects.create_user('e2e_closure_student_two',password=os.environ['E2E_PASSWORD'],first_name='Alumna cierre dos')
for person in (acd,acs,acu,acu2):InstitutionMember.objects.create(institution=aci,user=person)
InstitutionMandate.objects.create(institution=aci,user=acd,approved_by=operator,starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate()+timedelta(days=60),rationale='Mandato de cierre sintético')
acc=AcademicCycle.objects.create(institution=aci,code='CIERRE-2026',name='Ciclo cierre sintético',starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate(),created_by=acd)
import uuid
for index,(name,user) in enumerate([('Odontología cierre',acu),('Fisioterapia cierre',acu2)],1):
    s=Service.objects.create(site=acsite,name=name,confirmed=True)
    RoleAssignment.objects.create(user=acs,service=s,role='clinical',starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate()+timedelta(days=60),approved_by=acd)
    student=AcademicStudent.objects.create(institution=aci,user=user,enrollment=f'CIERRE-{index}',program='Salud sintética')
    placement=AcademicPlacement.objects.create(student=student,cycle=acc,service=s,supervisor=acs,group='GC',starts=acc.starts,ends=acc.ends,target_minutes=60,created_by=acd)
    pr=AcademicPractice.objects.create(placement=placement,client_key=uuid.uuid4(),title=f'Práctica de cierre {index}',performed_on=acc.ends,minutes=60,competency='Comunicación sintética',evidence_reference=f'Bitácora sintética {index}',status='validated')
    academic_event(pr,acs,'validate','Validación sintética para la prueba de cierre.')

# Independent peer schools and a one-way academic consultation grant.
from core.models import School,SchoolMember,SchoolMandate,SchoolAcademicGrant,AcademicCycleReport
from core.academic_assessment import build_snapshot as school_snapshot,digest as school_digest
si=Institution.objects.create(name='Universidad de escuelas sintéticas')
ssite=Site.objects.create(campus=Campus.objects.create(institution=si,name='Campus escuelas'),name='Sede escuelas')
health_school=School.objects.create(institution=si,code='salud',name='Escuela de Salud de prueba')
dental_school=School.objects.create(institution=si,code='odontologia',name='Escuela de Odontología de prueba')
hd=User.objects.create_user('e2e_health_director',password=os.environ['E2E_PASSWORD'],first_name='Dirección Salud prueba')
dd=User.objects.create_user('e2e_dental_director',password=os.environ['E2E_PASSWORD'],first_name='Dirección Odontología prueba')
ds=User.objects.create_user('e2e_dental_supervisor',password=os.environ['E2E_PASSWORD'],first_name='Supervisor dental prueba')
du=User.objects.create_user('e2e_dental_student',password=os.environ['E2E_PASSWORD'],first_name='Alumno dental prueba')
for person,school in ((hd,health_school),(dd,dental_school),(ds,dental_school),(du,dental_school)):
    InstitutionMember.objects.create(institution=si,user=person);SchoolMember.objects.create(school=school,user=person)
for director,school in ((hd,health_school),(dd,dental_school)):
    SchoolMandate.objects.create(school=school,user=director,approved_by=operator,starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate()+timedelta(days=60),rationale='Nombramiento escolar sintético')
svc=Service.objects.create(site=ssite,school=dental_school,name='Clínica Dental de prueba',confirmed=True)
RoleAssignment.objects.create(user=ds,service=svc,role='clinical',starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate()+timedelta(days=60),approved_by=dd)
dcycle=AcademicCycle.objects.create(institution=si,school=dental_school,code='DENTAL-2026',name='Ciclo dental de prueba',starts=timezone.localdate()-timedelta(days=20),ends=timezone.localdate(),created_by=dd)
dstudent=AcademicStudent.objects.create(institution=si,school=dental_school,user=du,enrollment='DENT-001',program='Cirujano Dentista sintético')
dplacement=AcademicPlacement.objects.create(student=dstudent,cycle=dcycle,service=svc,supervisor=ds,group='D1',starts=dcycle.starts,ends=dcycle.ends,created_by=dd)
AcademicPractice.objects.create(placement=dplacement,client_key=uuid.uuid4(),title='Práctica dental supervisada de prueba',performed_on=dcycle.ends,minutes=90,competency='Comunicación',evidence_reference='Bitácora sintética dental',status='validated')
cut=school_snapshot(dcycle)
AcademicCycleReport.objects.create(cycle=dcycle,sequence=1,source_revision=dcycle.revision,snapshot=cut,digest=school_digest(cut),client_key=uuid.uuid4(),created_by=dd)
SchoolAcademicGrant.objects.create(school=dental_school,reader_school=health_school,approved_by=dd,starts=dcycle.starts,ends=timezone.localdate()+timedelta(days=60),rationale='Consulta académica autorizada de Salud')

# Institutional superuser with the same explicit mandate shape as the demo owner.
home_admin=User.objects.create_superuser("e2e_school_admin",password=os.environ["E2E_PASSWORD"])
InstitutionMember.objects.create(institution=si,user=home_admin)
InstitutionMandate.objects.create(user=home_admin,institution=si,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=60),rationale="Mandato institucional sintético para panel académico")

if os.environ.get('E2E_INSTITUTIONAL_CATALOG')=='1':
    from django.core.management import call_command
    import io
    call_command('import_institutional_services',institution=si.pk,actor=home_admin.username,apply=True,stdout=io.StringIO())

# Only the guarded disposable cluster receives portal acceptance fixtures.
if os.environ.get('E2E_PORTAL_PILOT')=='1':
    from core.models import School,Campus,Site,Service,RoleAssignment
    campus=Campus.objects.create(institution=institution,name='Campus del ensayo de portal')
    site=Site.objects.create(campus=campus,name='Sede del ensayo de portal')
    for code,slug in [('salud','psicologia'),('odontologia','odontologia')]:
        school=School.objects.get_or_create(institution=institution,code=code,defaults={'name':code})[0]
        service=Service.objects.create(site=site,school=school,name='Servicio de ensayo '+slug,public_slug=slug,confirmed=True)
        RoleAssignment.objects.create(service=service,user=director,role='manager',starts=timezone.localdate()-timedelta(days=1),ends=timezone.localdate()+timedelta(days=30),approved_by=operator)
