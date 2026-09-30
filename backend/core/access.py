from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from .models import RoleAssignment,Service,SchoolMandate
from django.db.models import Q,F
READ={'director','coordinator','manager','contributor','compliance','clinical','auditor'}
WRITE={'manager','contributor'}
REVIEW={'manager','compliance','clinical'}
def scopes(user,roles=READ):
    if not user.is_authenticated or not user.is_active:return RoleAssignment.objects.none().values_list('service_id',flat=True)
    from .school_access import managed_schools
    today=timezone.localdate()
    assignments=RoleAssignment.objects.filter(user=user,role__in=roles,starts__lte=today,ends__gte=today,revoked_at__isnull=True)
    if SchoolMandate.objects.filter(user=user).exists():assignments=assignments.filter(service__school_id__in=managed_schools(user))
    predicate=Q(pk__in=assignments.values('service_id'))
    if 'director' in roles:predicate|=Q(school_id__in=managed_schools(user))
    return Service.objects.filter(predicate).annotate(service_id=F('id')).values_list('service_id',flat=True)

def require(user,service,roles):
    if not scopes(user,roles).filter(service_id=service).exists():
        raise PermissionDenied('No tiene permiso vigente para esta acción y servicio.')
