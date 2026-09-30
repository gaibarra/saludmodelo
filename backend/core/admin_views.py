from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.db.models import Q, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from .models import School, SchoolMember, Institution, InstitutionMember, Campus, Site, Service, RoleAssignment, QuestionVersion, QuestionnaireInstance, CatalogAccess
from .governance import managed_institutions, managed_services, require_institution, require_manage, questionnaire_services, record
from .admin_serializers import *
from .workflow import Conflict
from .publication import save_help, review_help, publish


def validated(serializer, request):
    obj = serializer(data=request.data)
    obj.is_valid(raise_exception=True)
    return obj.validated_data

class SetupView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        institutions = Institution.objects.filter(pk__in=managed_institutions(request.user))
        campuses = Campus.objects.filter(institution__in=institutions)
        sites = Site.objects.filter(campus__in=campuses)
        services = managed_services(request.user).select_related('site__campus')
        members = InstitutionMember.objects.filter(institution__in=institutions, user__is_active=True).select_related('user')
        return Response({'institutions': list(institutions.values('id', 'name')), 'campuses': list(campuses.values('id', 'name', 'institution')), 'sites': list(sites.values('id', 'name', 'campus', 'timezone')), 'services': ServiceAdminSerializer(services, many=True).data, 'users': [{'id': m.user_id, 'username': m.user.username, 'name': m.user.get_full_name(), 'institution': m.institution_id} for m in members], 'questionnaire_services': ServiceAdminSerializer(questionnaire_services(request.user).select_related('site__campus'), many=True).data})

