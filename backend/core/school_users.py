"""School account directory: scoped CRUD with reversible deactivation, never history deletion."""
import json
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction, IntegrityError
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404
from django.utils.crypto import salted_hmac, constant_time_compare
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .academic import AcademicView, data
from .admin_serializers import StrictSerializer
from .school_views import manageable
from .models import SchoolMember, InstitutionMember, SchoolMandate, InstitutionMandate, RoleAssignment, AcademicStudent, AcademicPlacement
from .governance import record, managed_institutions


def accounts(school):
    return get_user_model().objects.filter(schoolmember__school=school, patient_profile__isnull=True).distinct()


def restriction(user, school, actor):
    if user.pk==actor.pk:return 'Tu propia cuenta se administra por el procedimiento institucional.'
    if user.is_superuser or user.is_staff or SchoolMandate.objects.filter(user=user).exists() or InstitutionMandate.objects.filter(user=user).exists():
        return 'Cuenta de autoridad o administración: requiere gestión institucional.'
    if (SchoolMember.objects.filter(user=user).exclude(school=school).exists()
        or InstitutionMember.objects.filter(user=user).exclude(institution_id=school.institution_id).exists()
        or RoleAssignment.objects.filter(user=user).exclude(service__school=school).exists()
        or AcademicStudent.objects.filter(user=user).exclude(school=school).exists()
        or AcademicPlacement.objects.filter(supervisor=user).exclude(cycle__school=school).exists()):
        return 'Cuenta compartida con otros ámbitos: requiere gestión institucional.'
    return ''


def can_edit_name(user, school, actor):
    if not restriction(user,school,actor) or user.pk==actor.pk:return True
    institutions=set(managed_institutions(actor))
    if school.institution_id not in institutions:return False
    if (user.is_superuser or user.is_staff) and not actor.is_superuser:return False
    return not (SchoolMember.objects.filter(user=user).exclude(school__institution_id__in=institutions).exists()
        or InstitutionMember.objects.filter(user=user).exclude(institution_id__in=institutions).exists())


def revision(user):
    fields=[user.pk,user.username,user.first_name,user.last_name,user.email,user.is_active,user.password]
    return salted_hmac('school-account-revision',json.dumps(fields),algorithm='sha256').hexdigest()


def item(user,school,actor):
    reason=restriction(user,school,actor)
    return {'id':user.pk,'username':user.username,'first_name':user.first_name,'last_name':user.last_name,
            'email':user.email,'is_active':user.is_active,'version':revision(user),
            'can_manage':not reason,'can_edit_name':can_edit_name(user,school,actor),'restriction':reason}

class AccountEdit(StrictSerializer):
    version=serializers.CharField(max_length=64)
    username=serializers.RegexField(r'^[a-zA-Z0-9_.@+-]+$',max_length=150)
    first_name=serializers.CharField(max_length=150)
    last_name=serializers.CharField(max_length=150,allow_blank=True)
    email=serializers.EmailField(allow_blank=True)
    rationale=serializers.CharField(min_length=5,max_length=2000)

class AccountState(StrictSerializer):
    version=serializers.CharField(max_length=64)
    rationale=serializers.CharField(min_length=5,max_length=2000)

