"""Cash ledger: school isolation, accountable shifts and append-only movements."""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import CashShift, CashMovement, Service, SchoolMember, SchoolMandate, InstitutionMember
from .school_access import managed_schools
from .governance import managed_institutions, record
from .academic import AcademicView, data
from .admin_serializers import StrictSerializer
from .workflow import Conflict

ZERO=Decimal('0.00')
INCOMING={'collection','fund_in'}

def managers(user):
    return Service.objects.filter(Q(school_id__in=managed_schools(user))|Q(site__campus__institution_id__in=managed_institutions(user)))

def eligible(user):
    # Membership is rechecked on every request, including historical access.
    q=Q(school_id__in=SchoolMember.objects.filter(user=user).values('school_id'))|Q(school__isnull=True,site__campus__institution_id__in=InstitutionMember.objects.filter(user=user).values('institution_id'))
    if SchoolMandate.objects.filter(user=user).exists():q &= Q(school_id__in=managed_schools(user))
    return Service.objects.filter(q)

def shifts(user):
    return CashShift.objects.filter(Q(service__in=managers(user))|Q(responsible=user,service__in=eligible(user))).select_related('service__school','responsible','assigned_by')

def services(user):
    return Service.objects.filter(Q(pk__in=managers(user))|Q(pk__in=shifts(user).values('service_id'))).select_related('school')

def money(value):return str(value.quantize(Decimal('0.01')))
def name(user):return user.get_full_name() or user.username

def balance(shift):
    totals={x['kind']:x['total'] for x in shift.movements.values('kind').annotate(total=Sum('amount'))}
    return (shift.opening or ZERO)+sum((value if kind in INCOMING else -value for kind,value in totals.items()),ZERO)

def movement_item(m):
    return {'id':m.pk,'folio':f'CAJ-{m.pk:08d}','kind':m.kind,'method':m.method,'amount':money(m.amount),'concept':m.concept,'reference':m.reference,'related':m.related_id,'actor':name(m.actor),'created_at':m.created_at}

def shift_item(s,user):
    return {'id':s.pk,'service':s.service_id,'service_name':s.service.name,'school':s.service.school_id,'school_name':s.service.school.name if s.service.school_id else 'Institucional','responsible':s.responsible_id,'responsible_name':name(s.responsible),'assigned_by':name(s.assigned_by),'label':s.label,'starts':s.starts,'ends':s.ends,'state':s.state,'revision':s.revision,'opening':money(s.opening) if s.opening is not None else None,'balance':money(balance(s)),'counted':money(s.counted) if s.counted is not None else None,'expected':money(s.expected) if s.expected is not None else None,'difference':money(s.difference) if s.difference is not None else None,'opened_at':s.opened_at,'closed_at':s.closed_at,'close_reason':s.close_reason,'can_operate':s.responsible_id==user.pk and eligible(user).filter(pk=s.service_id).exists(),'can_manage':managers(user).filter(pk=s.service_id).exists()}

def audit(user,s,action,reason):record(user,s.service.site.campus.institution_id,'cash.'+action,s.pk,reason,service=s.service)
def check_version(s,v):
    if s.revision!=v['revision']:raise Conflict('La caja cambió. Actualice antes de continuar.')
def require_operator(user,s):
    if s.responsible_id!=user.pk or not eligible(user).filter(pk=s.service_id).exists():raise PermissionDenied('Sólo el responsable de este turno puede operar caja.')

def candidates(service):
    users=get_user_model().objects.filter(is_active=True,patient_profile__isnull=True)
    if service.school_id:users=users.filter(schoolmember__school_id=service.school_id)
    else:users=users.filter(institutionmember__institution_id=service.site.campus.institution_id)
    # School directors with legacy memberships cannot operate a foreign school.
    users=users.exclude(Q(schoolmandate__isnull=False)&~Q(pk__in=SchoolMandate.objects.filter(school_id=service.school_id,revoked_at__isnull=True,starts__lte=timezone.localdate(),ends__gte=timezone.localdate()).values('user_id')))
    return users.distinct()

class ShiftInput(StrictSerializer):
    service=serializers.IntegerField(min_value=1)
    responsible=serializers.IntegerField(min_value=1)
    label=serializers.CharField(max_length=100)
    starts=serializers.DateTimeField()
    ends=serializers.DateTimeField()
    client_key=serializers.UUIDField()
    def validate(self,v):
        if v['starts']>=v['ends']:raise ValidationError('El fin debe ser posterior al inicio.')
        return v
