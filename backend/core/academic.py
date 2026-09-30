"""Academic participation records; no clinical chart or automatic accreditation."""
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import (Institution, InstitutionMember, Service, RoleAssignment, AcademicCycle,
                     AcademicStudent, AcademicPlacement, AcademicPractice, AcademicPracticeEvent)
from .admin_serializers import StrictSerializer
from .governance import managed_institutions, require_institution, record
from .access import scopes
from .workflow import Conflict
from .school_access import owned,managed_schools,shared_schools,can_manage_academic,require_academic,require_owner
from .models import School,SchoolMember
from .academic_cycle import lock_open, changed

SUPERVISE={'clinical','manager'}
FIELDS=('title','performed_on','minutes','competency','evidence_reference','activity_reference')

def data(cls,request):
    serializer=cls(data=request.data);serializer.is_valid(raise_exception=True);return serializer.validated_data

def placements(user):
    return AcademicPlacement.objects.filter(
        owned(user,'cycle__',read=True) |
        Q(student__user=user) |
        Q(supervisor=user,service_id__in=scopes(user,SUPERVISE))
    ).select_related('student__user','cycle','service__site__campus','supervisor').distinct()

def is_manager(user,placement):
    return can_manage_academic(user,placement.cycle)

def can_review(user,p):
    return p.supervisor_id==user.pk and p.student.user_id!=user.pk and not p.revoked_at and not p.cycle.closed_at and p.service_id in scopes(user,SUPERVISE)

def practice_item(p,user):
    row={field:getattr(p,field) for field in FIELDS}
    row.update(id=p.pk,placement=p.placement_id,etag=p.etag,status=p.status,created_at=p.created_at,
        student=p.placement.student_id,student_name=p.placement.student.user.get_full_name() or p.placement.student.user.username,
        enrollment=p.placement.student.enrollment,program=p.placement.student.program,group=p.placement.group,
        service=p.placement.service_id,service_name=p.placement.service.name,cycle=p.placement.cycle_id,
        supervisor_name=p.placement.supervisor.get_full_name() or p.placement.supervisor.username,
        can_resubmit=p.placement.student.user_id==user.pk and not p.placement.revoked_at and not p.placement.cycle.closed_at and p.status=='returned',
        can_review=can_review(user,p.placement) and p.status=='submitted',
        can_void=not p.placement.cycle.closed_at and p.status!='void' and p.placement.student.user_id!=user.pk and (can_review(user,p.placement) or is_manager(user,p.placement)))
    return row

def snapshot(p):
    return {**{f:str(getattr(p,f)) if f=='performed_on' else getattr(p,f) for f in FIELDS},'status':p.status,'placement':p.placement_id}

def event(p,user,action,rationale=''):
    AcademicPracticeEvent.objects.create(practice=p,version=p.etag,action=action,actor=user,rationale=rationale,snapshot=snapshot(p))

def placement_item(p,user):
    return {'id':p.pk,'student':p.student_id,'student_name':p.student.user.get_full_name() or p.student.user.username,
        'enrollment':p.student.enrollment,'program':p.student.program,'cycle':p.cycle_id,'cycle_name':p.cycle.name,'school':p.cycle.school_id,'school_name':p.cycle.school.name if p.cycle.school_id else 'Sin clasificar',
        'service':p.service_id,'service_name':p.service.name,'site_name':p.service.site.name,'supervisor':p.supervisor_id,
        'supervisor_name':p.supervisor.get_full_name() or p.supervisor.username,'group':p.group,'starts':p.starts,'ends':p.ends,
        'target_minutes':p.target_minutes,'revoked_at':p.revoked_at,'revocation_reason':p.revocation_reason,
        'can_submit':p.student.user_id==user.pk and not p.revoked_at and p.service.confirmed and not p.cycle.closed_at,
        'can_manage':is_manager(user,p) and not p.cycle.closed_at}

class AcademicPage(PageNumberPagination):
    page_size=50

class AcademicView(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs)
        response['Cache-Control']='private, no-store'
        return response
    def page(self,request,qs,render):
        page=AcademicPage();rows=page.paginate_queryset(qs,request,view=self)
        return page.get_paginated_response([render(row) for row in rows])