class SchoolAccounts(AcademicView):
    @extend_schema(operation_id="school_accounts_list",responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        school=get_object_or_404(manageable(request.user),pk=pk)
        qs=accounts(school)
        query=request.query_params.get('q','').strip()
        if len(query)>150:raise ValidationError('La búsqueda admite hasta 150 caracteres.')
        state=request.query_params.get('state','all')
        if state not in ('all','active','inactive'):raise ValidationError('Estado inválido.')
        if state!='all':qs=qs.filter(is_active=state=='active')
        if query:qs=qs.annotate(full_name=Concat('first_name',Value(' '),'last_name')).filter(Q(username__icontains=query)|Q(full_name__icontains=query)|Q(email__icontains=query))
        return self.page(request,qs.order_by('last_name','first_name','id'),lambda u:item(u,school,request.user))

class SchoolAccountDetail(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk,user):
        school=get_object_or_404(manageable(request.user),pk=pk)
        return Response(item(get_object_or_404(accounts(school),pk=user),school,request.user))

    def target(self,request,pk,user,values,name_only=False):
        school=get_object_or_404(manageable(request.user),pk=pk)
        # Lock the actual user table (not the DISTINCT membership query).
        target=get_object_or_404(get_user_model().objects.select_for_update(),pk=user)
        if not accounts(school).filter(pk=target.pk).exists():
            from django.http import Http404
            raise Http404
        reason=restriction(target,school,request.user)
        if name_only:
            if not can_edit_name(target,school,request.user):raise PermissionDenied('No tiene permiso para corregir este nombre.')
        elif reason:raise PermissionDenied(reason)
        if not constant_time_compare(revision(target),values['version']):return school,target,Response({'detail':'La cuenta cambió. Recarga antes de guardar.'},status=409)
        return school,target,None

    @extend_schema(request=AccountEdit,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def patch(self,request,pk,user):
        v=data(AccountEdit,request);school,target,error=self.target(request,pk,user,v)
        if error is not None:return error
        if get_user_model().objects.exclude(pk=target.pk).filter(username__iexact=v['username']).exists():raise ValidationError('Usuario no disponible.')
        for field in ('username','first_name','last_name','email'):setattr(target,field,v[field])
        try:
            with transaction.atomic():target.save(update_fields=['username','first_name','last_name','email'])
        except IntegrityError:raise ValidationError('Usuario no disponible.')
        record(request.user,school.institution_id,'school.user.updated',target.pk,v['rationale'])
        return Response(item(target,school,request.user))

    @extend_schema(request=AccountState,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def delete(self,request,pk,user):
        v=data(AccountState,request);school,target,error=self.target(request,pk,user,v)
        if error is not None:return error
        if target.is_active:
            target.is_active=False;target.save(update_fields=['is_active'])
            # Old sessions must not become valid again on later reactivation.
            ids=[s.session_key for s in Session.objects.iterator() if str(s.get_decoded().get('_auth_user_id'))==str(target.pk)]
            Session.objects.filter(session_key__in=ids).delete()
            record(request.user,school.institution_id,'school.user.deactivated',target.pk,v['rationale'])
        return Response(item(target,school,request.user))

class SchoolAccountReactivate(SchoolAccountDetail):
    http_method_names=['post','options']
    @extend_schema(request=AccountState,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk,user):
        v=data(AccountState,request);school,target,error=self.target(request,pk,user,v)
        if error is not None:return error
        if not target.is_active:
            target.is_active=True;target.save(update_fields=['is_active'])
            record(request.user,school.institution_id,'school.user.reactivated',target.pk,v['rationale'])
        return Response(item(target,school,request.user))


class AccountNameEdit(StrictSerializer):
    version=serializers.CharField(max_length=64)
    first_name=serializers.CharField(max_length=150)
    last_name=serializers.CharField(max_length=150,allow_blank=True)
    rationale=serializers.CharField(min_length=5,max_length=2000)

class SchoolAccountName(SchoolAccountDetail):
    http_method_names=['patch','options']
    @extend_schema(request=AccountNameEdit,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def patch(self,request,pk,user):
        v=data(AccountNameEdit,request);school,target,error=self.target(request,pk,user,v,name_only=True)
        if error is not None:return error
        before={'first_name':target.first_name,'last_name':target.last_name}
        target.first_name=v['first_name'];target.last_name=v['last_name']
        target.save(update_fields=['first_name','last_name'])
        record(request.user,school.institution_id,'school.user.name_corrected',target.pk,json.dumps({'reason':v['rationale'],'before':before,'after':{'first_name':target.first_name,'last_name':target.last_name}},ensure_ascii=False))
        return Response(item(target,school,request.user))
