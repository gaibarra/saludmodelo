from django.contrib.auth import get_user_model
from django.db import transaction,IntegrityError
from django.db.models import Q,Sum,Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .academic import AcademicView,data
from .admin_serializers import StrictSerializer,UserInput,ServiceInput,ReasonInput
from .models import School,SchoolMember,SchoolAcademicGrant,InstitutionMember,Service,Site,AcademicCycle,AcademicStudent,AcademicPractice,AcademicCycleReport
from .school_access import managed_schools,shared_schools
from .governance import managed_institutions,record
from .institutional_services import published_services,public_item


def manageable(user):
    return School.objects.filter(Q(pk__in=managed_schools(user))|Q(institution_id__in=managed_institutions(user)))

def visible(user):
    return School.objects.filter(Q(pk__in=manageable(user))|Q(pk__in=shared_schools(user))).distinct()

def item(s,user):
    return {'id':s.pk,'institution':s.institution_id,'name':s.name,'code':s.code,'can_manage':manageable(user).filter(pk=s.pk).exists()}

class Schools(AcademicView):
    @extend_schema(operation_id='schools_list',responses=OpenApiTypes.OBJECT)
    def get(self,request):return self.page(request,visible(request.user).order_by('name','id'),lambda s:item(s,request.user))

class SchoolDashboard(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        school=get_object_or_404(visible(request.user),pk=pk)
        states=list(AcademicPractice.objects.filter(placement__cycle__school=school).values('status').annotate(participations=Count('id'),minutes=Sum('minutes')).order_by('status'))
        result={**item(school,request.user),'cycles':AcademicCycle.objects.filter(school=school).count(),'students':AcademicStudent.objects.filter(school=school).count(),'states':states,'reports':AcademicCycleReport.objects.filter(cycle__school=school).count(),'published_services':[public_item(row) for row in published_services().filter(service__school=school)]}
        if not result['can_manage']:
            record(request.user,school.institution_id,'school.academic.consulted',school.pk,'Consulta académica compartida; sin autoridad administrativa')
        return Response(result)

class SchoolManagement(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        school=get_object_or_404(manageable(request.user),pk=pk)
        return Response({**item(school,request.user),'users':[{'id':m.user_id,'name':m.user.get_full_name() or m.user.username} for m in SchoolMember.objects.filter(school=school,user__is_active=True,user__patient_profile__isnull=True).select_related('user').order_by('user_id')],
            'services':list(Service.objects.filter(school=school).values('id','name','site_id','confirmed','etag')),
            'sites':list(Site.objects.filter(campus__institution_id=school.institution_id).values('id','name'))})

class SchoolUserCreate(AcademicView):
    @extend_schema(request=UserInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        school=get_object_or_404(manageable(request.user),pk=pk)
        v=data(UserInput,request)
        if v.pop('institution')!=school.institution_id:raise ValidationError('Institución incompatible.')
        try:
            with transaction.atomic():user=get_user_model().objects.create_user(**v)
        except IntegrityError:raise ValidationError('Nombre de cuenta no disponible. No se vinculan cuentas ajenas automáticamente.')
        InstitutionMember.objects.create(user=user,institution=school.institution)
        SchoolMember.objects.create(user=user,school=school)
        record(request.user,school.institution_id,'school.user.created',user.pk,'Alta de cuenta en escuela '+str(school.pk))
        return Response({'id':user.pk},status=201)

class SchoolServiceCreate(AcademicView):
    @extend_schema(request=ServiceInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        school=get_object_or_404(manageable(request.user),pk=pk);v=data(ServiceInput,request)
        site=get_object_or_404(Site,pk=v.pop('site'),campus__institution_id=school.institution_id)
        service=Service.objects.create(school=school,site=site,**v)
        record(request.user,school.institution_id,'school.service.created',service.pk,'Alta pendiente de confirmación',service)
        return Response({'id':service.pk},status=201)

class GrantInput(StrictSerializer):
    reader_school=serializers.IntegerField(min_value=1)
    starts=serializers.DateField()
    ends=serializers.DateField()
    rationale=serializers.CharField(min_length=5,max_length=2000)
    def validate(self,v):
        if v['starts']>v['ends']:raise ValidationError('Fechas inválidas.')
        return v

class SchoolGrants(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        school=get_object_or_404(manageable(request.user),pk=pk)
        return Response({'schools':[],'grants':[],'sharing_enabled':False})
    @extend_schema(request=GrantInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        get_object_or_404(manageable(request.user),pk=pk)
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('El acceso entre escuelas está deshabilitado por disposición institucional.')

class SchoolGrantRevoke(AcademicView):
    @extend_schema(request=ReasonInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk,grant):
        school=get_object_or_404(manageable(request.user).select_for_update(),pk=pk);v=data(ReasonInput,request)
        g=get_object_or_404(SchoolAcademicGrant.objects.select_for_update(),pk=grant,school=school)
        if not g.revoked_at:
            g.revoked_at=timezone.now();g.save(update_fields=['revoked_at']);record(request.user,school.institution_id,'school.academic.revoked',g.pk,v['rationale'])
        return Response({'id':g.pk,'revoked_at':g.revoked_at})
