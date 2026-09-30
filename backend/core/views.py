from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
import hashlib,uuid,io
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from django.http import FileResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets,status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.throttling import AnonRateThrottle,UserRateThrottle
from rest_framework.exceptions import ValidationError
from .models import *
from .access import scopes,require,WRITE,READ
from .serializers import *
from .workflow import save_answer,transition,Conflict,audit
from rest_framework.authentication import SessionAuthentication
from .mfa import status as mfa_status

class SessionView(APIView):
    authentication_classes=[SessionAuthentication]
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs)
        response["Cache-Control"]="no-store"
        return response
    permission_classes=[AllowAny]
    throttle_classes=[AnonRateThrottle,UserRateThrottle]
    @extend_schema(responses=SessionSerializer)
    def get(self,request):return Response({**mfa_status(request),'csrf':get_token(request)})
    @extend_schema(request=LoginSerializer,responses=SessionSerializer)
    @method_decorator(csrf_protect)
    def post(self,request):
        data=LoginSerializer(data=request.data);data.is_valid(raise_exception=True)
        user=authenticate(request,**data.validated_data)
        if not user:return Response({'detail':'Usuario o contraseña incorrectos.'},status=400)
        request.session.flush()
        login(request,user)
        request.session['password_login_at']=timezone.now().timestamp()
        return Response({**mfa_status(request),'csrf':get_token(request)})
    @extend_schema(responses={204:None})
    @method_decorator(csrf_protect)
    def delete(self,request):logout(request);return Response(status=204)
class ServiceView(viewsets.ReadOnlyModelViewSet):
    queryset=Service.objects.none()
    serializer_class=ServiceSerializer
    def get_queryset(self):return Service.objects.filter(pk__in=scopes(self.request.user)).select_related('site').order_by('id')
class AnswerView(viewsets.ReadOnlyModelViewSet):
    queryset=Answer.objects.none()
    serializer_class=AnswerSerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False):return Answer.objects.none()
        qs=Answer.objects.filter(instance__service_id__in=scopes(self.request.user),instance__published=True).select_related('instance__question_version__source','instance__published_help').order_by('id')
        if self.request.query_params.get('service'):qs=qs.filter(instance__service_id=self.request.query_params['service'])
        return qs
    @extend_schema(request=SaveSerializer,responses=AnswerSerializer)
    @action(detail=True,methods=['post'])
    def save(self,request,pk=None):
        a=self.get_object();s=SaveSerializer(data=request.data);s.is_valid(raise_exception=True)
        a=save_answer(request.user,a.pk,s.validated_data['version'],s.validated_data['content'],s.validated_data['knowledge']);return Response(self.get_serializer(a).data)
    @extend_schema(request=TransitionSerializer,responses=AnswerSerializer)
    @action(detail=True,methods=['post'])
    def transition(self,request,pk=None):
        a=self.get_object();s=TransitionSerializer(data=request.data);s.is_valid(raise_exception=True)
        a=transition(request.user,a.pk,s.validated_data['version'],s.validated_data['target'],s.validated_data['rationale']);return Response(self.get_serializer(a).data)
    @extend_schema(request=UploadSerializer,responses={201:AnswerSerializer})
    @action(detail=True,methods=['post'])
    @transaction.atomic
    def evidence(self,request,pk=None):
        a=self.get_object();require(request.user,a.instance.service_id,WRITE)
        a=Answer.objects.select_for_update().get(pk=a.pk)
        try: expected=int(request.data.get('version',-1))
        except (TypeError,ValueError):raise ValidationError('Versión inválida.')
        if expected!=a.etag:raise Conflict()
        if a.state!='draft':raise ValidationError('Guarde un borrador antes de adjuntar.')
        f=request.FILES.get('file')
        if not f or f.size>10_000_000:raise ValidationError('Seleccione un archivo de hasta 10 MB.')
        # Accept only inert UTF-8 text; CSV parsing happens in the bounded worker.
        kind=f.name.rsplit('.',1)[-1].lower()
        if kind not in {'txt','csv','pdf','docx','xlsx','png','jpg','jpeg'}:raise ValidationError('Formato no habilitado. Se admite TXT, CSV, PDF, DOCX o XLSX según la configuración de seguridad.')
        if kind in {'pdf','docx','xlsx','png','jpg','jpeg'}:
            if not settings.DOCUMENT_SIGNATURES:raise ValidationError('Los documentos binarios requieren configurar primero el análisis de seguridad.')
            if kind in {'png','jpg','jpeg'} and not settings.DOCUMENT_OCR_RUNTIME:raise ValidationError('El reconocimiento de imágenes aún no está habilitado.')
        raw=f.read()
        if kind in {'txt','csv'}:
            try: text=raw.decode('utf-8')
            except UnicodeDecodeError:raise ValidationError('El archivo no es texto UTF-8.')
            if any(ord(c)<32 and c not in '\n\r\t' for c in text):raise ValidationError('El archivo contiene datos binarios.')
            if not text.strip():raise ValidationError('El archivo está vacío.')
        elif not raw:raise ValidationError('El archivo está vacío.')
        f.seek(0);original=f.name;f.name=str(uuid.uuid4())+'.'+kind
        doc=EvidenceDocument.objects.create(scan_required=bool(settings.DOCUMENT_SIGNATURES) or kind not in {"txt","csv"},format=kind,answer=a,revision=a.revisions.get(version=a.version),file=f,original_name=original[:255],sha256=hashlib.sha256(raw).hexdigest(),uploader=request.user)
        EvidenceExtraction.objects.create(document=doc)
        a.etag+=1;a.save(update_fields=['etag']);audit(request.user,a,'evidence.uploaded');return Response(self.get_serializer(a).data,status=201)
