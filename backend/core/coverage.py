"""Current role-linked coverage; never changes task ownership."""
from django.db.models import F
from django.utils import timezone
from .models import RoleAssignment

WORK_ROLES={'manager','coordinator','contributor','clinical','compliance'}
def coverages(service,holder,roles=WORK_ROLES):
    day=timezone.localdate()
    return RoleAssignment.objects.filter(service_id=service,substitutes__user_id=holder,substitutes__service_id=service,substitutes__substitutes__isnull=True,substitutes__role=F('role'),substitutes__revoked_at__isnull=True,substitutes__starts__lte=day,substitutes__ends__gte=day,role__in=roles,starts__lte=day,ends__gte=day,revoked_at__isnull=True,user__is_active=True).exclude(user_id=holder)

def covering(user,service,holder,roles=WORK_ROLES):
    return coverages(service,holder,roles).filter(user=user).exists()

def coverage_event_valid(event):
    if not event.coverage_id:return True
    return coverages(event.task.service_id,event.task.owner_id).filter(pk=event.coverage_id,user_id=event.recipient_id).exists()
