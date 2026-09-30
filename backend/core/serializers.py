from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from .models import *
class ServiceSerializer(serializers.ModelSerializer):
    site_name=serializers.CharField(source='site.name',read_only=True)
    class Meta:model=Service;fields=['id','name','site_name','kind','confirmed']
class SaveSerializer(serializers.Serializer):
    version=serializers.IntegerField(min_value=0)
    content=serializers.CharField(max_length=20000,allow_blank=True)
    knowledge=serializers.ChoiceField(choices=['known','unknown','absent','unconfirmed','not_applicable'])
    def validate(self,v):
        if v['knowledge']=='not_applicable' and not v['content'].strip():raise serializers.ValidationError('Justifique por qué considera que no aplica.')
        return v
class TransitionSerializer(serializers.Serializer):
    version=serializers.IntegerField(min_value=1)
    target=serializers.ChoiceField(choices=['submitted','validated','returned'])
    rationale=serializers.CharField(max_length=5000,allow_blank=True,default='')
class AnswerSerializer(serializers.ModelSerializer):
    upload_formats=serializers.SerializerMethodField()
    def get_upload_formats(self,obj)->list[str]:
        from django.conf import settings
        return ['txt','csv']+(['pdf','docx','xlsx'] if settings.DOCUMENT_SIGNATURES else [])+(['png','jpg','jpeg'] if settings.DOCUMENT_SIGNATURES and settings.DOCUMENT_OCR_RUNTIME else [])
    questionnaire=serializers.IntegerField(source='instance_id')
    can_ai=serializers.SerializerMethodField()
    def get_can_ai(self,obj)->bool:
        from .access import scopes,WRITE
        return obj.instance.service_id in scopes(self.context["request"].user,WRITE)
    can_consult=serializers.SerializerMethodField()
    def get_can_consult(self,obj)->bool:
        from .consultations import CONSULT_ROLES
        from .access import scopes
        return obj.instance.service_id in scopes(self.context['request'].user,CONSULT_ROLES)
    original=serializers.CharField(source='instance.question_version.source.text')
    source=serializers.CharField(source='instance.question_version.source.locator')
    question_version=serializers.IntegerField(source='instance.question_version.version')
    service=serializers.IntegerField(source='instance.service_id')
    help=serializers.JSONField(source='instance.published_help.content')
    revisions=serializers.SerializerMethodField()
    evidence=serializers.SerializerMethodField()
    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_revisions(self,a):return list(a.revisions.order_by('-version').values('version','content','knowledge','author_id','created_at'))
    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_evidence(self,a):
        from .access import scopes
        from .document_views import DOCUMENT_ROLES
        if a.instance.service_id not in scopes(self.context['request'].user,DOCUMENT_ROLES):return []
        return [{'id':str(e.pk),'name':e.original_name,'state':e.state,'download_allowed':(not e.scan_required and e.format in {'txt','csv'}) or e.security_state=='clean','url':f'/api/v1/evidence/{e.pk}/download/'} for e in a.evidencedocument_set.all()]
    class Meta:model=Answer;fields=['id','upload_formats','questionnaire','can_ai','can_consult','version','etag','state','original','source','question_version','service','help','revisions','evidence']
class TaskSerializer(serializers.ModelSerializer):
    class Meta:model=Task;fields=['id','service','answer','title','owner','starts','due','state']

class SessionSerializer(serializers.Serializer):
    password_only_demo=serializers.BooleanField(required=False)
    mfa_required=serializers.BooleanField()
    mfa_enabled=serializers.BooleanField()
    mfa_verified=serializers.BooleanField()
    mfa_configured=serializers.BooleanField(required=False)
    recovery_remaining=serializers.IntegerField(required=False)
    csrf=serializers.CharField()
    authenticated=serializers.BooleanField()
    username=serializers.CharField()
class LoginSerializer(serializers.Serializer):
    username=serializers.CharField(max_length=150)
    password=serializers.CharField(max_length=256,write_only=True,trim_whitespace=False)
class MetricSerializer(serializers.Serializer):
    numerator=serializers.IntegerField()
    denominator=serializers.IntegerField()
    pending=serializers.IntegerField()
    label=serializers.CharField()
    records_url=serializers.CharField()
class DashboardSerializer(serializers.Serializer):
    validated=MetricSerializer()
    tasks_pending=serializers.IntegerField()
    updated_at=serializers.DateTimeField()
    clinical_scope=serializers.CharField()
class UploadSerializer(serializers.Serializer):
    version=serializers.IntegerField(min_value=0)
    file=serializers.FileField()
