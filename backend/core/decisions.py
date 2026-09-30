"""Scoped decision register; records resolutions without executing them."""
import hashlib,json
from datetime import date
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .access import scopes,require,READ
from .governance import require_manage,can_manage
from .admin_serializers import StrictSerializer
from .models import Service,Task,Decision,DecisionEvent,AuditEvent
from .tracking.workflow import WORK
from .workflow import Conflict

class NewDecision(StrictSerializer):
    title=serializers.CharField(max_length=250)
    question=serializers.CharField(max_length=5000)
    alternatives=serializers.CharField(max_length=5000)
    due=serializers.DateField()
    task=serializers.IntegerField(min_value=1,allow_null=True,default=None)
    client_key=serializers.UUIDField()
    def validate_due(self,value):
        if value<date(2026,10,1):raise serializers.ValidationError('El plan comienza el 1 de octubre de 2026.')
        return value
class DecisionInput(StrictSerializer):
    version=serializers.IntegerField(min_value=1)
    action=serializers.ChoiceField(choices=['resolve','dismiss','withdraw','reopen'])
    note=serializers.CharField(max_length=5000)
    task_version=serializers.IntegerField(min_value=0,allow_null=True,default=None)
    client_key=serializers.UUIDField()

def snap(d):
    return {'id':d.pk,'title':d.title,'question':d.question,'alternatives':d.alternatives,'due':str(d.due),'state':d.state,'etag':d.etag,'resolution':d.resolution,'resolved_by':d.resolved_by_id,'task_id':d.task_id,'task_snapshot':d.task_snapshot}
def serialize(d,user,history=False):
    task=Task.objects.filter(pk=d.task_id,service=d.service).values('id','title','etag','state').first() if d.task_id else None
    return {**snap(d),'created_at':d.created_at,'resolved_at':d.resolved_at,'requested_by':d.requested_by_id,'task_current':task,
            'can_resolve':can_manage(user,d.service) and d.requested_by_id!=user.pk,'can_manage':can_manage(user,d.service),
            'can_withdraw':d.requested_by_id==user.pk or can_manage(user,d.service),
            **({'events':list(d.events.order_by('version').values('version','action','note','actor_id','snapshot','created_at'))} if history else {})}
def fingerprint(data):return hashlib.sha256(json.dumps(data,sort_keys=True,cls=DjangoJSONEncoder).encode()).hexdigest()
def replay(user,service,key,payload):
    event=DecisionEvent.objects.filter(service=service,actor=user,client_key=key).first()
    if event and event.payload_hash!=fingerprint(payload):raise serializers.ValidationError('Clave usada para otra operación.')
    return event.decision if event else None

def record(user,d,key,payload,action,note):
    DecisionEvent.objects.create(service=d.service,decision=d,actor=user,client_key=key,payload_hash=fingerprint(payload),version=d.etag,action=action,note=note,snapshot=snap(d))
    AuditEvent.objects.create(actor=user,service=d.service,action='decision.'+action,object_id=str(d.pk))

@transaction.atomic
def create(user,service_id,data):
    service=get_object_or_404(Service.objects.select_for_update(),pk=service_id,pk__in=scopes(user,WORK|{'director'}))
    require(user,service.pk,WORK|{'director'})
    payload={'action':'create',**data};key=data['client_key']
    existing=replay(user,service,key,payload)
    if existing:return existing
    task=get_object_or_404(Task.objects.select_for_update(),pk=data['task'],service=service) if data['task'] else None
    d=Decision.objects.create(service=service,task=task,requested_by=user,title=data['title'],question=data['question'],alternatives=data['alternatives'],due=data['due'],task_snapshot={'id':task.pk,'title':task.title,'etag':task.etag,'state':task.state} if task else {})
    record(user,d,key,payload,'create',data['question']);return d

@transaction.atomic
def change(user,pk,data):
    original=get_object_or_404(Decision,pk=pk,service_id__in=scopes(user,READ))
    service=Service.objects.select_for_update().get(pk=original.service_id)
    require(user,service.pk,READ)
    d=Decision.objects.select_for_update().get(pk=pk)
    action=data['action']
    if action in ['resolve','dismiss','reopen'] or d.requested_by_id!=user.pk:require_manage(user,service)
    if action in ['resolve','dismiss'] and d.requested_by_id==user.pk:raise serializers.ValidationError('Otra persona de Dirección debe resolver la solicitud.')
    payload={'decision':pk,**data};key=data['client_key']
    existing=replay(user,service,key,payload)
    if existing:return existing
    if d.etag!=data['version']:raise Conflict()
    if action=='reopen':
        if d.state=='pending':raise serializers.ValidationError('La decisión ya está pendiente.')
        d.state='pending';d.resolution='';d.resolved_by=None;d.resolved_at=None
    else:
        if d.state!='pending':raise serializers.ValidationError('La decisión ya fue cerrada; revise su historial.')
        if d.task_id:
            task=Task.objects.select_for_update().get(pk=d.task_id,service=service)
            if task.etag!=data['task_version']:raise Conflict()
        elif data['task_version'] is not None:raise serializers.ValidationError('La decisión no está vinculada a una tarea.')
        d.state={'resolve':'resolved','dismiss':'dismissed','withdraw':'withdrawn'}[action]
        d.resolution=data['note'];d.resolved_by=user;d.resolved_at=timezone.now()
    d.etag+=1;d.save()
    record(user,d,key,payload,action,data['note']);return d

class Private(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs);response['Cache-Control']='private, no-store';return response
class DecisionList(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,service):
        service=get_object_or_404(Service,pk=service,pk__in=scopes(request.user,READ))
        rows=list(Decision.objects.filter(service=service).select_related('service').order_by('-id')[:501])
        if len(rows)>500:raise serializers.ValidationError('Más de 500 decisiones; se requiere ampliar paginación antes de mostrar este registro.')
        from .decision_notices import board
        return Response({'notices':board(request.user,service,rows),'can_create':scopes(request.user,WORK|{'director'}).filter(service_id=service.pk).exists(),'decisions':[serialize(d,request.user) for d in rows]})
    @extend_schema(request=NewDecision,responses=OpenApiTypes.OBJECT)
    def post(self,request,service):
        s=NewDecision(data=request.data);s.is_valid(raise_exception=True)
        return Response(serialize(create(request.user,service,s.validated_data),request.user,True),status=201)
class DecisionDetail(Private):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        d=get_object_or_404(Decision,pk=pk,service_id__in=scopes(request.user,READ))
        return Response(serialize(d,request.user,True))
    @extend_schema(request=DecisionInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        s=DecisionInput(data=request.data);s.is_valid(raise_exception=True)
        return Response(serialize(change(request.user,pk,s.validated_data),request.user,True))