class DownloadView(APIView):
    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self,request,pk):
        e=get_object_or_404(EvidenceDocument,pk=pk,answer__instance__service_id__in=scopes(request.user,WRITE|{'manager','compliance','clinical','auditor'}))
        if (e.scan_required or e.format not in {'txt','csv'}) and e.security_state!='clean':raise ValidationError('El documento permanece bloqueado hasta superar el análisis de seguridad.')
        audit(request.user,e.answer,'evidence.downloaded')
        with e.file.open('rb') as source:raw=source.read(10_000_001)
        if len(raw)>10_000_000 or hashlib.sha256(raw).hexdigest()!=e.sha256:raise ValidationError('El original almacenado no coincide con su huella; la descarga queda bloqueada.')
        response=FileResponse(io.BytesIO(raw),as_attachment=True,filename=e.original_name,content_type='application/octet-stream')
        response['Cache-Control']='private, no-store';return response
class TaskView(viewsets.ReadOnlyModelViewSet):
    queryset=Task.objects.none()
    serializer_class=TaskSerializer
    def get_queryset(self):return Task.objects.filter(service_id__in=scopes(self.request.user)).order_by('due','id')
class DashboardView(APIView):
    @extend_schema(responses=DashboardSerializer)
    def get(self,request):
        from django.utils import timezone
        from django.db.models import Q
        from .governance import managed_services
        allowed_services=Service.objects.filter(Q(pk__in=scopes(request.user))|Q(pk__in=managed_services(request.user)))
        q=QuestionnaireInstance.objects.filter(service__in=allowed_services,service__confirmed=True)
        total=q.count();validated=Answer.objects.filter(instance__in=q,state='validated').count()
        return Response({'validated':{'numerator':validated,'denominator':total,'pending':total-validated,'label':'Sin alcance definido' if not total else f'{validated} de {total}','records_url':'/api/v1/answers/'},'tasks_pending':Task.objects.filter(service__in=allowed_services).exclude(state__in=['accepted','cancelled']).count(),'updated_at':timezone.now(),'clinical_scope':'Pendiente de implementación y aceptación R01–R12 y C18'})
