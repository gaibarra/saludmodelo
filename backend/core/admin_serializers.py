from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Service, RoleAssignment, QuestionnaireInstance, HelpRevision
from .publication import HELP_FIELDS, complete

class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({'non_field_errors': ['Campos no admitidos: ' + ', '.join(sorted(unknown))]})
        return super().to_internal_value(data)

class CampusInput(StrictSerializer):
    institution = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=120)

class SiteInput(StrictSerializer):
    campus = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=120)
    timezone = serializers.CharField(max_length=60, default='America/Merida')
    def validate_timezone(self, value):
        try: ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError): raise serializers.ValidationError('Zona horaria desconocida.')
        return value

class ServiceInput(StrictSerializer):
    site = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=160)
    kind = serializers.ChoiceField(choices=['service', 'administration'], default='service')

class ConfirmInput(StrictSerializer):
    version = serializers.IntegerField(min_value=0)
    rationale = serializers.CharField(max_length=5000)

class UserInput(StrictSerializer):
    institution = serializers.IntegerField(min_value=1)
    username = serializers.RegexField(r'^[a-zA-Z0-9_.@+-]+$', max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True, default='')
    password = serializers.CharField(max_length=256, min_length=12, write_only=True, trim_whitespace=False)
    def validate(self, data):
        user = get_user_model()(username=data['username'], first_name=data['first_name'], last_name=data['last_name'])
        try: password_validation.validate_password(data['password'], user=user)
        except DjangoValidationError as error: raise serializers.ValidationError({'password': error.messages})
        return data

class AssignmentInput(StrictSerializer):
    substitutes = serializers.IntegerField(min_value=1,allow_null=True,required=False,default=None)
    user = serializers.IntegerField(min_value=1)
    service = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=RoleAssignment._meta.get_field('role').choices)
    starts = serializers.DateField()
    ends = serializers.DateField()
    rationale = serializers.CharField(max_length=5000)
    def validate(self, data):
        if data['starts'] > data['ends']: raise serializers.ValidationError('La fecha final debe ser igual o posterior al inicio.')
        return data

class ReasonInput(StrictSerializer):
    rationale = serializers.CharField(max_length=5000)

class SelectionInput(StrictSerializer):
    service = serializers.IntegerField(min_value=1)
    question_versions = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=200)
    rationale = serializers.CharField(max_length=5000)

class HelpContent(StrictSerializer):
    pass
for field in HELP_FIELDS:
    HelpContent._declared_fields[field] = serializers.CharField(max_length=5000, allow_blank=True, required=True)

class HelpInput(StrictSerializer):
    proposal_digest = serializers.RegexField(r"^[a-f0-9]{64}$",allow_blank=True,required=False,default="")
    version = serializers.IntegerField(min_value=0)
    content = HelpContent()

class HelpReviewInput(ConfirmInput):
    decision = serializers.ChoiceField(choices=['approved', 'returned'])

class VersionInput(StrictSerializer):
    version = serializers.IntegerField(min_value=0)

class ServiceAdminSerializer(serializers.ModelSerializer):
    institution = serializers.IntegerField(source='site.campus.institution_id')
    site_name = serializers.CharField(source='site.name')
    class Meta:
        model = Service
        fields = ['id', 'name', 'site', 'site_name', 'institution', 'kind', 'confirmed', 'etag']

class AssignmentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    approved_by_name = serializers.CharField(source='approved_by.username')
    class Meta:
        model = RoleAssignment
        fields = ['id', 'user', 'username', 'service', 'role', 'starts', 'ends', 'approved_by_name', 'rationale', 'revoked_at', 'revocation_reason', 'substitutes']

class HelpRevisionSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username')
    review = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()
    def get_sources(self, revision) -> list[dict]:
        return [{"id":link.source_id,"locator":link.source.locator,"text":link.source.text} for link in revision.source_links.select_related("source")]
    def get_review(self, revision) -> dict | None:
        if not hasattr(revision, 'review'): return None
        r = revision.review
        return {'decision': r.decision, 'reviewer': r.reviewer.username, 'rationale': r.rationale, 'created_at': r.created_at}
    class Meta:
        model = HelpRevision
        fields = ['id', 'number', 'content', 'author_name', 'created_at', 'review', 'origin', 'sources', 'question_version']

class QuestionnaireSerializer(serializers.ModelSerializer):
    original = serializers.CharField(source='question_version.source.text')
    section = serializers.CharField(source='question_version.source.section')
    locator = serializers.CharField(source='question_version.source.locator')
    code = serializers.CharField(source='question_version.question.stable_id')
    question_version_number = serializers.IntegerField(source='question_version.version')
    revisions = serializers.SerializerMethodField()
    draft_available = serializers.SerializerMethodField()
    can_consult = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    def get_draft_available(self,obj) -> bool:
        from .help_drafts import available
        return available(obj)
    def get_can_consult(self,obj) -> bool:
        from .consultations import CONSULT_ROLES
        from .access import scopes
        return obj.service_id in scopes(self.context['request'].user,CONSULT_ROLES)
    def get_revisions(self, obj) -> list[dict]:
        return HelpRevisionSerializer(obj.help_revisions.order_by('-number'), many=True).data
    def get_can_edit(self, obj) -> bool:
        from .access import scopes
        from .governance import EDIT_HELP
        return obj.service_id in scopes(self.context['request'].user, EDIT_HELP)
    def get_can_review(self, obj) -> bool:
        from .access import scopes, REVIEW
        return obj.service_id in scopes(self.context['request'].user, REVIEW)
    class Meta:
        model = QuestionnaireInstance
        fields = ['id', 'service', 'etag', 'published', 'published_help', 'question_version_number', 'original', 'section', 'locator', 'code', 'revisions', 'can_edit', 'can_review', 'draft_available', 'can_consult']
