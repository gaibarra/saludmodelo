"""Institution-wide daily planning; no clinical/absence reasons or automatic task changes."""
import hashlib,json
from datetime import date,timedelta
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema,OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Institution,Service,RoleAssignment,CapacityDay,CapacityAllocation,CapacityChange,GovernanceEvent
from .governance import require_institution,managed_institutions
from .admin_serializers import StrictSerializer
from .tracking.workflow import WORK
from .workflow import Conflict

class AllocationInput(StrictSerializer):
    service=serializers.IntegerField(min_value=1)
    minutes=serializers.IntegerField(min_value=1,max_value=1440)
class CapacityInput(StrictSerializer):
    person=serializers.IntegerField(min_value=1)
    day=serializers.DateField()
    version=serializers.IntegerField(min_value=0)
    minutes=serializers.IntegerField(min_value=0,max_value=1440)
    unavailable_minutes=serializers.IntegerField(min_value=0,max_value=1440)
    allocations=AllocationInput(many=True)
    rationale=serializers.CharField(max_length=3000)
    client_key=serializers.UUIDField()
    def validate(self,data):
        if data['day']<date(2026,10,1):raise serializers.ValidationError('El plan comienza el 1 de octubre de 2026.')
        rows=data['allocations']
        if len(rows)>20 or len({a['service'] for a in rows})!=len(rows):raise serializers.ValidationError('Use como máximo veinte servicios distintos.')
        if data['unavailable_minutes']>data['minutes'] or sum(a['minutes'] for a in rows)>data['minutes']-data['unavailable_minutes']:raise serializers.ValidationError('La distribución excede la capacidad disponible después de ausencias.')
        return data
class CapacityReviewInput(StrictSerializer):
    approve=serializers.BooleanField()
    rationale=serializers.CharField(max_length=3000)
class PeriodInput(StrictSerializer):
    start=serializers.DateField(required=False)
    def validate_start(self,value):
        if not date(2026,10,1)<=value<=date(9999,12,24):raise serializers.ValidationError('Fecha fuera del intervalo de planificación.')
        return value

def assignments(institution,person,day):
    return RoleAssignment.objects.filter(service__site__campus__institution_id=institution,user_id=person,user__is_active=True,role__in=WORK|{'director'},revoked_at__isnull=True,starts__lte=day,ends__gte=day)
def validate_person(institution,person,day,rows,minutes,unavailable):
    if not assignments(institution,person,day).exists() and not (minutes==0 and unavailable==0 and not rows and CapacityDay.objects.filter(institution_id=institution,person_id=person,day=day).exists()):raise serializers.ValidationError('La persona necesita un nombramiento de trabajo vigente para ese día.')
    valid=set(assignments(institution,person,day).values_list('service_id',flat=True))
    if not {r['service'] for r in rows}<=valid:raise serializers.ValidationError('Servicio ajeno o sin nombramiento vigente para la persona y fecha.')
def state(day):
    return {'etag':day.etag,'confirmed':day.confirmed,'minutes':day.minutes,'unavailable_minutes':day.unavailable_minutes,'allocations':list(day.allocations.order_by('service_id').values('service_id','minutes'))}
def fingerprint(data):return hashlib.sha256(json.dumps(data,sort_keys=True,cls=DjangoJSONEncoder).encode()).hexdigest()
def event(user,institution,action,change,rationale):
    GovernanceEvent.objects.create(institution_id=institution,actor=user,action=action,object_id=str(change.pk),rationale=rationale)

@transaction.atomic
def propose(user,institution,data):
    require_institution(user,institution)
    Institution.objects.select_for_update().get(pk=institution)
    require_institution(user,institution)
    existing=CapacityChange.objects.filter(institution_id=institution,requested_by=user,client_key=data['client_key']).first()
    digest=fingerprint(data)
    if existing:
        if existing.payload_hash!=digest:raise serializers.ValidationError('Clave usada con otra propuesta.')
        return existing
    validate_person(institution,data['person'],data['day'],data['allocations'],data['minutes'],data['unavailable_minutes'])
    day,_=CapacityDay.objects.get_or_create(institution_id=institution,person_id=data['person'],day=data['day'])
    if day.etag!=data['version']:raise Conflict()
    proposal={k:data[k] for k in ['minutes','unavailable_minutes','allocations']}
    change=CapacityChange.objects.create(capacity=day,institution_id=institution,requested_by=user,client_key=data['client_key'],payload_hash=digest,expected_etag=day.etag,previous=state(day),proposal=proposal,rationale=data['rationale'])
    event(user,institution,'capacity.proposed',change,data['rationale']);return change

