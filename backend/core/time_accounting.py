"""Effective time with immutable originals and correction versions."""
from django.db.models import OuterRef,Subquery,Sum,IntegerField,F
from django.db.models.functions import Coalesce
from .models import TimeCorrection

def effective(entries):
    latest=TimeCorrection.objects.filter(entry_id=OuterRef('pk')).order_by('-version')
    return entries.annotate(effective_minutes=Coalesce(Subquery(latest.values('minutes')[:1]),F('minutes'),output_field=IntegerField()),correction_version=Coalesce(Subquery(latest.values('version')[:1]),0))

def total(entries):
    return effective(entries).aggregate(total=Sum('effective_minutes'))['total'] or 0