class CycleInput(StrictSerializer):
    school=serializers.IntegerField(min_value=1,required=False,allow_null=True,default=None)
    institution=serializers.IntegerField(min_value=1)
    code=serializers.CharField(max_length=60)
    name=serializers.CharField(max_length=160)
    starts=serializers.DateField()
    ends=serializers.DateField()
    def validate(self,v):
        if v['starts']>v['ends']:raise ValidationError('El inicio debe ser anterior o igual al cierre del ciclo.')
        return v

class StudentInput(StrictSerializer):
    school=serializers.IntegerField(min_value=1,required=False,allow_null=True,default=None)
    institution=serializers.IntegerField(min_value=1)
    user=serializers.IntegerField(min_value=1)
    enrollment=serializers.CharField(max_length=60)
    program=serializers.CharField(max_length=160)

class PlacementInput(StrictSerializer):
    student=serializers.IntegerField(min_value=1)
    cycle=serializers.IntegerField(min_value=1)
    service=serializers.IntegerField(min_value=1)
    supervisor=serializers.IntegerField(min_value=1)
    group=serializers.CharField(max_length=80)
    starts=serializers.DateField()
    ends=serializers.DateField()
    target_minutes=serializers.IntegerField(min_value=1,max_value=1000000,required=False,allow_null=True)

class AcademicReasonInput(StrictSerializer):
    rationale=serializers.CharField(min_length=5,max_length=2000)

class AcademicPracticeInput(StrictSerializer):
    placement=serializers.IntegerField(min_value=1)
    client_key=serializers.UUIDField()
    title=serializers.CharField(max_length=200)
    performed_on=serializers.DateField()
    minutes=serializers.IntegerField(min_value=1,max_value=1440)
    competency=serializers.CharField(max_length=300)
    evidence_reference=serializers.CharField(max_length=500)
    activity_reference=serializers.CharField(max_length=100,allow_blank=True,default='')

class AcademicResubmitInput(StrictSerializer):
    version=serializers.IntegerField(min_value=1)
    title=serializers.CharField(max_length=200)
    performed_on=serializers.DateField()
    minutes=serializers.IntegerField(min_value=1,max_value=1440)
    competency=serializers.CharField(max_length=300)
    evidence_reference=serializers.CharField(max_length=500)
    activity_reference=serializers.CharField(max_length=100,allow_blank=True,default='')
    rationale=serializers.CharField(min_length=5,max_length=2000)

class AcademicReviewInput(AcademicReasonInput):
    version=serializers.IntegerField(min_value=1)
    action=serializers.ChoiceField(choices=['validate','return','void'])

class AcademicFilter(serializers.Serializer):
    school=serializers.IntegerField(min_value=1,required=False)
    institution=serializers.IntegerField(min_value=1,required=False)
    student=serializers.IntegerField(min_value=1,required=False)
    cycle=serializers.IntegerField(min_value=1,required=False)
    service=serializers.IntegerField(min_value=1,required=False)
    supervisor=serializers.IntegerField(min_value=1,required=False)
    group=serializers.CharField(max_length=80,required=False)
    program=serializers.CharField(max_length=160,required=False)
    status=serializers.ChoiceField(choices=['submitted','returned','validated','void'],required=False)

def filtered(qs,request,practice=False):
    for key in request.query_params:
        if key not in {'page',*AcademicFilter().fields}:raise ValidationError('Filtro no reconocido.')
        if len(request.query_params.getlist(key))!=1:raise ValidationError('Filtro repetido.')
    f=AcademicFilter(data=request.query_params);f.is_valid(raise_exception=True)
    prefix='placement__' if practice else ''
    paths={'school':'cycle__school_id','institution':'student__institution_id','student':'student_id','cycle':'cycle_id','service':'service_id','supervisor':'supervisor_id','group':'group','program':'student__program'}
    for key,value in f.validated_data.items():
        if key=='status':
            if practice:qs=qs.filter(status=value)
        else:qs=qs.filter(**{prefix+paths[key]:value})
    return qs

