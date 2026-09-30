"""Apply a reviewed ownership plan; no invented users, source changes or implicit sharing."""
import json
from datetime import date
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from core.models import Institution,InstitutionMember,School,SchoolMember,SchoolMandate,Service,AcademicCycle,AcademicStudent,AcademicPlacement
from core.governance import record

class Command(BaseCommand):
    help='Validate school ownership plan; --apply commits. Existing accounts only; never assigns unlisted records.'
    def add_arguments(self,parser):
        parser.add_argument('--plan',required=True)
        parser.add_argument('--apply',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        try:
            plan=json.loads(Path(options['plan']).read_text())
            institution=Institution.objects.select_for_update().get(pk=plan['institution'])
            approver=get_user_model().objects.get(username=plan['approved_by'],is_active=True)
            starts=date.fromisoformat(plan['starts']);ends=date.fromisoformat(plan['ends'])
            if starts>ends or len(plan['rationale'].strip())<5:raise ValueError('Fechas o justificación inválidas')
            seen={key:set() for key in ('services','cycles','students')}
            result=[]
            for row in plan['schools']:
                director=get_user_model().objects.get(username=row['director'],is_active=True)
                if director.pk==approver.pk:raise ValueError('El director no puede aprobar su nombramiento')
                users=list(get_user_model().objects.filter(username__in=set(row['members'])|{row['director']},is_active=True,patient_profile__isnull=True))
                if len(users)!=len(set(row['members'])|{row['director']}):raise ValueError('Faltan cuentas activas no pacientes')
                if InstitutionMember.objects.filter(institution=institution,user__in=users).count()!=len(users):raise ValueError('Cuentas sin pertenencia institucional')
                school,created=School.objects.get_or_create(institution=institution,code=row['code'],defaults={'name':row['name']})
                if school.name!=row['name']:raise ValueError('El nombre no coincide con la escuela existente')
                for user in users:SchoolMember.objects.get_or_create(school=school,user=user)
                existing=SchoolMandate.objects.filter(school=school,user=director,starts=starts,ends=ends,revoked_at__isnull=True).first()
                if not existing:
                    grant=SchoolMandate.objects.create(school=school,user=director,approved_by=approver,starts=starts,ends=ends,rationale=plan['rationale'])
                    record(approver,institution.pk,'school.direction.granted',grant.pk,plan['rationale'])
                counts={}
                for key,model in [('services',Service),('cycles',AcademicCycle),('students',AcademicStudent)]:
                    ids=row.get(key,[])
                    if len(ids)!=len(set(ids)) or seen[key]&set(ids):raise ValueError('Registros repetidos entre escuelas: '+key)
                    seen[key].update(ids)
                    qs=model.objects.select_for_update().filter(pk__in=ids)
                    if qs.count()!=len(ids):raise ValueError('Identificadores inexistentes: '+key)
                    for obj in qs:
                        inst=obj.site.campus.institution_id if key=='services' else obj.institution_id
                        if inst!=institution.pk or obj.school_id not in (None,school.pk):raise ValueError('Propiedad incompatible; no se trasladan registros entre escuelas')
                        if key=='students' and obj.user_id not in {u.pk for u in users}:raise ValueError('Alumno fuera de los miembros explícitos')
                        if obj.school_id is None:
                            obj.school=school
                            fields=['school']
                            if key=='cycles':obj.revision+=1;fields.append('revision')
                            obj.save(update_fields=fields)
                            record(approver,institution.pk,'school.ownership.assigned',f'{key}:{obj.pk}',plan['rationale'],obj if key=='services' else None)
                    counts[key]=len(ids)
                result.append({'school':school.pk,'code':school.code,'records':counts})
            # Verify every placement touched by the plan has one consistent school owner.
            from django.db.models import Q
            touched=AcademicPlacement.objects.filter(Q(service_id__in=seen['services'])|Q(cycle_id__in=seen['cycles'])|Q(student_id__in=seen['students'])).select_related('service','cycle','student')
            for p in touched:
                if not p.cycle.school_id or not p.cycle.school_id==p.service.school_id==p.student.school_id:raise ValueError('Plan incompleto: rotación '+str(p.pk)+' mezcla escuelas o registros sin clasificar')
            self.stdout.write(json.dumps({'applied':options['apply'],'schools':result,'sharing_grants_created':0},ensure_ascii=False))
            if not options['apply']:transaction.set_rollback(True)
        except (KeyError,ValueError,TypeError,Institution.DoesNotExist,get_user_model().DoesNotExist) as exc:
            raise CommandError('Plan rechazado: '+str(exc))
