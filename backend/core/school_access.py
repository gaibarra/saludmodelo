"""Independent school administration. Inter-school access is prohibited."""
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied,ValidationError
from .models import School,SchoolMandate,SchoolAcademicGrant

def managed_schools(user):
    today=timezone.localdate()
    return SchoolMandate.objects.filter(user=user,starts__lte=today,ends__gte=today,revoked_at__isnull=True).values_list('school_id',flat=True) if user.is_authenticated and user.is_active else SchoolMandate.objects.none().values_list('school_id',flat=True)

def shared_schools(user):
    # Historical grants are retained but never confer access.
    return SchoolAcademicGrant.objects.none().values_list('school_id',flat=True)

def owned(user,prefix='',read=False):
    from .governance import managed_institutions
    q=Q(**{prefix+'institution_id__in':managed_institutions(user)})|Q(**{prefix+'school_id__in':managed_schools(user)})
    if read:q|=Q(**{prefix+'school_id__in':shared_schools(user)})
    return q

def can_manage_academic(user,obj):
    from .governance import managed_institutions
    return obj.institution_id in managed_institutions(user) or (obj.school_id is not None and obj.school_id in managed_schools(user))

def can_read_academic(user,obj):
    return can_manage_academic(user,obj) or (obj.school_id is not None and obj.school_id in shared_schools(user))

def require_academic(user,obj):
    if not can_manage_academic(user,obj):raise PermissionDenied('Requiere Dirección vigente de la escuela propietaria.')

def require_owner(user,institution,school):
    from .governance import require_institution
    if school is None:
        require_institution(user,institution)
        if School.objects.filter(institution_id=institution).exists():raise ValidationError('Seleccione la escuela propietaria.')
    else:
        try:obj=School.objects.get(pk=school,institution_id=institution)
        except School.DoesNotExist:raise ValidationError('Escuela e institución incompatibles.')
        if school not in managed_schools(user):require_institution(user,institution)
