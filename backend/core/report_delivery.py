"""Explicit internal distribution of approved reports; never sends external messages."""
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .capacity import Private
from .access import scopes,READ,require
from .admin_serializers import StrictSerializer
from .models import SavedReport,ReportDelivery,Service,RoleAssignment,AuditEvent
from .report_schedules import authorize
from .saved_reports import serialize
from .workflow import Conflict

def eligible(service):
    day=timezone.localdate()
    return RoleAssignment.objects.filter(service_id=service,role__in=READ,user__is_active=True,revoked_at__isnull=True,starts__lte=day,ends__gte=day).order_by('user_id').values('user_id','user__username').distinct()

def available(report,content_hash):
    data=serialize(report,True)
    if data['availability']!='retained' or report.state!='approved':
        raise serializers.ValidationError('El informe debe estar aprobado y no retirado ni sustituido.')
    if report.content_hash!=content_hash:raise Conflict()
    return data

def receipt(row):
    return {'id':row.pk,'report_id':row.report_id,'recipient_id':row.recipient_id,'sender_id':row.sender_id,'created_at':row.created_at,'acknowledged_at':row.acknowledged_at,'rationale':row.rationale}

class ReportDistributionInput(StrictSerializer):
    content_hash=serializers.CharField(min_length=64,max_length=64)
    recipients=serializers.ListField(child=serializers.IntegerField(min_value=1),min_length=1,max_length=100)
    rationale=serializers.CharField(max_length=3000)
    def validate_recipients(self,values):
        if len(set(values))!=len(values):raise serializers.ValidationError('No repita destinatarios.')
        return values
class ReportReceiptInput(StrictSerializer):
    content_hash=serializers.CharField(min_length=64,max_length=64)

class DeliveryPageInput(StrictSerializer):
    page_size=serializers.IntegerField(default=50,min_value=1,max_value=100)
    before=serializers.IntegerField(required=False,min_value=1,max_value=9223372036854775807)

class DistributionPageInput(StrictSerializer):
    page_size=serializers.IntegerField(default=50,min_value=1,max_value=100)
    people_after=serializers.IntegerField(required=False,min_value=1,max_value=9223372036854775807)
    deliveries_before=serializers.IntegerField(required=False,min_value=1,max_value=9223372036854775807)

def page_input(serializer,request):
    if any(len(request.query_params.getlist(key))!=1 for key in request.query_params):
        raise serializers.ValidationError('No repita parámetros de paginación.')
    s=serializer(data=request.query_params);s.is_valid(raise_exception=True)
    return s.validated_data

class ReportDistribution(Private):
    @extend_schema(parameters=[DistributionPageInput],responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        report=get_object_or_404(SavedReport,pk=pk,service_id__in=scopes(request.user,READ))
        authorize(request.user,report.service)
        params=page_input(DistributionPageInput,request);size=params['page_size']
        people=eligible(report.service_id)
        rows=report.deliveries.order_by('-id')
        if 'people_after' in params:people=people.filter(user_id__gt=params['people_after'])
        if 'deliveries_before' in params:rows=rows.filter(id__lt=params['deliveries_before'])
        people=list(people[:size+1]);rows=list(rows[:size+1])
        return Response({'eligible_recipients':people[:size],'deliveries':[receipt(r) for r in rows[:size]],
            'next_people_after':people[size-1]['user_id'] if len(people)>size else None,
            'next_deliveries_before':rows[size-1].pk if len(rows)>size else None})
    @extend_schema(request=ReportDistributionInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        s=ReportDistributionInput(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
        original=get_object_or_404(SavedReport,pk=pk,service_id__in=scopes(request.user,READ))
        service=Service.objects.select_for_update().get(pk=original.service_id)
        authorize(request.user,service)
        report=SavedReport.objects.get(pk=pk);available(report,data['content_hash'])
        # Lock selected accounts in stable order; appointment changes share the service lock.
        users=list(get_user_model().objects.select_for_update().filter(pk__in=data['recipients'],is_active=True).order_by('pk'))
        valid=set(eligible(service.pk).filter(user_id__in=data['recipients']).values_list('user_id',flat=True))
        if len(users)!=len(data['recipients']) or not set(data['recipients'])<=valid:
            raise serializers.ValidationError('Todos los destinatarios deben ser cuentas activas con lectura vigente del servicio.')
        created=0
        for user in users:
            row,new=ReportDelivery.objects.get_or_create(report=report,recipient=user,defaults={'sender':request.user,'rationale':data['rationale']})
            if new:
                created+=1
                AuditEvent.objects.create(actor=request.user,service=service,action='report.internal_delivered',object_id=str(row.pk))
        return Response({'created':created,'already_delivered':len(users)-created,'channel':'internal'})

class ReportInbox(Private):
    @extend_schema(parameters=[DeliveryPageInput],responses=OpenApiTypes.OBJECT)
    def get(self,request):
        params=page_input(DeliveryPageInput,request);size=params['page_size']
        query=ReportDelivery.objects.filter(recipient=request.user,recipient__is_active=True,report__service_id__in=scopes(request.user,READ)).select_related('report__service','report__disposition').order_by('-id')
        if 'before' in params:query=query.filter(id__lt=params['before'])
        rows=list(query[:size+1])
        return Response({'results':[{**receipt(r),'service':r.report.service.name,'period':r.report.start,'state':r.report.state,'availability':serialize(r.report)['availability']} for r in rows[:size]],
            'next_before':rows[size-1].pk if len(rows)>size else None})

class ReportAcknowledge(Private):
    @extend_schema(request=ReportReceiptInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        s=ReportReceiptInput(data=request.data);s.is_valid(raise_exception=True)
        original=get_object_or_404(ReportDelivery,pk=pk,recipient=request.user,recipient__is_active=True,report__service_id__in=scopes(request.user,READ))
        Service.objects.select_for_update().get(pk=original.report.service_id)
        require(request.user,original.report.service_id,READ)
        get_object_or_404(get_user_model().objects.select_for_update(),pk=request.user.pk,is_active=True)
        row=ReportDelivery.objects.select_for_update().get(pk=pk)
        available(row.report,s.validated_data['content_hash'])
        if row.acknowledged_at is None:
            row.acknowledged_at=timezone.now();row.save(update_fields=['acknowledged_at'])
            AuditEvent.objects.create(actor=request.user,service_id=row.report.service_id,action='report.read_acknowledged',object_id=str(row.pk))
        return Response(receipt(row))
