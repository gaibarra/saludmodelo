"""Bounded keyset pages for report histories; never loads an entire archive."""
from rest_framework import serializers
from .admin_serializers import StrictSerializer

class ReportHistoryPageInput(StrictSerializer):
    page_size=serializers.IntegerField(default=50,min_value=1,max_value=100)
    before=serializers.IntegerField(required=False,min_value=1,max_value=9223372036854775807)

class SavedReportPageInput(ReportHistoryPageInput):
    start=serializers.DateField(required=False)
    state=serializers.ChoiceField(choices=['pending','approved','rejected'],required=False)
    retained_only=serializers.BooleanField(default=False)
    exclude=serializers.IntegerField(required=False,min_value=1,max_value=9223372036854775807)

def parameters(cls,request):
    if any(len(request.query_params.getlist(key))!=1 for key in request.query_params):
        raise serializers.ValidationError('No repita parámetros de consulta.')
    form=cls(data=request.query_params);form.is_valid(raise_exception=True)
    return form.validated_data

def page(query,params):
    if 'before' in params:query=query.filter(pk__lt=params['before'])
    size=params['page_size'];rows=list(query.order_by('-pk')[:size+1])
    return rows[:size],rows[size-1].pk if len(rows)>size else None