class CampusCreate(APIView):
    @extend_schema(request=CampusInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(CampusInput, request)
        require_institution(request.user, data['institution'])
        campus = Campus.objects.create(institution_id=data['institution'], name=data['name'])
        record(request.user, campus.institution_id, 'campus.created', campus.pk, 'Alta de campus')
        return Response({'id': campus.pk}, status=201)

class SiteCreate(APIView):
    @extend_schema(request=SiteInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(SiteInput, request)
        campus = get_object_or_404(Campus, pk=data['campus'], institution_id__in=managed_institutions(request.user))
        site = Site.objects.create(campus=campus, name=data['name'], timezone=data['timezone'])
        record(request.user, campus.institution_id, 'site.created', site.pk, 'Alta de sede')
        return Response({'id': site.pk}, status=201)

class ServiceAdminView(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.none()
    serializer_class = ServiceAdminSerializer
    def get_queryset(self): return managed_services(self.request.user).select_related('site__campus').order_by('id')
    @extend_schema(request=ServiceInput, responses={201: ServiceAdminSerializer})
    @transaction.atomic
    def create(self, request):
        data = validated(ServiceInput, request)
        site = get_object_or_404(Site, pk=data['site'], campus__institution_id__in=managed_institutions(request.user))
        if School.objects.filter(institution=site.campus.institution).exists():raise ValidationError('Registre el servicio desde la administración de su escuela.')
        service = Service.objects.create(site=site, name=data['name'], kind=data['kind'])
        record(request.user, site.campus.institution_id, 'service.created', service.pk, 'Alta pendiente de confirmación', service)
        return Response(self.get_serializer(service).data, status=201)
    @extend_schema(request=ConfirmInput, responses=ServiceAdminSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def confirm(self, request, pk=None):
        service = self.get_object()
        data = validated(ConfirmInput, request)
        service = Service.objects.select_for_update().get(pk=service.pk)
        if service.etag != data['version']: raise Conflict()
        if not service.confirmed:
            service.confirmed = True
            service.etag += 1
            service.save(update_fields=['confirmed', 'etag'])
            record(request.user, service.site.campus.institution_id, 'service.confirmed', service.pk, data['rationale'], service)
        return Response(self.get_serializer(service).data)

class UserCreate(APIView):
    @extend_schema(request=UserInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(UserInput, request)
        require_institution(request.user, data['institution'])
        try:
            with transaction.atomic():
                user = get_user_model().objects.create_user(username=data['username'], password=data['password'], first_name=data['first_name'], last_name=data['last_name'])
        except IntegrityError:
            raise ValidationError('No se puede registrar ese nombre de usuario. Elija otro o solicite vinculación al operador autorizado.')
        InstitutionMember.objects.create(institution_id=data['institution'], user=user)
        record(request.user, data['institution'], 'user.created', user.pk, 'Cuenta creada sin permisos de servicio')
        return Response({'id': user.pk, 'username': user.username}, status=201)

class AssignmentView(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = RoleAssignment.objects.none()
    serializer_class = AssignmentSerializer
    def get_queryset(self):
        return RoleAssignment.objects.filter(service__in=managed_services(self.request.user)).select_related('user', 'approved_by').order_by('-id')
    @extend_schema(request=AssignmentInput, responses={201: AssignmentSerializer})
    @transaction.atomic
    def create(self, request):
        data = validated(AssignmentInput, request)
        service = get_object_or_404(managed_services(request.user), pk=data['service'])
        # Serialize appointments for this service to avoid duplicate concurrent grants.
        service = Service.objects.select_for_update().get(pk=service.pk)
        require_manage(request.user,service)
        user = get_object_or_404(get_user_model(), pk=data['user'], is_active=True, institutionmember__institution_id=service.site.campus.institution_id)
        if service.school_id and not SchoolMember.objects.filter(school_id=service.school_id,user=user).exists():raise ValidationError('La cuenta debe pertenecer a la escuela del servicio.')
        if user.pk == request.user.pk: raise ValidationError('No puede asignarse permisos a sí mismo.')
        if RoleAssignment.objects.filter(user=user, service=service, role=data['role'], revoked_at__isnull=True, starts__lte=data['ends'], ends__gte=data['starts']).exists():
            raise ValidationError('Ya existe un nombramiento de ese rol que coincide con este periodo.')
        source = None
        if data['substitutes'] is not None:
            source=get_object_or_404(RoleAssignment.objects.select_for_update(),pk=data['substitutes'],service=service)
            if source.substitutes_id or source.revoked_at or not source.user.is_active:
                raise ValidationError('El titular debe ser un nombramiento original no revocado de una persona activa.')
            if source.user_id==user.pk or source.role!=data['role'] or not source.starts<=data['starts']<=data['ends']<=source.ends:
                raise ValidationError('La suplencia requiere otra persona, el mismo rol y fechas dentro del nombramiento titular.')
            if data['ends']<timezone.localdate():raise ValidationError('No se puede crear una suplencia ya vencida.')
        assignment = RoleAssignment.objects.create(user=user, service=service, role=data['role'], starts=data['starts'], ends=data['ends'], approved_by=request.user, rationale=data['rationale'],substitutes=source)
        record(request.user, service.site.campus.institution_id, 'assignment.approved', assignment.pk, data['rationale'], service)
        return Response(self.get_serializer(assignment).data, status=201)
    @extend_schema(request=ReasonInput, responses=AssignmentSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def revoke(self, request, pk=None):
        assignment = self.get_object()
        data = validated(ReasonInput, request)
        service=Service.objects.select_for_update().get(pk=assignment.service_id)
        require_manage(request.user,service)
        assignment = RoleAssignment.objects.select_for_update().get(pk=assignment.pk)
        if assignment.revoked_at is None:
            assignment.revoked_at = timezone.now()
            assignment.revoked_by = request.user
            assignment.revocation_reason = data['rationale']
            assignment.save(update_fields=['revoked_at', 'revoked_by', 'revocation_reason'])
            record(request.user, assignment.service.site.campus.institution_id, 'assignment.revoked', assignment.pk, data['rationale'], assignment.service)
        # All mutation paths lock the service first, including concurrent new substitutions.
        for substitute in assignment.substitutions.select_for_update().filter(revoked_at__isnull=True):
            substitute.revoked_at=timezone.now();substitute.revoked_by=request.user
            substitute.revocation_reason=f'Revocación del nombramiento titular {assignment.pk}: '+data['rationale']
            substitute.save(update_fields=['revoked_at','revoked_by','revocation_reason'])
            record(request.user,service.site.campus.institution_id,'assignment.substitution_revoked',substitute.pk,substitute.revocation_reason,service)
        return Response(self.get_serializer(assignment).data)

class CatalogView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        try: service_id = int(request.query_params.get('service', ''))
        except ValueError: raise ValidationError('Seleccione un servicio.')
        service = get_object_or_404(managed_services(request.user), pk=service_id)
        batches = CatalogAccess.objects.filter(institution_id=service.site.campus.institution_id).values_list('batch_id', flat=True)
        # Latest version visible within the explicitly granted source batches.
        later = QuestionVersion.objects.filter(question_id=OuterRef('question_id'), version__gt=OuterRef('version'), source__batch_id__in=batches)
        versions = QuestionVersion.objects.filter(source__batch_id__in=batches).annotate(has_later=Exists(later)).filter(has_later=False).select_related('source', 'question').order_by('id')
        return Response({'questions': [{'id': v.pk, 'code': v.question.stable_id, 'original': v.source.text, 'section': v.source.section, 'version': v.version, 'locator': v.source.locator} for v in versions]})

class QuestionnaireView(viewsets.ReadOnlyModelViewSet):
    queryset = QuestionnaireInstance.objects.none()
    serializer_class = QuestionnaireSerializer
    def get_queryset(self):
        qs = QuestionnaireInstance.objects.filter(service__in=questionnaire_services(self.request.user)).select_related('question_version__source__batch', 'question_version__question', 'service__site__campus', 'published_help').order_by('id')
        service = self.request.query_params.get('service')
        if service:
            if not service.isdecimal(): raise ValidationError('Servicio inválido.')
            qs = qs.filter(service_id=int(service))
        return qs
    @extend_schema(request=SelectionInput, responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def select(self, request):
        data = validated(SelectionInput, request)
        service = get_object_or_404(managed_services(request.user), pk=data['service'])
        service = Service.objects.select_for_update().get(pk=service.pk)
        batches = CatalogAccess.objects.filter(institution_id=service.site.campus.institution_id).values_list('batch_id', flat=True)
        ids = set(data['question_versions'])
        versions = list(QuestionVersion.objects.filter(pk__in=ids, source__batch_id__in=batches))
        if len(versions) != len(ids): raise ValidationError('Alguna pregunta no pertenece al inventario autorizado.')
        if len({v.question_id for v in versions}) != len(versions): raise ValidationError('Seleccione una sola versión de cada pregunta.')
        created = 0
        for version in versions:
            if QuestionVersion.objects.filter(question_id=version.question_id, version__gt=version.version, source__batch_id__in=batches).exists():
                raise ValidationError('Seleccione la versión vigente del inventario autorizado.')
            if QuestionnaireInstance.objects.filter(service=service, question_version__question_id=version.question_id).exclude(question_version=version).exists():
                raise ValidationError('El cambio de versión de fuente requiere una revisión de alcance; no se sustituirá el cuestionario existente.')
            _, new = QuestionnaireInstance.objects.get_or_create(service=service, question_version=version)
            created += int(new)
        if created:
            record(request.user, service.site.campus.institution_id, 'questionnaire.scope_added', service.pk, data['rationale'], service)
        return Response({'created': created})
    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['get'])
    def draft(self, request, pk=None):
        from .access import require
        from .governance import EDIT_HELP
        from .help_drafts import build
        instance=self.get_object()
        require(request.user,instance.service_id,EDIT_HELP)
        return Response(build(instance))
    @extend_schema(request=HelpInput, responses=QuestionnaireSerializer)
    @action(detail=True, methods=['post'])
    def help(self, request, pk=None):
        instance = self.get_object()
        data = validated(HelpInput, request)
        instance = save_help(request.user, instance.pk, data['version'], data['content'], data['proposal_digest'])
        return Response(self.get_serializer(instance).data)
    @extend_schema(request=HelpReviewInput, responses=QuestionnaireSerializer)
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        instance = self.get_object()
        data = validated(HelpReviewInput, request)
        instance = review_help(request.user, instance.pk, data['version'], data['decision'], data['rationale'])
        return Response(self.get_serializer(instance).data)
    @extend_schema(request=VersionInput, responses=QuestionnaireSerializer)
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        instance = self.get_object()
        data = validated(VersionInput, request)
        instance = publish(request.user, instance.pk, data['version'])
        return Response(self.get_serializer(instance).data)
