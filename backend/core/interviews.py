"""Persistent private guided interviews; never send typed facts to a provider."""
import copy
import hashlib
import json
import re
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .access import scopes,require,WRITE
from .admin_serializers import StrictSerializer
from .ai.views import PrivateView
from .ai.workflow import context_for
from .ai.contracts import validate_result,validate_action
from .models import QuestionnaireInstance,Answer,Interview,InterviewTurn,AIRequest,AuditEvent
from .workflow import Conflict,save_answer

LABELS={'pending':'Pendiente','known':'Declarado por usted','unknown':'No lo sé','absent':'No existe actualmente','unconfirmed':'Está por confirmar','not_applicable':'Considero que no aplica'}


def identity(text):
    return hashlib.sha256(' '.join(text.split()).casefold().encode()).hexdigest()


def initial_items(instance):
    guide=instance.published_help.content.get('steps','')
    prompts=re.findall(r'^\s*\d+\.\s+(.+)$',guide,re.MULTILINE)
    if not prompts or len(prompts)>12:prompts=[instance.question_version.source.text]
    result=[]
    for prompt in prompts:
        key=identity(prompt)
        if key not in {p['id'] for p in result}:
            result.append({'id':key,'prompt':prompt,'origin':'help','request_id':None,'reply':'','knowledge':'pending'})
    return result


def checked_job(user,instance,pk):
    job=get_object_or_404(AIRequest,pk=pk,instance=instance,requested_by=user,state='ready')
    context,fragments=context_for(job)
    try:return validate_action(validate_result(job.result,context['question_id'],context['question_version'],fragments),job.action)
    except ValueError:raise serializers.ValidationError('El resultado guardado no cumple el contrato verificable.')


def ai_available(thread,user):
    try:
        for pk in {i['request_id'] for i in thread.items if i['request_id']}:
            checked_job(user,thread.instance,pk)
        return True
    except (serializers.ValidationError,Conflict,ValueError):return False
    except Exception as error:
        from rest_framework.exceptions import APIException
        from django.http import Http404
        if isinstance(error,(APIException,Http404)):return False
        raise


def preview(items):
    return '\n\n'.join(f"{item['prompt']}\n{LABELS[item['knowledge']]}: {item['reply']}" for item in items)


def state(thread,instance,user):
    answer=Answer.objects.get(instance=instance)
    revision=answer.revisions.filter(version=answer.version).first()
    current_answer=revision.content if revision else ''
    if not thread:return {'current_answer':current_answer,'exists':False,'etag':0,'answer_etag':answer.etag,'items':[],'next':[],'history':[]}
    available=ai_available(thread,user)
    items=thread.items if available else []
    stale=thread.help_revision_id!=instance.published_help_id or thread.answer_etag!=answer.etag or not instance.published
    text=preview(items)
    return {'current_answer':current_answer,'exists':True,'etag':thread.etag,'answer_etag':answer.etag,'context_answer_etag':thread.answer_etag,
            'help_revision':thread.help_revision_id,'stale':stale,'sources_blocked':not available,'items':items,
            'next':[i['id'] for i in items if i['knowledge']=='pending'][:2],
            'answered':sum(i['knowledge']!='pending' for i in items),'declared':sum(i['knowledge']=='known' for i in items),'total':len(thread.items),
            'preview':text,'can_apply':bool(items) and all(i['knowledge']!='pending' for i in items) and not stale and len(text)<=20000 and answer.state not in ['submitted','in_review'] and not thread.turns.filter(version=thread.etag,action='apply').exists(),
            'history':list(thread.turns.order_by('-version').values('version','action','help_revision_id','answer_etag','applied_revision_id','created_at')[:100])}


class InterviewInput(StrictSerializer):
    action=serializers.ChoiceField(choices=['open','reply','add_ai','rebase','apply'])
    version=serializers.IntegerField(min_value=0)
    answer_version=serializers.IntegerField(min_value=0)
    client_key=serializers.UUIDField()
    item_id=serializers.CharField(max_length=64,required=False)
    reply=serializers.CharField(max_length=2000,allow_blank=True,required=False)
    knowledge=serializers.ChoiceField(choices=['known','unknown','absent','unconfirmed','not_applicable'],required=False)
    request_id=serializers.IntegerField(min_value=1,required=False)
    def validate(self,data):
        common={'action','version','answer_version','client_key'}
        extra={'open':set(),'rebase':set(),'apply':set(),'reply':{'item_id','reply','knowledge'},'add_ai':{'request_id'}}[data['action']]
        if set(data)!=(common|extra):raise serializers.ValidationError('Campos incompletos o no permitidos para esta acción.')
        return data


