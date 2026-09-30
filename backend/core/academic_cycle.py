"""Common lock order for academic mutations: cycle -> student -> service -> record."""
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from .models import AcademicCycle

def lock_open(cycle_id):
    cycle=get_object_or_404(AcademicCycle.objects.select_for_update(),pk=cycle_id)
    if cycle.closed_at:raise ValidationError('El ciclo está cerrado. Dirección debe reabrirlo con un motivo antes de modificar registros.')
    return cycle

def changed(cycle):
    cycle.revision+=1
    cycle.save(update_fields=['revision'])