class AcademicOptions(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        managed=list(managed_institutions(request.user));schools=list(managed_schools(request.user))
        visible=placements(request.user)
        institutions=Institution.objects.filter(Q(pk__in=managed)|Q(pk__in=School.objects.filter(pk__in=schools).values('institution_id'))|Q(pk__in=visible.values('student__institution_id'))|Q(pk__in=AcademicStudent.objects.filter(user=request.user).values('institution_id'))).distinct()
        members=InstitutionMember.objects.filter(Q(institution_id__in=managed)|Q(user_id__in=SchoolMember.objects.filter(school_id__in=schools).values('user_id'),institution_id__in=School.objects.filter(pk__in=schools).values('institution_id')),user__is_active=True,user__patient_profile__isnull=True).select_related('user').distinct()
        services=Service.objects.filter(Q(site__campus__institution_id__in=managed)|Q(school_id__in=schools),confirmed=True).select_related('site__campus')
        supervisors=RoleAssignment.objects.filter(service__in=services,role__in=SUPERVISE,revoked_at__isnull=True,user__is_active=True).select_related('user')
        school_rows=School.objects.filter(Q(institution_id__in=managed)|Q(pk__in=schools)|Q(pk__in=shared_schools(request.user))).distinct()
        return Response({'institutions':[{'id':i.pk,'name':i.name,'can_manage':i.pk in managed} for i in institutions],
            'schools':[{'id':s.pk,'institution':s.institution_id,'name':s.name,'can_manage':s.pk in schools or s.institution_id in managed} for s in school_rows],
            'users':[{'id':m.user_id,'institution':m.institution_id,'schools':list(SchoolMember.objects.filter(user=m.user,school__in=school_rows).values_list('school_id',flat=True)),'name':m.user.get_full_name() or m.user.username} for m in members],
            'services':[{'id':s.pk,'institution':s.site.campus.institution_id,'school':s.school_id,'name':s.name,'site_name':s.site.name} for s in services],
            'supervisors':[{'id':a.user_id,'service':a.service_id,'name':a.user.get_full_name() or a.user.username,'starts':a.starts,'ends':a.ends} for a in supervisors]})

class AcademicCycles(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        qs=AcademicCycle.objects.filter(owned(request.user,read=True)|Q(pk__in=placements(request.user).values('cycle_id'))).distinct().order_by('-starts','-id')
        return self.page(request,qs,lambda c:{'id':c.pk,'institution':c.institution_id,'code':c.code,'name':c.name,'starts':c.starts,'ends':c.ends,'revision':c.revision,'closed_at':c.closed_at,'closed_report':c.closed_report_id,'school':c.school_id,'school_name':c.school.name if c.school_id else 'Sin clasificar','can_manage':can_manage_academic(request.user,c)})
    @extend_schema(request=CycleInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        v=data(CycleInput,request);require_owner(request.user,v['institution'],v['school'])
        Institution.objects.select_for_update().get(pk=v['institution'])
        v['code']=v['code'].strip().upper()
        if AcademicCycle.objects.filter(institution_id=v['institution'],school_id=v['school'],code=v['code']).exists():raise ValidationError('Ya existe ese código de ciclo.')
        c=AcademicCycle.objects.create(institution_id=v.pop('institution'),school_id=v.pop('school'),created_by=request.user,**v)
        record(request.user,c.institution_id,'academic.cycle.created',c.pk,'Alta de ciclo académico')
        return Response({'id':c.pk},status=201)

class AcademicStudents(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        qs=AcademicStudent.objects.filter(owned(request.user,read=True)|Q(user=request.user)|Q(pk__in=placements(request.user).values('student_id'))).select_related('user').distinct().order_by('enrollment','id')
        return self.page(request,qs,lambda s:{'id':s.pk,'institution':s.institution_id,'user':s.user_id,'name':s.user.get_full_name() or s.user.username,'enrollment':s.enrollment,'program':s.program,'school':s.school_id})
    @extend_schema(request=StudentInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        v=data(StudentInput,request);require_owner(request.user,v['institution'],v['school'])
        if v['school'] and not SchoolMember.objects.filter(school_id=v['school'],user_id=v['user']).exists():raise ValidationError('La cuenta debe pertenecer a la escuela.')
        user=get_object_or_404(get_user_model().objects.select_for_update(of=('self',)),pk=v['user'],is_active=True,institutionmember__institution_id=v['institution'],patient_profile__isnull=True)
        v['enrollment']=v['enrollment'].strip().upper()
        try:
            with transaction.atomic():s=AcademicStudent.objects.create(institution_id=v['institution'],school_id=v['school'],user=user,enrollment=v['enrollment'],program=v['program'])
        except IntegrityError:raise ValidationError('La cuenta o matrícula ya está registrada como alumno.')
        record(request.user,s.institution_id,'academic.student.created',s.pk,'Alta de alumno')
        return Response({'id':s.pk},status=201)

class AcademicPlacements(AcademicView):
    @extend_schema(parameters=[AcademicFilter],responses=OpenApiTypes.OBJECT)
    def get(self,request):
        return self.page(request,filtered(placements(request.user),request).order_by('-id'),lambda p:placement_item(p,request.user))
    @extend_schema(request=PlacementInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        v=data(PlacementInput,request)
        student=get_object_or_404(AcademicStudent.objects.filter(owned(request.user)),pk=v['student'],user__is_active=True)
        cycle=get_object_or_404(AcademicCycle,pk=v['cycle'],institution_id=student.institution_id,school_id=student.school_id)
        cycle=lock_open(cycle.pk)
        AcademicStudent.objects.select_for_update().get(pk=student.pk)
        service=get_object_or_404(Service.objects.select_for_update(),pk=v['service'],confirmed=True,site__campus__institution_id=student.institution_id,school_id=cycle.school_id)
        if not cycle.starts<=v['starts']<=v['ends']<=cycle.ends:raise ValidationError('La rotación debe quedar dentro de las fechas del ciclo.')
        if v['supervisor']==student.user_id:raise ValidationError('El alumno no puede ser su propio supervisor.')
        if not RoleAssignment.objects.filter(user_id=v['supervisor'],user__is_active=True,service=service,role__in=SUPERVISE,revoked_at__isnull=True,starts__lte=v['starts'],ends__gte=v['ends']).exists():raise ValidationError('El supervisor requiere un nombramiento clínico o responsable del servicio que cubra toda la rotación.')
        if AcademicPlacement.objects.filter(student=student,service=service,revoked_at__isnull=True,starts__lte=v['ends'],ends__gte=v['starts']).exists():raise ValidationError('El alumno ya tiene una rotación activa en ese servicio para esas fechas.')
        p=AcademicPlacement.objects.create(student=student,cycle=cycle,service=service,supervisor_id=v['supervisor'],group=v['group'],starts=v['starts'],ends=v['ends'],target_minutes=v.get('target_minutes'),created_by=request.user)
        changed(cycle)
        record(request.user,student.institution_id,'academic.placement.created',p.pk,'Asignación académica de servicio y supervisor',service)
        return Response({'id':p.pk},status=201)

class AcademicPlacementRevoke(AcademicView):
    @extend_schema(request=AcademicReasonInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        v=data(AcademicReasonInput,request)
        p=get_object_or_404(placements(request.user),pk=pk)
        require_academic(request.user,p.cycle)
        cycle=lock_open(p.cycle_id)
        AcademicStudent.objects.select_for_update().get(pk=p.student_id)
        p=AcademicPlacement.objects.select_for_update().get(pk=pk)
        if not p.revoked_at:
            p.revoked_at=timezone.now();p.revocation_reason=v['rationale'];p.save(update_fields=['revoked_at','revocation_reason'])
            changed(cycle)
            record(request.user,p.student.institution_id,'academic.placement.revoked',p.pk,v['rationale'],p.service)
        return Response({'id':p.pk,'revoked_at':p.revoked_at})

def validate_activity(p,v,exclude=None):
    if p.revoked_at or not p.service.confirmed:raise ValidationError('La rotación no está habilitada para registrar prácticas.')
    if not p.starts<=v['performed_on']<=p.ends or v['performed_on']>timezone.localdate():raise ValidationError('La práctica debe haberse realizado dentro de la rotación y no en una fecha futura.')
    current=AcademicPractice.objects.filter(placement__student_id=p.student_id,performed_on=v['performed_on']).exclude(status='void')
    if exclude:current=current.exclude(pk=exclude)
    total=current.aggregate(total=Sum('minutes'))['total'] or 0
    if total+v['minutes']>1440:raise ValidationError('Las participaciones del alumno excederían 24 horas en ese día, considerando todos sus servicios.')

class AcademicPractices(AcademicView):
    @extend_schema(parameters=[AcademicFilter],responses=OpenApiTypes.OBJECT)
    def get(self,request):
        qs=AcademicPractice.objects.filter(placement__in=placements(request.user)).select_related('placement__student__user','placement__supervisor','placement__service')
        return self.page(request,filtered(qs,request,True).order_by('-performed_on','-id'),lambda p:practice_item(p,request.user))
    @extend_schema(request=AcademicPracticeInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        v=data(AcademicPracticeInput,request)
        p=get_object_or_404(placements(request.user),pk=v['placement'],student__user=request.user)
        cycle=lock_open(p.cycle_id)
        AcademicStudent.objects.select_for_update().get(pk=p.student_id)
        p=placements(request.user).get(pk=p.pk)
        previous=AcademicPractice.objects.filter(placement=p,client_key=v['client_key']).first()
        if previous:
            first=previous.events.order_by('version').first().snapshot
            if any(str(first[f])!=str(v[f]) for f in FIELDS):raise ValidationError('La clave de envío corresponde a otra práctica.')
            return Response(practice_item(previous,request.user))
        validate_activity(p,v)
        row=AcademicPractice.objects.create(placement=p,client_key=v['client_key'],**{f:v[f] for f in FIELDS})
        event(row,request.user,'submitted')
        changed(cycle)
        return Response(practice_item(row,request.user),status=201)

class AcademicResubmit(AcademicView):
    @extend_schema(request=AcademicResubmitInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        v=data(AcademicResubmitInput,request)
        row=get_object_or_404(AcademicPractice,pk=pk,placement__student__user=request.user)
        cycle=lock_open(row.placement.cycle_id)
        AcademicStudent.objects.select_for_update().get(pk=row.placement.student_id)
        row=AcademicPractice.objects.select_for_update().get(pk=pk)
        if row.etag!=v['version']:raise Conflict()
        if row.status!='returned':raise ValidationError('Sólo se pueden corregir prácticas devueltas por el supervisor.')
        validate_activity(row.placement,v,exclude=pk)
        for f in FIELDS:setattr(row,f,v[f])
        row.status='submitted';row.etag+=1;row.save()
        event(row,request.user,'resubmitted',v['rationale'])
        changed(cycle)
        return Response(practice_item(row,request.user))

class AcademicReview(AcademicView):
    @extend_schema(request=AcademicReviewInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        v=data(AcademicReviewInput,request)
        row=get_object_or_404(AcademicPractice,pk=pk,placement__in=placements(request.user))
        cycle=lock_open(row.placement.cycle_id)
        AcademicStudent.objects.select_for_update().get(pk=row.placement.student_id)
        # Match service lock used when revoking a staff appointment.
        Service.objects.select_for_update().get(pk=row.placement.service_id)
        row=AcademicPractice.objects.select_for_update().get(pk=pk);p=row.placement
        if p.student.user_id==request.user.pk:raise PermissionDenied('Un alumno no puede validar o anular su propia práctica.')
        if not can_review(request.user,p) and not (v['action']=='void' and is_manager(request.user,p)):raise PermissionDenied('Requiere el supervisor asignado con nombramiento vigente.')
        if row.etag!=v['version']:raise Conflict()
        if row.status=='void' or (v['action']!='void' and row.status!='submitted'):raise ValidationError('La práctica ya no está pendiente de esta revisión.')
        row.status={'validate':'validated','return':'returned','void':'void'}[v['action']];row.etag+=1;row.save()
        event(row,request.user,v['action'],v['rationale'])
        changed(cycle)
        return Response(practice_item(row,request.user))

class AcademicHistory(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        row=get_object_or_404(AcademicPractice,pk=pk,placement__in=placements(request.user))
        return self.page(request,row.events.select_related('actor').order_by('version'),lambda e:{'id':e.pk,'version':e.version,'action':e.action,'actor':e.actor.get_full_name() or e.actor.username,'rationale':e.rationale,'snapshot':e.snapshot,'created_at':e.created_at})

class AcademicSummary(AcademicView):
    @extend_schema(parameters=[AcademicFilter],responses=OpenApiTypes.OBJECT)
    def get(self,request):
        qs=AcademicPractice.objects.filter(placement__in=placements(request.user))
        qs=filtered(qs,request,True)
        states=list(qs.values('status').annotate(participations=Count('id'),minutes=Sum('minutes')).order_by('status'))
        return Response({'as_of':timezone.now(),'states':states,'unit':'participaciones individuales; no pacientes ni actividades únicas','academic_accreditation':False})