class InterviewView(PrivateView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,instance):
        instance=get_object_or_404(QuestionnaireInstance.objects.select_related('published_help','question_version__source'),pk=instance,service_id__in=scopes(request.user,WRITE))
        if not instance.published or not instance.published_help_id:raise serializers.ValidationError('La pregunta necesita ayuda revisada publicada.')
        thread=Interview.objects.filter(instance=instance,owner=request.user).select_related('instance').first()
        result=state(thread,instance,request.user)
        result['guide']=instance.published_help.content.get('steps','')
        result['ai_requests']=list(AIRequest.objects.filter(instance=instance,requested_by=request.user,state='ready',answer_etag=Answer.objects.get(instance=instance).etag).order_by('-id').values_list('id',flat=True)[:20])
        return Response(result)

    @extend_schema(request=InterviewInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,instance):
        form=InterviewInput(data=request.data);form.is_valid(raise_exception=True);data=form.validated_data
        instance=get_object_or_404(QuestionnaireInstance.objects.select_for_update(of=('self',)).select_related('published_help','question_version__source'),pk=instance,service_id__in=scopes(request.user,WRITE))
        if not instance.published or not instance.published_help_id:raise serializers.ValidationError('La pregunta necesita ayuda publicada.')
        require(request.user,instance.service_id,WRITE)
        answer=Answer.objects.select_for_update().get(instance=instance)
        thread=Interview.objects.select_for_update().filter(instance=instance,owner=request.user).first()
        digest=hashlib.sha256(json.dumps(data,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()
        if thread:
            existing=thread.turns.filter(client_key=data['client_key']).first()
            if existing:
                if existing.payload_hash!=digest:raise serializers.ValidationError('La clave de envío ya identifica otro contenido.')
                return Response({**state(thread,instance,request.user),'replayed':True,'applied_revision':existing.applied_revision_id})
        if data['version']!=(thread.etag if thread else 0) or data['answer_version']!=answer.etag:raise Conflict()
        action=data['action']
        if not thread:
            if action!='open':raise serializers.ValidationError('Inicie primero la entrevista.')
            thread=Interview.objects.create(instance=instance,owner=request.user,help_revision=instance.published_help,answer_etag=answer.etag,items=initial_items(instance))
        elif action=='open':raise serializers.ValidationError('La entrevista ya existe; consulte los avances guardados.')
        stale=thread.help_revision_id!=instance.published_help_id or thread.answer_etag!=answer.etag
        if action!='rebase' and (stale or not ai_available(thread,request.user)):
            raise Conflict('Cambió el contexto o la autorización de fuentes; actualice contexto antes de continuar.')
        applied=None
        if action=='rebase':
            old={item['id']:item for item in thread.items if item['origin']=='help'}
            items=initial_items(instance)
            for item in items:
                if item['id'] in old:item['reply']=old[item['id']]['reply']
            thread.items=items;thread.help_revision=instance.published_help;thread.answer_etag=answer.etag
        elif action=='reply':
            item=next((i for i in thread.items if i['id']==data.get('item_id')),None)
            if not item or 'reply' not in data or 'knowledge' not in data:raise serializers.ValidationError('Seleccione un apartado válido y su declaración.')
            if data['knowledge'] in ['known','not_applicable'] and not data['reply'].strip():raise serializers.ValidationError('Escriba la declaración o el fundamento de no aplicabilidad.')
            item['reply']=data['reply'];item['knowledge']=data['knowledge']
        elif action=='add_ai':
            if not data.get('request_id'):raise serializers.ValidationError('Seleccione una solicitud disponible propia.')
            result=checked_job(request.user,instance,data['request_id'])
            for prompt in result.follow_up_questions:
                if identity(prompt) not in {i['id'] for i in thread.items}:
                    thread.items.append({'id':identity(prompt),'prompt':prompt,'origin':'ai','request_id':data['request_id'],'reply':'','knowledge':'pending'})
            if len(thread.items)>20:raise serializers.ValidationError('Límite de veinte apartados; revise el alcance antes de añadir más aclaraciones.')
        elif action=='apply':
            if thread.turns.filter(version=thread.etag,action='apply').exists():raise serializers.ValidationError('Esta versión de entrevista ya se trasladó a borrador.')
            if any(i['knowledge']=='pending' for i in thread.items):raise serializers.ValidationError('Conteste los apartados o indique honestamente qué falta confirmar.')
            text=preview(thread.items)
            if not text or len(text)>20000:raise serializers.ValidationError('El borrador supera el límite o está vacío; ajuste los apartados.')
            answer=save_answer(request.user,answer.pk,answer.etag,text,'unconfirmed')
            applied=answer.revisions.get(version=answer.version)
            thread.answer_etag=answer.etag
        thread.etag+=1;thread.save()
        turn=InterviewTurn.objects.create(interview=thread,version=thread.etag,client_key=data['client_key'],payload_hash=digest,action=action,snapshot=copy.deepcopy(thread.items),help_revision=thread.help_revision,answer_etag=thread.answer_etag,applied_revision=applied)
        AuditEvent.objects.create(actor=request.user,service=instance.service,action='interview.'+action,object_id=str(turn.pk))
        return Response({**state(thread,instance,request.user),'applied_revision':applied.pk if applied else None})