@transaction.atomic
def review(user,pk,data):
    original=get_object_or_404(CapacityChange,pk=pk,institution_id__in=managed_institutions(user))
    Institution.objects.select_for_update().get(pk=original.institution_id)
    require_institution(user,original.institution_id)
    change=CapacityChange.objects.select_for_update().get(pk=pk)
    if change.requested_by_id==user.pk:raise serializers.ValidationError('Otra persona con mandato institucional debe revisar la propuesta.')
    target='approved' if data['approve'] else 'rejected'
    if change.state!='pending':
        if change.state==target and change.reviewed_by_id==user.pk and change.review_reason==data['rationale']:return change
        raise Conflict()
    day=CapacityDay.objects.select_for_update().get(pk=change.capacity_id)
    if data['approve']:
        if day.etag!=change.expected_etag:raise Conflict()
        checked=CapacityInput(data={'person':day.person_id,'day':day.day,'version':change.expected_etag,'rationale':change.rationale,'client_key':change.client_key,**change.proposal})
        checked.is_valid(raise_exception=True)
        if fingerprint(checked.validated_data)!=change.payload_hash:raise serializers.ValidationError('La propuesta no coincide con su registro original.')
        validate_person(day.institution_id,day.person_id,day.day,change.proposal['allocations'],change.proposal['minutes'],change.proposal['unavailable_minutes'])
        day.minutes=change.proposal['minutes'];day.unavailable_minutes=change.proposal['unavailable_minutes'];day.confirmed=True;day.etag+=1;day.save()
        # Current allocation rows are a projection; immutable proposals retain every approved version.
        day.allocations.all().delete()
        CapacityAllocation.objects.bulk_create([CapacityAllocation(capacity=day,service_id=r['service'],minutes=r['minutes']) for r in change.proposal['allocations']])
    change.state=target;change.reviewed_by=user;change.review_reason=data['rationale'];change.reviewed_at=timezone.now();change.save()
    event(user,day.institution_id,'capacity.'+target,change,data['rationale']);return change

def serialize_change(change):
    return {'id':change.pk,'capacity_id':change.capacity_id,'expected_etag':change.expected_etag,'requested_by':change.requested_by_id,'state':change.state,'proposal':change.proposal,'previous':change.previous,'rationale':change.rationale,'reviewed_by':change.reviewed_by_id,'review_reason':change.review_reason,'created_at':change.created_at,'reviewed_at':change.reviewed_at}
class Private(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs);response['Cache-Control']='private, no-store';return response
class Institutions(Private):
    @extend_schema(operation_id="capacity_managed_institutions",responses=OpenApiTypes.OBJECT)
    def get(self,request):return Response(list(Institution.objects.filter(pk__in=managed_institutions(request.user)).order_by('id').values('id','name')))
class CapacityBoard(Private):
    @extend_schema(operation_id='capacity_weekly_board',parameters=[OpenApiParameter('start',OpenApiTypes.DATE)],responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def get(self,request,institution):
        require_institution(request.user,institution)
        Institution.objects.select_for_update().get(pk=institution)
        require_institution(request.user,institution)
        params=PeriodInput(data=request.query_params);params.is_valid(raise_exception=True)
        start=params.validated_data.get('start',max(date(2026,10,1),timezone.localdate()));end=start+timedelta(days=7)
        days=list(CapacityDay.objects.filter(institution_id=institution,day__gte=start,day__lt=end).select_related('person').prefetch_related('allocations').order_by('day','person_id')[:501])
        if len(days)>500:raise serializers.ValidationError('La semana supera 500 registros; requiere paginación ampliada.')
        changes=list(CapacityChange.objects.filter(capacity__in=days).order_by('-id')[:501])
        if len(changes)>500:raise serializers.ValidationError('Más de 500 cambios; requiere paginación ampliada antes de mostrar la historia.')
        rows=[]
        for day in days:
            current=state(day);valid=set(assignments(institution,day.person_id,day.day).values_list('service_id',flat=True));allocated=sum(a['minutes'] for a in current['allocations'])
            rows.append({'id':day.pk,'person':day.person_id,'name':day.person.username,'day':day.day,**current,'available_minutes':day.minutes-day.unavailable_minutes if day.confirmed else None,'unallocated_minutes':day.minutes-day.unavailable_minutes-allocated if day.confirmed else None,'needs_review':(not valid and day.minutes>0) or any(a['service_id'] not in valid for a in current['allocations'])})
        people=RoleAssignment.objects.filter(service__site__campus__institution_id=institution,user__is_active=True,role__in=WORK|{'director'},revoked_at__isnull=True,starts__lt=end,ends__gte=start).order_by('user_id').values('user_id','user__username').distinct()
        return Response({'start':start,'end_exclusive':end,'user_id':request.user.pk,'days':rows,'changes':[serialize_change(c) for c in changes],'people':list({p['user_id']:p for p in list(people)+[{'user_id':d.person_id,'user__username':d.person.username} for d in days]}.values()),'services':list(Service.objects.filter(site__campus__institution_id=institution).order_by('id').values('id','name')),'scope':'institution_only','reference_hours':{'base':295,'reserve':59,'total':354,'status':'provisional_reference_not_multiplied_or_committed'}})
    @extend_schema(request=CapacityInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,institution):
        s=CapacityInput(data=request.data);s.is_valid(raise_exception=True)
        return Response(serialize_change(propose(request.user,institution,s.validated_data)),status=201)
class CapacityReview(Private):
    @extend_schema(request=CapacityReviewInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        s=CapacityReviewInput(data=request.data);s.is_valid(raise_exception=True)
        return Response(serialize_change(review(request.user,pk,s.validated_data)))
