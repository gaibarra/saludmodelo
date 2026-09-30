"""One-time synthetic demonstration; refuses every other database and existing data."""
import os,sys,json,secrets,io,uuid
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,'/app/backend')
import django
django.setup()
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from core.models import Institution,InstitutionMember,InstitutionMandate,Campus,Site,Service,RoleAssignment,ImportBatch,CatalogAccess,QuestionVersion,QuestionnaireInstance,Answer,MFADevice,SecurityEvent,WorkPlan,WorkCalendarRevision
from core.publication import save_help,review_help,publish
from core.workflow import save_answer,transition
from core.help_drafts import build
from core.mfa import cipher,recovery_codes
from core.tracking import workflow as tasks
from core import capacity
import pyotp
if os.getenv('SALUD_DEMO')!='odontologia-sintetica' or settings.DATABASES['default']['NAME']!='salud_modelo_demo' or settings.DATABASES['default']['HOST']!='/pgsocket':
    raise SystemExit('Carga bloqueada fuera del entorno de demostración.')
User=get_user_model()
private=Path('/demo-private')
credentials=private/'accesos-demo.json'
if User.objects.exists() or Institution.objects.exists() or credentials.exists():
    raise SystemExit('La demostración ya tiene datos: no se sobrescriben cuentas ni actividad.')
reason='SIMULACIÓN DEMO: decisión ficticia para mostrar el funcionamiento; sin validez institucional.'
accounts=[]
with transaction.atomic():
    operator=User.objects.create_superuser('demo_operador',password=None)
    inst=Institution.objects.create(name='Escuela de Salud Modelo — DEMOSTRACIÓN FICTICIA')
    service=Service.objects.create(site=Site.objects.create(campus=Campus.objects.create(institution=inst,name='Campus de demostración'),name='Sede de demostración'),name='Odontología · DEMO',confirmed=True)
    users={}
    for name,role in [('direccion','director'),('odontologia','manager'),('revision','clinical'),('colaborador','contributor')]:
        password=secrets.token_urlsafe(20)
        user=User.objects.create_user('demo_'+name,password=password,first_name='Demo',last_name=name.capitalize())
        users[name]=user
        InstitutionMember.objects.create(institution=inst,user=user)
        RoleAssignment.objects.create(user=user,service=service,role=role,starts=timezone.localdate()-timedelta(days=1),ends=date(2026,12,31),approved_by=operator,rationale=reason)
        secret=pyotp.random_base32()
        device=MFADevice(user=user,secret=cipher().encrypt(secret.encode()).decode(),enabled=True,generation=1)
        codes=recovery_codes(device);device.save()
        SecurityEvent.objects.create(user=user,action='demo.synthetic_mfa_bootstrap')
        accounts.append({'username':user.username,'role':role,'password':password,'totp_secret':secret,'recovery_codes':codes})
    director=users['direccion'];manager=users['odontologia'];reviewer=users['revision']
    for user in [director,reviewer]:
        InstitutionMandate.objects.create(institution=inst,user=user,approved_by=operator,starts=timezone.localdate()-timedelta(days=1),ends=date(2026,12,31),rationale=reason)
    call_command('import_plan','/app/Plan_Trabajo_Escuela_Salud_Modelo.docx',approve_sha='72108682be8b63f71c15d70d8d43fa370a033f04fd8af4526b4acf10b0e236be',actor=operator.username,stdout=io.StringIO())
    CatalogAccess.objects.create(institution=inst,batch=ImportBatch.objects.get(digest='72108682be8b63f71c15d70d8d43fa370a033f04fd8af4526b4acf10b0e236be'),granted_by=operator)
    instances=[]
    for number in [1,3,5,6,11,12]:
        version=QuestionVersion.objects.get(question__stable_id=f'Unidad de odontología::{number}')
        instance=QuestionnaireInstance.objects.create(service=service,question_version=version)
        proposal=build(instance)
        content={key:'DEMOSTRACIÓN FICTICIA; requiere revisión institucional.\n'+value for key,value in proposal['content'].items()}
        instance=save_help(manager,instance.pk,0,content,proposal['digest'])
        instance=review_help(reviewer,instance.pk,instance.etag,'approved',reason)
        instances.append(instance)
    for instance in instances:publish(reviewer,instance.pk,instance.etag)
    examples=[
        'EJEMPLO FICTICIO: recepción busca el expediente antes de abrir uno nuevo, compara dos datos de identificación y consulta las coincidencias al responsable. Falta acordar cómo resolver homónimos.',
        'EJEMPLO FICTICIO: el estudiante captura antecedentes, alergias y medicamentos; el docente revisa exploración y diagnóstico antes de validar. Confirmar con el servicio.',
        'EJEMPLO FICTICIO: falta acordar qué procedimientos requieren consentimiento específico y cómo comprobar la representación de un menor; consultar en la reunión del piloto.',
    ]
    for index,text in enumerate(examples):
        answer=Answer.objects.get(instance=instances[index]);answer=save_answer(manager,answer.pk,answer.etag,text,'unknown' if index==2 else 'known')
        if index<2:answer=transition(manager,answer.pk,answer.etag,'submitted','')
        if index==0:transition(reviewer,answer.pk,answer.etag,'validated',reason)
    plan=WorkPlan.objects.create(institution=inst,weekdays=[0,1,2,3,4],holidays=[],confirmed_by=director,confirmed_at=timezone.now(),rationale=reason,etag=1)
    WorkCalendarRevision.objects.create(plan=plan,version=1,actor=director,weekdays=plan.weekdays,holidays=[],rationale=reason)
    for offset in [0,1,4,5,6]:
        day=date(2026,10,1)+timedelta(days=offset)
        unavailable=120 if offset==4 else 0
        change=capacity.propose(director,inst.pk,{'person':manager.pk,'day':day,'version':0,'minutes':240,'unavailable_minutes':unavailable,'allocations':[{'service':service.pk,'minutes':240-unavailable}],'rationale':reason,'client_key':uuid.uuid4()})
        capacity.review(reviewer,change.pk,{'approve':True,'rationale':reason})
    for index,(title,start,end,minutes) in enumerate([
        ('DEMO: acordar recepción y responsable de primera atención','2026-10-01','2026-10-02',120),
        ('DEMO: definir suplencia por ausencia del docente','2026-10-05','2026-10-06',90),
        ('DEMO: revisar consentimiento y atención de menores','2026-10-06','2026-10-07',120),
    ]):
        data={'title':title,'owner':manager.pk,'substitute':users['colaborador'].pk,'coordinator':None,'starts':start,'due':end,'priority':'high' if index==1 else 'normal','estimated_minutes':minutes,'acceptance_criteria':'DEMOSTRACIÓN: describir responsable, pasos y excepción; revisión por otra cuenta. No representa aceptación institucional.','predecessors':[],'reservation_plan':[],'budget_bucket':'base'}
        task=tasks.create(manager,service,data)
        change=tasks.propose(manager,task.pk,task.etag,data,reason)
        if index<2:tasks.decide(director,change.pk,True,reason)
    payload={'url':'https://plansaludmodelo.online','service_id':service.pk,'institution_id':inst.pk,'accounts':accounts}
    fd=os.open(credentials,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
print('Demostración inicializada: 4 cuentas, 6 preguntas originales, respuestas y planificación ficticias. Credenciales en archivo privado.')
