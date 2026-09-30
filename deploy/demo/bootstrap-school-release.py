"""Authorized 0.35 account/ownership bootstrap. Configuration enters via stdin only.
No email delivery, no MFA enrollment/reset, no patient intake, no reset of existing users.
"""
import os,sys,json
sys.path.insert(0,os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from datetime import date,timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.test import APIClient
from core.models import (Institution,InstitutionMember,InstitutionMandate,School,SchoolMember,SchoolMandate,SchoolAcademicGrant,Service,AcademicCycle,AcademicStudent,AcademicPlacement,AcademicPractice,AcademicCycleReport,GovernanceEvent,MFADevice,RoleAssignment)
from core.governance import record,managed_institutions,managed_services
from core.school_access import managed_schools,shared_schools
from core.access import scopes
from core.mfa import required

cfg=json.load(sys.stdin)
db=settings.DATABASES['default']
assert db['NAME'] in ('salud_modelo_demo','salud_school_rehearsal'),'Unexpected database'
assert db['HOST']=='/pgsocket' or str(db['HOST']).startswith('/tmp/salud-'),'Private database socket required'
assert not settings.PATIENT_PORTAL_ENABLED and not settings.AI_EXTERNAL_ENABLED,'Demo flags required'
assert settings.MFA_REQUIRE_PRIVILEGED,'MFA must remain enabled'
assert set(a['username'] for a in cfg['accounts'])=={'amiraleon@modelo.edu.mx','mariososa@modelo.edu.mx','gibarra@modelo.edu.mx'}
assert set(a['role'] for a in cfg['accounts'])=={'salud','odontologia','institution'}
start=date.fromisoformat(cfg['starts']);end=date.fromisoformat(cfg['ends']);assert start<=timezone.localdate()<=end
key=cfg['release_key'];users={}
with transaction.atomic():
    inst=Institution.objects.select_for_update().get(pk=cfg['institution'])
    assert inst.name in (cfg['previous_institution_name'],cfg['institution_name']),'Institution identity changed'
    operator=get_user_model().objects.get(username='demo_operador',is_active=True,is_superuser=True)
    previous=GovernanceEvent.objects.filter(action='release.schools.configured',object_id=key).exists()
    if not previous:
        assert set(Service.objects.filter(site__campus__institution=inst).values_list('id',flat=True))==set(cfg['dental_services']),'Unexpected existing services'
        assert not AcademicCycle.objects.filter(institution=inst).exists(),'Review existing academic records before classification'
        assert not AcademicStudent.objects.filter(institution=inst).exists(),'Review existing students before classification'
        for a in cfg['accounts']:
            if get_user_model().objects.filter(Q(username__iexact=a['username'])|Q(email__iexact=a['username'])).exists():raise RuntimeError('Account collision; refusing to reset an existing account')
            u=get_user_model().objects.create_user(username=a['username'],email=a['username'],first_name=a['first_name'],last_name=a['last_name'],password=a['password'],is_staff=a['role']=='institution',is_superuser=a['role']=='institution')
            InstitutionMember.objects.create(institution=inst,user=u);users[a['role']]=u
            record(operator,inst.pk,'release.account.created',u.pk,'Alta solicitada por el usuario; credencial inicial explícita, MFA conservado; '+key)
        owner=users['institution']
        InstitutionMandate.objects.create(institution=inst,user=owner,approved_by=operator,starts=start,ends=end,rationale=cfg['rationale'])
        health=School.objects.create(institution=inst,code='salud',name='Escuela de Salud')
        dental=School.objects.create(institution=inst,code='odontologia',name='Escuela de Odontología')
        for role,school in [('salud',health),('odontologia',dental)]:
            SchoolMember.objects.create(school=school,user=users[role])
            mandate=SchoolMandate.objects.create(school=school,user=users[role],approved_by=owner,starts=start,ends=end,rationale=cfg['rationale'])
            record(owner,inst.pk,'school.direction.granted',mandate.pk,cfg['rationale'])
        for service in Service.objects.select_for_update().filter(pk__in=cfg['dental_services']):
            assert service.school_id is None,'Service already classified'
            service.school=dental;service.save(update_fields=['school'])
            record(owner,inst.pk,'school.ownership.assigned',f'services:{service.pk}',cfg['rationale'],service)
        for username in ('demo_odontologia','demo_revision','demo_colaborador'):
            SchoolMember.objects.create(school=dental,user=get_user_model().objects.get(username=username))
        legacy=get_user_model().objects.get(username='demo_direccion')
        SchoolMember.objects.create(school=health,user=legacy)
        SchoolMandate.objects.create(school=health,user=legacy,approved_by=owner,starts=start,ends=end,rationale='Cuenta ficticia de Salud limitada a su escuela; '+cfg['rationale'])
        for mandate in InstitutionMandate.objects.select_for_update().filter(institution=inst,user__username__in=['demo_direccion','demo_revision']):
            assert mandate.starts<start,'Cannot expire future mandate implicitly'
            original=str(mandate.ends);mandate.ends=start-timedelta(days=1);mandate.save(update_fields=['ends'])
            record(owner,inst.pk,'institution.legacy_mandate.expired',mandate.pk,'Separación de escuelas; fecha anterior '+original+'; roles de servicio conservados')
        for role in RoleAssignment.objects.select_for_update().filter(user=legacy,service_id__in=cfg['dental_services'],revoked_at__isnull=True):
            role.revoked_at=timezone.now();role.revoked_by=owner;role.revocation_reason='Cuenta ficticia de Dirección de Salud: sin administración de Odontología';role.save(update_fields=['revoked_at','revoked_by','revocation_reason'])
            record(owner,inst.pk,'assignment.revoked',role.pk,role.revocation_reason,role.service)
        grant=SchoolAcademicGrant.objects.create(school=dental,reader_school=health,approved_by=owner,starts=start,ends=end,rationale=cfg['rationale'])
        record(owner,inst.pk,'school.academic.granted',grant.pk,cfg['rationale'])
        old_name=inst.name;inst.name=cfg['institution_name'];inst.save(update_fields=['name'])
        record(owner,inst.pk,'institution.label.updated',inst.pk,'Universidad como entidad superior; nombre anterior: '+old_name)
        record(owner,inst.pk,'release.schools.configured',key,cfg['rationale'])
    else:
        users={a['role']:get_user_model().objects.get(username=a['username'],email=a['username'],is_active=True) for a in cfg['accounts']}
        health=School.objects.get(institution=inst,code='salud');dental=School.objects.get(institution=inst,code='odontologia')
    assert list(managed_institutions(users['salud']))==[] and list(managed_institutions(users['odontologia']))==[]
    assert set(managed_schools(users['salud']))=={health.pk}
    assert set(managed_schools(users['odontologia']))=={dental.pk}
    assert set(shared_schools(users['salud']))=={dental.pk} and not shared_schools(users['odontologia']).exists()
    assert set(scopes(users['odontologia']))==set(cfg['dental_services']) and not scopes(users['salud']).exists()
    assert set(managed_institutions(users['institution']))=={inst.pk} and users['institution'].is_superuser
    for u in users.values():assert required(u),'MFA not required'
    # Real permission routing without creating public sessions or enrolling another persons authenticator.
    for role,other in [('salud',dental),('odontologia',health)]:
        client=APIClient();client.force_authenticate(users[role])
        assert client.get(f'/api/v1/schools/{other.pk}/management/',HTTP_HOST='plansaludmodelo.online').status_code==404
        response=client.get(f'/api/v1/schools/{other.pk}/',HTTP_HOST='plansaludmodelo.online')
        assert response.status_code==(200 if role=='salud' else 404)
    assert previous or not MFADevice.objects.filter(user__in=users.values()).exists(),'Do not enroll or alter personal authenticators during bootstrap'
print(json.dumps({'configured':True,'idempotent_repeat':previous,'school_ids':{'salud':health.pk,'odontologia':dental.pk},'account_ids':{k:v.pk for k,v in users.items()},'new_accounts':0 if previous else 3,'mfa_required':True,'mfa_enrollment':'first personal login','patient_intake_enabled':False}))
