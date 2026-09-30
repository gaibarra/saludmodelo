from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .access import scopes,WRITE,REVIEW
from .admin_serializers import StrictSerializer
from .models import EvidenceDocument, EvidenceExtraction, AIFragmentRelease
from .documents import review_document,retry_document

DOCUMENT_ROLES=WRITE|REVIEW|{'auditor'}
def authorized(user,pk):
    return get_object_or_404(EvidenceDocument.objects.select_related('answer__instance','revision','uploader'),pk=pk,answer__instance__service_id__in=scopes(user,DOCUMENT_ROLES))

def detail(doc,user):
    extraction=EvidenceExtraction.objects.filter(document=doc).first()
    latest=doc.reviews.order_by('-id').first()
    return {'id':str(doc.pk),'instance':doc.answer.instance_id,'name':doc.original_name,'sha256':doc.sha256,'format':doc.format,'state':doc.state,'security_state':doc.security_state,'scan_required':doc.scan_required or doc.format not in {'txt','csv'},'scanned_at':doc.scanned_at,'etag':doc.etag,'answer_version':doc.revision.version,'current_answer_version':doc.answer.version,'is_current':doc.answer.version==doc.revision.version,'expired':bool(latest and latest.decision=='accepted' and latest.valid_until and latest.valid_until<timezone.localdate()),'can_review':doc.answer.instance.service_id in scopes(user,REVIEW) and user.pk not in {doc.uploader_id,doc.revision.author_id},'requires_ocr_check':bool(extraction and extraction.fragments.filter(method='ocr').exists()),'can_retry':bool(extraction and extraction.state=='failed' and extraction.attempts<3 and doc.answer.instance.service_id in scopes(user,WRITE|REVIEW)),'extraction':{'state':extraction.state if extraction else 'pending','error':extraction.error if extraction else '', 'extractor':extraction.extractor if extraction else '', 'count':extraction.fragments.count() if extraction else 0},'ai_releases':[{'id':r.pk,'fragment_id':r.fragment_id,'provider':r.provider,'expires':r.expires,'revoked':r.revoked_at is not None} for r in AIFragmentRelease.objects.filter(fragment__extraction__document=doc).order_by('-id')],'reviews':[{'decision':r.decision,'reviewer':r.reviewer.username,'rationale':r.rationale,'ocr_checked':r.ocr_checked,'valid_until':r.valid_until,'created_at':r.created_at} for r in doc.reviews.select_related('reviewer').order_by('-id')]}
class ReviewInput(StrictSerializer):
    ocr_checked=serializers.BooleanField(default=False)
    version=serializers.IntegerField(min_value=0)
    decision=serializers.ChoiceField(choices=['accepted','returned'])
    rationale=serializers.CharField(max_length=5000)
    valid_until=serializers.DateField(required=False,allow_null=True,default=None)
class PrivateDocumentView(APIView):
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs)
        response['Cache-Control']='private, no-store'
        return response
class DocumentView(PrivateDocumentView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):return Response(detail(authorized(request.user,pk),request.user))
    @extend_schema(request=ReviewInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        authorized(request.user,pk)
        data=ReviewInput(data=request.data);data.is_valid(raise_exception=True)
        doc=review_document(request.user,pk,**data.validated_data)
        return Response(detail(doc,request.user))
class FragmentView(PrivateDocumentView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        doc=authorized(request.user,pk)
        value=request.query_params.get('page','1')
        if not value.isdecimal() or not 1<=int(value)<=201:raise serializers.ValidationError('Página inválida.')
        page=int(value);extraction=EvidenceExtraction.objects.filter(document=doc,state='ready').first()
        query=extraction.fragments.order_by('ordinal') if extraction else None
        count=query.count() if query is not None else 0
        return Response({'count':count,'page':page,'has_next':count>page*50,'fragments':list(query.values('id','ordinal','locator','text','cells','method','confidence')[(page-1)*50:page*50]) if query is not None else []})

class RetryInput(StrictSerializer):
    version=serializers.IntegerField(min_value=0)
class RetryView(PrivateDocumentView):
    @extend_schema(request=RetryInput,responses=OpenApiTypes.OBJECT)
    def post(self,request,pk):
        authorized(request.user,pk)
        data=RetryInput(data=request.data);data.is_valid(raise_exception=True)
        return Response(detail(retry_document(request.user,pk,data.validated_data['version']),request.user))
