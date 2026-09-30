from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import ClarificationRequest, QuestionnaireInstance
from .access import scopes, REVIEW
from .admin_serializers import StrictSerializer
from .consultations import CONSULT_ROLES, visible, recipients, open_request, post_message, resolve

class RequestInput(StrictSerializer):
    instance=serializers.IntegerField(min_value=1)
    assigned_to=serializers.IntegerField(min_value=1)
    question=serializers.CharField(max_length=5000)
    due=serializers.DateField()
    client_key=serializers.UUIDField()
class MessageInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    body=serializers.CharField(max_length=5000)
    client_key=serializers.UUIDField()
class ResolutionInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
    rationale=serializers.CharField(max_length=5000)
class RequestSerializer(serializers.ModelSerializer):
    original=serializers.CharField(source='instance.question_version.source.text')
    service_name=serializers.CharField(source='instance.service.name')
    opened_by_name=serializers.CharField(source='opened_by.username')
    assigned_to_name=serializers.CharField(source='assigned_to.username')
    help_version=serializers.IntegerField(source='help_revision.number',default=None,allow_null=True)
    answer_version=serializers.IntegerField(source='answer_revision.version',default=None,allow_null=True)
    messages=serializers.SerializerMethodField()
    can_reply=serializers.SerializerMethodField()
    can_resolve=serializers.SerializerMethodField()
    def get_messages(self,obj)->list[dict]:
        return [{'id':m.pk,'author':m.author.username,'body':m.body,'created_at':m.created_at} for m in obj.messages.select_related('author').order_by('id')]
    def get_can_reply(self,obj)->bool:
        user=self.context['request'].user
        return obj.state!='resolved' and (obj.opened_by_id==user.pk or obj.instance.service_id in scopes(user,REVIEW))
    def get_can_resolve(self,obj)->bool:
        return obj.state=='answered' and obj.opened_by_id==self.context['request'].user.pk
    class Meta:
        model=ClarificationRequest
        fields=['id','instance','original','service_name','opened_by_name','assigned_to_name','question','due','state','etag','resolution','created_at','updated_at','help_version','answer_version','messages','can_reply','can_resolve']

def validate(serializer,request):
    data=serializer(data=request.data);data.is_valid(raise_exception=True);return data.validated_data

class ConsultationView(viewsets.ReadOnlyModelViewSet):
    queryset=ClarificationRequest.objects.none()
    serializer_class=RequestSerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False):return ClarificationRequest.objects.none()
        query=visible(self.request.user).select_related('instance__question_version__source','instance__service','opened_by','assigned_to','help_revision','answer_revision').order_by('-updated_at','-id')
        instance=self.request.query_params.get('instance')
        if instance:
            if not instance.isdecimal():raise ValidationError('Pregunta inválida.')
            query=query.filter(instance_id=int(instance))
        return query
    @extend_schema(request=RequestInput,responses={201:RequestSerializer})
    def create(self,request):
        data=validate(RequestInput,request)
        get_object_or_404(QuestionnaireInstance,pk=data['instance'],service_id__in=scopes(request.user,CONSULT_ROLES))
        result=open_request(request.user,data['instance'],data['assigned_to'],data['question'],data['due'],data['client_key'])
        return Response(self.get_serializer(result).data,status=201)
    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False,methods=['get'])
    def recipients(self,request):
        value=request.query_params.get('instance','')
        if not value.isdecimal():raise ValidationError('Seleccione una pregunta.')
        instance=get_object_or_404(QuestionnaireInstance,pk=int(value),service_id__in=scopes(request.user,CONSULT_ROLES))
        values={a.user_id:{'id':a.user_id,'name':a.user.get_full_name() or a.user.username,'username':a.user.username} for a in recipients(instance,request.user)}
        return Response({'people':list(values.values())})
    @extend_schema(request=MessageInput,responses=RequestSerializer)
    @action(detail=True,methods=['post'])
    def message(self,request,pk=None):
        obj=self.get_object();data=validate(MessageInput,request)
        result=post_message(request.user,obj.pk,data['version'],data['body'],data['client_key'])
        return Response(self.get_serializer(result).data)
    @extend_schema(request=ResolutionInput,responses=RequestSerializer)
    @action(detail=True,methods=['post'])
    def resolve(self,request,pk=None):
        obj=self.get_object();data=validate(ResolutionInput,request)
        result=resolve(request.user,obj.pk,data['version'],data['rationale'])
        return Response(self.get_serializer(result).data)
