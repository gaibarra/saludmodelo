"""Read-only public facts, independent of operational service confirmation."""
from .models import InstitutionalService

def published_services():
    return InstitutionalService.objects.filter(published=True).select_related('service__school').order_by('public_name','id')

def public_item(row):
    return {'code':row.code,'name':row.public_name,'area':row.area,'additional_areas':row.additional_areas,'additional_sources':row.additional_sources,'school':row.service.school_id,
            'school_name':row.service.school.name if row.service.school_id else '',
            'description':row.description,'audience':row.audience,'schedule':row.schedule,
            'contacts':row.contacts,'notes':row.notes,'location_note':row.location_note,
            'source_url':row.source_url,'source_checked_on':row.source_checked_on}