class ActionInput(StrictSerializer):
    action=serializers.ChoiceField(choices=['open','close','cancel'])
    revision=serializers.IntegerField(min_value=0)
    amount=serializers.DecimalField(max_digits=12,decimal_places=2,min_value=ZERO,required=False)
    reason=serializers.CharField(max_length=2000,required=False,allow_blank=True,default='')
class MovementInput(StrictSerializer):
    kind=serializers.ChoiceField(choices=['collection','fund_in','withdrawal','refund'])
    amount=serializers.DecimalField(max_digits=12,decimal_places=2,min_value=Decimal('0.01'))
    concept=serializers.CharField(max_length=240)
    reference=serializers.CharField(max_length=100,required=False,allow_blank=True,default='')
    related=serializers.IntegerField(min_value=1,required=False,allow_null=True,default=None)
    client_key=serializers.UUIDField()
    revision=serializers.IntegerField(min_value=0)
class Filters(StrictSerializer):
    service=serializers.IntegerField(min_value=1,required=False)
    state=serializers.ChoiceField(choices=['planned','open','closed','cancelled'],required=False)
    date_from=serializers.DateField(required=False)
    date_to=serializers.DateField(required=False)
    page=serializers.IntegerField(min_value=1,required=False)
    def validate(self,v):
        if v.get('date_from') and v.get('date_to') and v['date_from']>v['date_to']:raise ValidationError('Fechas inválidas.')
        return v

def filtered(request):
    f=Filters(data=request.query_params);f.is_valid(raise_exception=True);v=f.validated_data
    qs=shifts(request.user)
    if 'service' in v:
        get_object_or_404(services(request.user),pk=v['service']);qs=qs.filter(service_id=v['service'])
    if 'state' in v:qs=qs.filter(state=v['state'])
    if 'date_from' in v:qs=qs.filter(starts__date__gte=v['date_from'])
    if 'date_to' in v:qs=qs.filter(starts__date__lte=v['date_to'])
    return qs.order_by('-starts','-id')

