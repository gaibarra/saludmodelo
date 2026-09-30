from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from .models import InstitutionMandate, Service, GovernanceEvent, SchoolMandate
from .access import scopes, READ, REVIEW

EDIT_HELP = {'manager', 'coordinator', 'contributor'}

def managed_institutions(user):
    if not user.is_authenticated:
        return InstitutionMandate.objects.none().values_list('institution_id', flat=True)
    if SchoolMandate.objects.filter(user=user).exists():
        return InstitutionMandate.objects.none().values_list('institution_id',flat=True)
    today = timezone.localdate()
    return InstitutionMandate.objects.filter(user=user, starts__lte=today, ends__gte=today).values_list('institution_id', flat=True)

def require_institution(user, institution_id):
    if institution_id not in managed_institutions(user):
        raise PermissionDenied('Requiere un nombramiento institucional vigente de Dirección.')

def managed_services(user):
    from .school_access import managed_schools
    return Service.objects.filter(Q(site__campus__institution_id__in=managed_institutions(user)) | Q(pk__in=scopes(user, {'director'})) | Q(school_id__in=managed_schools(user)))

def can_manage(user, service):
    return managed_services(user).filter(pk=service.pk).exists()

def require_manage(user, service):
    if not can_manage(user, service):
        raise PermissionDenied('Dirección debe autorizar esta acción dentro de su alcance.')

def questionnaire_services(user):
    return Service.objects.filter(Q(pk__in=scopes(user, EDIT_HELP | REVIEW | {'director'})) | Q(pk__in=managed_services(user)))

def record(user, institution_id, action, object_id, rationale, service=None):
    return GovernanceEvent.objects.create(actor=user, institution_id=institution_id, action=action, object_id=str(object_id), rationale=rationale, service=service)
