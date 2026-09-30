"""On-demand internal notices. No deliveries, scheduler or changes to decisions."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .access import READ,require,scopes
from .coverage import covering,coverages,WORK_ROLES
from .governance import can_manage
from .admin_serializers import StrictSerializer
from .models import Decision,DecisionNoticeReceipt,Service,WorkPlan,AuditEvent
from .decisions import Private
from .tracking import workflow as calendar
from .workflow import Conflict

def notice(d,user,plan,now):
    if not plan or not plan.confirmed_by_id or d.state!='pending' or (d.requested_by_id!=user.pk and not can_manage(user,d.service) and not covering(user,d.service_id,d.requested_by_id,WORK_ROLES|{'director'})):
        return None
    if now<calendar.START or now<d.due or now.weekday() not in plan.weekdays or str(now) in plan.holidays:return None
    delay=calendar.working_days(d.due,now,plan)
    stage=3 if delay>=3 else 2 if delay>=2 else 0
    receipt=DecisionNoticeReceipt.objects.filter(decision=d,recipient=user,decision_version=d.etag,calendar_version=plan.etag,stage=stage).first()
    return {'coverage_ids':list(coverages(d.service_id,d.requested_by_id,WORK_ROLES|{'director'}).filter(user=user).values_list('id',flat=True)),'decision_id':d.pk,'title':d.title,'due':d.due,'decision_version':d.etag,'calendar_version':plan.etag,'stage':stage,'working_days_late':delay,'acknowledged_at':receipt.created_at if receipt else None}

def board(user,service,decisions):
    plan=WorkPlan.objects.filter(institution=service.site.campus.institution).first()
    now=calendar.today(service)
    return {'calendar_confirmed':bool(plan and plan.confirmed_by_id),'observed_day':now,'timezone':service.site.timezone,'items':[item for d in decisions if (item:=notice(d,user,plan,now)) is not None]}

class DecisionNoticeInput(StrictSerializer):
    decision_version=serializers.IntegerField(min_value=1)
    calendar_version=serializers.IntegerField(min_value=0)
    stage=serializers.ChoiceField(choices=[0,2,3])

class DecisionNoticeAcknowledge(Private):
    @extend_schema(request=DecisionNoticeInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        s=DecisionNoticeInput(data=request.data);s.is_valid(raise_exception=True)
        original=get_object_or_404(Decision,pk=pk,service_id__in=scopes(request.user,READ))
        service=Service.objects.select_for_update().get(pk=original.service_id)
        require(request.user,service.pk,READ)
        d=Decision.objects.get(pk=pk)
        plan=WorkPlan.objects.select_for_update().filter(institution=service.site.campus.institution).first()
        item=notice(d,request.user,plan,calendar.today(service))
        if item is None or any(item[k]!=v for k,v in s.validated_data.items()):raise Conflict()
        _,created=DecisionNoticeReceipt.objects.get_or_create(decision=d,recipient=request.user,defaults={'coverage_ids':item['coverage_ids']},**s.validated_data)
        if created:AuditEvent.objects.create(actor=request.user,service=service,action='decision.notice_acknowledged',object_id=str(d.pk))
        return Response(notice(d,request.user,plan,calendar.today(service)))