class CashServices(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        managed=set(managers(request.user).values_list('id',flat=True))
        return self.page(request,services(request.user).order_by('school_id','name'),lambda s:{'id':s.pk,'name':s.name,'school_name':s.school.name if s.school else 'Institucional','can_manage':s.pk in managed})
class CashCandidates(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        service=get_object_or_404(managers(request.user),pk=pk)
        return self.page(request,candidates(service).order_by('first_name','id'),lambda u:{'id':u.pk,'name':name(u),'username':u.username})
class CashShifts(AcademicView):
    @extend_schema(operation_id="cash_shifts_list",responses=OpenApiTypes.OBJECT)
    def get(self,request):return self.page(request,filtered(request),lambda s:shift_item(s,request.user))
    @extend_schema(request=ShiftInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        v=data(ShiftInput,request)
        service=get_object_or_404(managers(request.user).select_for_update(),pk=v['service'])
        prior=CashShift.objects.filter(client_key=v['client_key']).first()
        if prior:
            if prior.assigned_by_id!=request.user.pk or any(getattr(prior,k+'_id' if k in ('service','responsible') else k)!=value for k,value in v.items()):raise Conflict('Solicitud reutilizada con datos diferentes.')
            return Response(shift_item(prior,request.user))
        get_object_or_404(candidates(service),pk=v['responsible'])
        if v['ends']<=timezone.now():raise ValidationError('El turno debe finalizar en el futuro.')
        if CashShift.objects.filter(service=service,state__in=['planned','open'],starts__lt=v['ends'],ends__gt=v['starts']).exists():raise Conflict('Ya hay un turno programado en este horario para el servicio.')
        try:
            with transaction.atomic():
                s=CashShift.objects.create(**{k:value for k,value in v.items() if k not in ('service','responsible')},service=service,responsible_id=v['responsible'],assigned_by=request.user)
        except IntegrityError:raise Conflict('Solicitud de turno duplicada. Actualice los datos.')
        audit(request.user,s,'assigned',s.label)
        return Response(shift_item(s,request.user),status=201)
class CashDetail(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):return Response(shift_item(get_object_or_404(shifts(request.user),pk=pk),request.user))
    @extend_schema(operation_id="cash_shift_action",request=ActionInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        v=data(ActionInput,request)
        initial=get_object_or_404(shifts(request.user),pk=pk)
        # Consistent service -> shift lock order serializes opening, closing and cash writes.
        Service.objects.select_for_update().get(pk=initial.service_id)
        s=get_object_or_404(shifts(request.user).select_for_update(of=('self',)),pk=pk);check_version(s,v)
        action=v['action']
        if action=='cancel':
            get_object_or_404(managers(request.user),pk=s.service_id)
            if s.state!='planned':raise Conflict('Sólo se cancela un turno sin abrir.')
            if not v['reason']:raise ValidationError('Indique el motivo.')
            s.state='cancelled';s.close_reason=v['reason']
        else:
            require_operator(request.user,s)
            if 'amount' not in v:raise ValidationError('Indique el efectivo contado.')
            if action=='open':
                if s.state!='planned':raise Conflict('El turno ya fue abierto o cancelado.')
                if not s.starts<=timezone.now()<s.ends:raise ValidationError('Abra dentro del horario programado.')
                if CashShift.objects.filter(service=s.service,state='open').exists():raise Conflict('Cierre el turno anterior antes de abrir éste.')
                s.opening=v['amount'];s.opened_at=timezone.now();s.state='open'
            else:
                if s.state!='open':raise Conflict('El turno no está abierto.')
                s.expected=balance(s);s.counted=v['amount'];s.difference=s.counted-s.expected
                if s.difference and not v['reason']:raise ValidationError('Explique la diferencia de arqueo.')
                s.close_reason=v['reason'];s.closed_at=timezone.now();s.state='closed'
        s.revision+=1;s.save();audit(request.user,s,action,v['reason'] or action)
        return Response(shift_item(s,request.user))
class CashMovements(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        s=get_object_or_404(shifts(request.user),pk=pk)
        return self.page(request,s.movements.select_related('actor').order_by('-id'),movement_item)
    @extend_schema(request=MovementInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        v=data(MovementInput,request)
        initial=get_object_or_404(shifts(request.user),pk=pk)
        Service.objects.select_for_update().get(pk=initial.service_id)
        s=get_object_or_404(shifts(request.user).select_for_update(of=('self',)),pk=pk);require_operator(request.user,s)
        previous=CashMovement.objects.filter(client_key=v['client_key']).first()
        if previous:
            if previous.shift_id!=s.pk or previous.actor_id!=request.user.pk or any(getattr(previous,'related_id' if k=='related' else k)!=value for k,value in v.items() if k not in ('revision','client_key')):raise Conflict('Solicitud reutilizada con datos diferentes.')
            return Response(movement_item(previous))
        check_version(s,v)
        if s.state!='open':raise Conflict('Abra el turno antes de registrar movimientos.')
        if v['kind']=='refund':
            original=get_object_or_404(CashMovement,pk=v['related'],shift__service=s.service,kind='collection')
            refunded=CashMovement.objects.filter(related=original,kind='refund').aggregate(total=Sum('amount'))['total'] or ZERO
            if v['amount']>original.amount-refunded:raise ValidationError('La devolución excede el cobro pendiente de devolver.')
        elif v['related'] is not None:raise ValidationError('Sólo las devoluciones requieren un cobro original.')
        if v['kind'] not in INCOMING and v['amount']>balance(s):raise ValidationError('No hay efectivo suficiente en caja.')
        try:
            with transaction.atomic():
                m=CashMovement.objects.create(shift=s,actor=request.user,**{('related_id' if k=='related' else k):value for k,value in v.items() if k!='revision'})
        except IntegrityError:raise Conflict('Solicitud de movimiento duplicada. Actualice los datos.')
        s.revision+=1;s.save(update_fields=['revision']);audit(request.user,s,'movement',f'{m.pk}: {m.kind} {money(m.amount)} MXN · {m.concept}')
        return Response(movement_item(m),status=201)
class CashSummary(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        qs=filtered(request)
        totals={r['kind']:money(r['total']) for r in CashMovement.objects.filter(shift__in=qs).values('kind').annotate(total=Sum('amount'))}
        closed=qs.filter(state='closed')
        return Response({'currency':'MXN','basis':'Turnos por fecha de inicio; movimientos completos de esos turnos. Sin fechas: todo el historial autorizado.','totals':totals,'open_shifts':qs.filter(state='open').count(),'closed_shifts':closed.count(),'differences':money(closed.aggregate(total=Sum('difference'))['total'] or ZERO),'with_difference':closed.exclude(difference=0).count(),'cash_in_open_shifts':money(sum((balance(s) for s in qs.filter(state='open')),ZERO))})
