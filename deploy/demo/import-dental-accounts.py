"""Executed inside Django with CONFIG supplied in memory, never stores passwords.
Creates only the explicitly requested school memberships; no service roles.
"""
import hashlib,json,unicodedata
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.db import transaction
from core.models import School,SchoolMember,InstitutionMember,RoleAssignment
from core.governance import record

def norm(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if not unicodedata.combining(c)).split())

def execute(config):
    User=get_user_model();school=School.objects.get(code='odontologia',institution_id=1)
    actor=User.objects.get(email='gibarra@modelo.edu.mx',is_active=True,is_superuser=True)
    mario=User.objects.get(username='mariososa@modelo.edu.mx',is_active=True)
    assert SchoolMember.objects.filter(user=mario,school=school).exists()
    assert len(config['rows'])==56
    existing=list(User.objects.all())
    original={u.pk:User.objects.filter(pk=u.pk).values().get() for u in existing}
    created=[];skipped=[];seen=set();planned=[]
    with transaction.atomic():
        # Serialize this batch against concurrent reruns.
        School.objects.select_for_update().get(pk=school.pk)
        for row in config['rows']:
            assert norm(row['source_name'])!='sosa correa mario'
            validate_email(row['email']);assert row['username']==row['email'] and len(row['username'])<=150
            assert row['username'] not in seen;seen.add(row['username'])
            assert len(row['first_name'])<=150 and len(row['last_name'])<=150
            matches=[u for u in existing if norm(u.email)==norm(row['email']) or norm(u.username)==norm(row['username']) or norm(u.last_name+' '+u.first_name)==norm(row['source_name'])]
            if matches:
                assert len(matches)==1,'Ambiguous existing account'
                u=matches[0]
                assert u.email.casefold()==row['email'] and u.username==row['username'] and u.is_active,'Existing identity conflict'
                assert SchoolMember.objects.filter(user=u,school=school).exists(),'Existing account belongs elsewhere'
                assert not SchoolMember.objects.filter(user=u).exclude(school=school).exists(),'Cross-school membership'
                skipped.append({'username':u.username,'name':row['source_name']});continue
            planned.append(row)
        if config.get('apply'):
            assert config.get('password'),'Initial password required'
            for row in planned:
                u=User.objects.create_user(username=row['username'],email=row['email'],first_name=row['first_name'],last_name=row['last_name'],password=config['password'])
                InstitutionMember.objects.create(user=u,institution_id=school.institution_id)
                SchoolMember.objects.create(user=u,school=school)
                record(actor,school.institution_id,'school.user.created',u.pk,'Alta autorizada de colaboradores de Odontología 13/10/2026; fuente SHA256 '+config['source_sha256']+'; clave '+row['source_key']+'. Contraseña provisional por excepción expresa; sin asignar funciones.')
                assert u.check_password(config['password']) and not u.is_superuser and not u.is_staff
                assert not RoleAssignment.objects.filter(user=u).exists()
                created.append({'id':u.pk,'username':u.username,'name':row['source_name']})
        for pk,values in original.items():assert User.objects.filter(pk=pk).values().get()==values,'Existing account changed'
    return {'applied':bool(config.get('apply')),'planned':len(planned),'created':created,'skipped':skipped,'excluded':'SOSA CORREA MARIO','existing_accounts_unchanged':len(original),'school':school.pk}

RESULT=execute(CONFIG)
print(json.dumps(RESULT,ensure_ascii=False))
