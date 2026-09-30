import uuid
from datetime import date
from django.conf import settings
from django.db import models
from django.db.models import Q,F

class Institution(models.Model):
    name=models.CharField(max_length=200)
class School(models.Model):
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    code=models.SlugField(max_length=60)
    name=models.CharField(max_length=200)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','code'],name='school_code')]

class SchoolMember(models.Model):
    school=models.ForeignKey(School,on_delete=models.PROTECT)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['school','user'],name='school_member')]

class SchoolMandate(models.Model):
    school=models.ForeignKey(School,on_delete=models.PROTECT)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    starts=models.DateField()
    ends=models.DateField()
    rationale=models.TextField()
    revoked_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(starts__lte=F('ends')),name='school_mandate_dates'),models.CheckConstraint(condition=~Q(user=F('approved_by')),name='school_mandate_four_eyes')]

class SchoolAcademicGrant(models.Model):
    school=models.ForeignKey(School,on_delete=models.PROTECT,related_name='academic_grants')
    reader_school=models.ForeignKey(School,on_delete=models.PROTECT,related_name='academic_read_access')
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    starts=models.DateField()
    ends=models.DateField()
    rationale=models.TextField()
    revoked_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(starts__lte=F('ends')),name='school_grant_dates'),models.CheckConstraint(condition=~Q(school=F('reader_school')),name='school_grant_distinct')]

class Campus(models.Model):
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    name=models.CharField(max_length=120)
class Site(models.Model):
    campus=models.ForeignKey(Campus,on_delete=models.PROTECT)
    name=models.CharField(max_length=120)
    timezone=models.CharField(max_length=60,default='America/Merida')
class Service(models.Model):
    school=models.ForeignKey(School,null=True,blank=True,on_delete=models.PROTECT)
    public_slug=models.CharField(max_length=40,unique=True,null=True,blank=True)
    etag=models.PositiveIntegerField(default=0)
    site=models.ForeignKey(Site,on_delete=models.PROTECT)
    name=models.CharField(max_length=160)
    confirmed=models.BooleanField(default=False)
    kind=models.CharField(max_length=30,default='service')
class InstitutionalService(models.Model):
    code=models.SlugField(max_length=80,unique=True)
    service=models.OneToOneField(Service,on_delete=models.PROTECT,related_name='institutional_information')
    public_name=models.CharField(max_length=180)
    area=models.CharField(max_length=40,blank=True)
    description=models.TextField()
    audience=models.CharField(max_length=20,choices=[('general','Público en general'),('university','Comunidad universitaria')])
    schedule=models.JSONField(default=list)
    contacts=models.JSONField(default=list)
    notes=models.TextField(blank=True)
    location_note=models.TextField(blank=True)
    classification_basis=models.TextField(blank=True)
    source_url=models.URLField()
    source_checked_on=models.DateField()
    source_sha256=models.CharField(max_length=64)
    published=models.BooleanField(default=True)

class RoleAssignment(models.Model):
    substitutes=models.ForeignKey('self',null=True,on_delete=models.PROTECT,related_name='substitutions')
    rationale=models.TextField(default='')
    revoked_at=models.DateTimeField(null=True)
    revoked_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    revocation_reason=models.TextField(default='')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    role=models.CharField(max_length=30,choices=[(r,r) for r in ['director','coordinator','manager','contributor','compliance','clinical','developer','technical','auditor']])
    starts=models.DateField()
    ends=models.DateField()
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(starts__lte=F('ends')),name='assignment_dates'),models.CheckConstraint(condition=~Q(user=F('approved_by')),name='no_self_assignment')]
class ImportBatch(models.Model):
    digest=models.CharField(max_length=64,unique=True)
    filename=models.CharField(max_length=255)
    report=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT)
class SourceRecord(models.Model):
    batch=models.ForeignKey(ImportBatch,on_delete=models.PROTECT)
    stable_id=models.CharField(max_length=200)
    locator=models.CharField(max_length=250)
    section=models.TextField()
    text=models.TextField()
    kind=models.CharField(max_length=40)
    links=models.JSONField(default=list)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['batch','stable_id'],name='source_identity')]
class Question(models.Model):
    stable_id=models.CharField(max_length=200,unique=True)
class QuestionVersion(models.Model):
    question=models.ForeignKey(Question,on_delete=models.PROTECT)
    source=models.OneToOneField(SourceRecord,on_delete=models.PROTECT)
    version=models.PositiveIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['question','version'],name='question_version')]
class QuestionHelpVersion(models.Model):
    question_version=models.OneToOneField(QuestionVersion,on_delete=models.PROTECT)
    content=models.JSONField(default=dict)
    author=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    reviewed_at=models.DateTimeField(null=True)
class QuestionnaireInstance(models.Model):
    etag=models.PositiveIntegerField(default=0)
    published_help=models.ForeignKey('HelpRevision',null=True,on_delete=models.PROTECT,related_name='+')
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    question_version=models.ForeignKey(QuestionVersion,on_delete=models.PROTECT)
    published=models.BooleanField(default=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['service','question_version'],name='instance_unique')]
class Answer(models.Model):
    etag=models.PositiveIntegerField(default=0)
    instance=models.OneToOneField(QuestionnaireInstance,on_delete=models.PROTECT)
    version=models.PositiveIntegerField(default=0)
    state=models.CharField(max_length=30,default='pending')
class AnswerRevision(models.Model):
    help_revision=models.ForeignKey('HelpRevision',null=True,on_delete=models.PROTECT,related_name='+')
    answer=models.ForeignKey(Answer,on_delete=models.PROTECT,related_name='revisions')
    version=models.PositiveIntegerField()
    content=models.TextField()
    knowledge=models.CharField(max_length=30,default='known')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['answer','version'],name='answer_revision')]
class Review(models.Model):
    revision=models.ForeignKey(AnswerRevision,on_delete=models.PROTECT)
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    decision=models.CharField(max_length=30)
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
class Task(models.Model):
    reservation_plan=models.JSONField(default=list)
    budget_bucket=models.CharField(max_length=10,default="base")
    etag=models.PositiveIntegerField(default=0)
    committed=models.BooleanField(default=False)
    priority=models.CharField(max_length=20,default='normal')
    estimated_minutes=models.PositiveIntegerField(default=0)
    acceptance_criteria=models.TextField(default='')
    substitute=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    coordinator=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    blocked_since=models.DateTimeField(null=True)
    submitted_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')

    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    answer=models.ForeignKey(Answer,null=True,on_delete=models.PROTECT)
    title=models.CharField(max_length=250)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    starts=models.DateField(default=date(2026,10,1))
    due=models.DateField(default=date(2026,10,7))
    state=models.CharField(max_length=30,default='pending')
    deduplication_key=models.CharField(max_length=200,unique=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(starts__gte=date(2026,10,1))&Q(due__gte=F('starts')),name='task_dates')]
class EvidenceDocument(models.Model):
    scan_required=models.BooleanField(default=False)
    security_state=models.CharField(max_length=20,default="not_scanned")
    scanned_at=models.DateTimeField(null=True)
    etag=models.PositiveIntegerField(default=0)
    format=models.CharField(max_length=10,default="txt")
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    answer=models.ForeignKey(Answer,on_delete=models.PROTECT)
    revision=models.ForeignKey(AnswerRevision,on_delete=models.PROTECT)
    file=models.FileField(upload_to='evidence/%Y/%m')
    original_name=models.CharField(max_length=255)
    sha256=models.CharField(max_length=64)
    uploader=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    state=models.CharField(max_length=30,default='received')
    created_at=models.DateTimeField(auto_now_add=True)
class AuditEvent(models.Model):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    action=models.CharField(max_length=80)
    object_id=models.CharField(max_length=200)
    created_at=models.DateTimeField(auto_now_add=True)
class OutboxEvent(models.Model):
    coverage=models.ForeignKey(RoleAssignment,null=True,on_delete=models.PROTECT,related_name="task_notices")
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    task_etag=models.PositiveIntegerField(null=True)

    key=models.CharField(max_length=200,unique=True)
    task=models.ForeignKey(Task,on_delete=models.PROTECT)
    delivered_at=models.DateTimeField(null=True)
class Notification(models.Model):
    event=models.OneToOneField(OutboxEvent,on_delete=models.PROTECT)
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)

class InstitutionMember(models.Model):
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','user'],name='institution_member_unique')]

class InstitutionMandate(models.Model):
    """Explicit authority to administer organization and appointments; never clinical access."""
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    starts=models.DateField()
    ends=models.DateField()
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(starts__lte=F('ends')),name='mandate_dates'),models.CheckConstraint(condition=~Q(user=F('approved_by')),name='mandate_four_eyes')]

class GovernanceEvent(models.Model):
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    service=models.ForeignKey(Service,null=True,on_delete=models.PROTECT)
    action=models.CharField(max_length=80)
    object_id=models.CharField(max_length=200)
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)

class CatalogAccess(models.Model):
    """Explicit grant of an imported source inventory to an institution."""
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    batch=models.ForeignKey(ImportBatch,on_delete=models.PROTECT)
    granted_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','batch'],name='catalog_access_unique')]

class HelpRevision(models.Model):
    question_version=models.ForeignKey(QuestionVersion,null=True,on_delete=models.PROTECT,related_name="+")
    proposal_digest=models.CharField(max_length=64,default='')
    origin=models.CharField(max_length=40,default='manual')
    instance=models.ForeignKey(QuestionnaireInstance,on_delete=models.PROTECT,related_name='help_revisions')
    number=models.PositiveIntegerField()
    content=models.JSONField()
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['instance','number'],name='service_help_revision_unique')]

class HelpReview(models.Model):
    revision=models.OneToOneField(HelpRevision,on_delete=models.PROTECT,related_name='review')
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    decision=models.CharField(max_length=20,choices=[('approved','approved'),('returned','returned')])
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)

class HelpSourceLink(models.Model):
    revision=models.ForeignKey(HelpRevision,on_delete=models.PROTECT,related_name='source_links')
    source=models.ForeignKey(SourceRecord,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['revision','source'],name='help_source_unique')]

class ClarificationRequest(models.Model):
    instance=models.ForeignKey(QuestionnaireInstance,on_delete=models.PROTECT)
    opened_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    help_revision=models.ForeignKey(HelpRevision,null=True,on_delete=models.PROTECT)
    answer_revision=models.ForeignKey(AnswerRevision,null=True,on_delete=models.PROTECT)
    question=models.TextField()
    due=models.DateField()
    client_key=models.UUIDField()
    state=models.CharField(max_length=20,default='open')
    etag=models.PositiveIntegerField(default=0)
    resolution=models.TextField(default='')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['opened_by','client_key'],name='consultation_request_key'),models.CheckConstraint(condition=~Q(opened_by=F('assigned_to')),name='consultation_distinct_people'),models.CheckConstraint(condition=Q(due__gte=date(2026,10,1)),name='consultation_plan_start')]

class ClarificationMessage(models.Model):
    request=models.ForeignKey(ClarificationRequest,on_delete=models.PROTECT,related_name='messages')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    body=models.TextField()
    client_key=models.UUIDField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['request','author','client_key'],name='consultation_message_key')]


class EvidenceExtraction(models.Model):
    document=models.OneToOneField(EvidenceDocument,on_delete=models.PROTECT,related_name='extraction')
    state=models.CharField(max_length=20,default='pending')
    attempts=models.PositiveIntegerField(default=0)
    token=models.UUIDField(null=True)
    leased_until=models.DateTimeField(null=True)
    error=models.CharField(max_length=80,default='')
    extractor=models.CharField(max_length=40,default='text-csv-v1')
    finished_at=models.DateTimeField(null=True)

class EvidenceFragment(models.Model):
    method=models.CharField(max_length=20,default="literal")
    confidence=models.FloatField(null=True)
    extraction=models.ForeignKey(EvidenceExtraction,on_delete=models.PROTECT,related_name='fragments')
    ordinal=models.PositiveIntegerField()
    locator=models.CharField(max_length=120)
    text=models.TextField()
    cells=models.JSONField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['extraction','ordinal'],name='evidence_fragment_ordinal')]

class EvidenceReview(models.Model):
    ocr_checked=models.BooleanField(default=False)
    document=models.ForeignKey(EvidenceDocument,on_delete=models.PROTECT,related_name='reviews')
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    decision=models.CharField(max_length=20)
    rationale=models.TextField()
    valid_until=models.DateField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)

def default_ai_actions():
    return ['suggest']

class AIServicePolicy(models.Model):
    actions=models.JSONField(default=default_ai_actions)
    monthly_user_calls=models.PositiveIntegerField(default=0)
    monthly_cost_limit=models.DecimalField(max_digits=12,decimal_places=6,default=0)
    service=models.OneToOneField(Service,on_delete=models.PROTECT)
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    providers=models.JSONField(default=list)
    enabled=models.BooleanField(default=False)
    monthly_calls=models.PositiveIntegerField(default=0)
    monthly_tokens=models.PositiveIntegerField(default=0)
    rationale=models.TextField()
    etag=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)

class AIFragmentRelease(models.Model):
    fragment=models.ForeignKey(EvidenceFragment,on_delete=models.PROTECT)
    provider=models.CharField(max_length=20)
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    classification=models.CharField(max_length=30)
    rationale=models.TextField()
    expires=models.DateField()
    revoked_at=models.DateTimeField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)

class AIAnswerRelease(models.Model):
    purpose=models.CharField(max_length=20,choices=[(x,x) for x in ['review','interview']],default='review')
    revision=models.ForeignKey(AnswerRevision,on_delete=models.PROTECT)
    answer_etag=models.PositiveIntegerField()
    content_sha256=models.CharField(max_length=64)
    provider=models.CharField(max_length=20)
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    classification=models.CharField(max_length=30)
    rationale=models.TextField()
    expires=models.DateField()
    revoked_at=models.DateTimeField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)

class AIRequest(models.Model):
    answer_release=models.ForeignKey(AIAnswerRelease,null=True,on_delete=models.PROTECT)
    action=models.CharField(max_length=20,default='suggest',choices=[(x,x) for x in ['suggest','explain','interview','extract','review','contradictions','report']])
    reserved_cost=models.DecimalField(max_digits=12,decimal_places=6,default=0)
    estimated_cost=models.DecimalField(max_digits=12,decimal_places=6,null=True)
    rate_snapshot=models.JSONField(default=dict)
    instance=models.ForeignKey(QuestionnaireInstance,on_delete=models.PROTECT)
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    provider=models.CharField(max_length=20)
    model=models.CharField(max_length=120,default='')
    prompt_version=models.CharField(max_length=40,default='salud-assistant-1')
    client_key=models.UUIDField()
    answer_etag=models.PositiveIntegerField()
    references=models.JSONField(default=list)
    state=models.CharField(max_length=20,default='pending')
    error=models.CharField(max_length=60,default='')
    result=models.JSONField(null=True)
    reserved_tokens=models.PositiveIntegerField(default=0)
    input_tokens=models.PositiveIntegerField(default=0)
    output_tokens=models.PositiveIntegerField(default=0)
    latency_ms=models.PositiveIntegerField(default=0)
    started_at=models.DateTimeField(null=True)
    finished_at=models.DateTimeField(null=True)
    applied_revision=models.ForeignKey(AnswerRevision,null=True,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['requested_by','client_key'],name='ai_request_key')]

class NormativeEntry(models.Model):
    source=models.OneToOneField(SourceRecord,on_delete=models.PROTECT)
    code=models.CharField(max_length=20)
    title=models.TextField()
    subject=models.TextField()
    scope_text=models.TextField()
    links=models.JSONField(default=list)

class ComplianceProcess(models.Model):
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    name=models.CharField(max_length=200)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['service','name'],name='compliance_process_service_name')]

class ComplianceRecord(models.Model):
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    etag=models.PositiveIntegerField(default=0)
    version=models.PositiveIntegerField(default=0)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)

class ComplianceRevision(models.Model):
    record=models.ForeignKey(ComplianceRecord,on_delete=models.PROTECT,related_name='revisions')
    version=models.PositiveIntegerField()
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    norm=models.ForeignKey(NormativeEntry,on_delete=models.PROTECT)
    control=models.ForeignKey(SourceRecord,on_delete=models.PROTECT)
    process=models.ForeignKey(ComplianceProcess,on_delete=models.PROTECT)
    question=models.ForeignKey(QuestionnaireInstance,on_delete=models.PROTECT)
    answer_revision=models.ForeignKey(AnswerRevision,null=True,on_delete=models.PROTECT)
    evidence=models.ManyToManyField(EvidenceDocument)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    nature=models.CharField(max_length=30)
    numeral=models.CharField(max_length=160,blank=True)
    consulted_version=models.CharField(max_length=200,blank=True)
    official_url=models.URLField(max_length=1000,blank=True)
    consulted_on=models.DateField(null=True)
    validity=models.CharField(max_length=20,default='pending')
    applicability=models.CharField(max_length=20,default='pending')
    applicability_reason=models.TextField()
    obligation=models.TextField()
    link_reason=models.TextField()
    next_review=models.DateField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['record','version'],name='compliance_revision_version')]

class ComplianceTest(models.Model):
    revision=models.ForeignKey(ComplianceRevision,on_delete=models.PROTECT,related_name='checks')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    procedure=models.TextField()
    expected=models.TextField()
    observed=models.TextField()
    result=models.CharField(max_length=20)
    created_at=models.DateTimeField(auto_now_add=True)

class ComplianceReview(models.Model):
    revision=models.ForeignKey(ComplianceRevision,on_delete=models.PROTECT,related_name='reviews')
    test=models.ForeignKey(ComplianceTest,null=True,on_delete=models.PROTECT)
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    decision=models.CharField(max_length=20)
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)


class WorkPlan(models.Model):
    institution=models.OneToOneField(Institution,on_delete=models.PROTECT)
    etag=models.PositiveIntegerField(default=0)
    weekdays=models.JSONField(default=list)
    holidays=models.JSONField(default=list)
    confirmed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT)
    confirmed_at=models.DateTimeField(null=True)
    rationale=models.TextField(default='')

class WorkCalendarRevision(models.Model):
    plan=models.ForeignKey(WorkPlan,on_delete=models.PROTECT,related_name='revisions')
    version=models.PositiveIntegerField()
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    weekdays=models.JSONField()
    holidays=models.JSONField()
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['plan','version'],name='work_calendar_version')]

class TaskDependency(models.Model):
    task=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='dependencies')
    predecessor=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='successors')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['task','predecessor'],name='task_dependency_unique'),models.CheckConstraint(condition=~Q(task=F('predecessor')),name='task_dependency_not_self')]

class BaselineChange(models.Model):
    task=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='baseline_changes')
    expected_etag=models.PositiveIntegerField()
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    proposal=models.JSONField()
    previous=models.JSONField()
    rationale=models.TextField()
    state=models.CharField(max_length=20,default='pending')
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    review_reason=models.TextField(default='')
    created_at=models.DateTimeField(auto_now_add=True)
    reviewed_at=models.DateTimeField(null=True)

class TaskEvent(models.Model):
    task=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='events')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    kind=models.CharField(max_length=40)
    note=models.TextField()
    snapshot=models.JSONField(default=dict)
    created_at=models.DateTimeField(auto_now_add=True)

class TimeEntry(models.Model):
    budget_bucket=models.CharField(max_length=10,default="base")
    task=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='time_entries')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    day=models.DateField()
    minutes=models.PositiveIntegerField()
    note=models.TextField()
    client_key=models.UUIDField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['actor','client_key'],name='time_entry_key'),models.CheckConstraint(condition=Q(minutes__gt=0)&Q(minutes__lte=1440),name='time_entry_minutes'),models.CheckConstraint(condition=Q(day__gte=date(2026,10,1)),name='time_entry_plan_start')]

class MFADevice(models.Model):
    recovery_required=models.BooleanField(default=False)
    recovery_session_hash=models.CharField(max_length=64,blank=True)
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    secret=models.TextField(default='')
    enabled=models.BooleanField(default=False)
    generation=models.PositiveIntegerField(default=0)
    last_step=models.BigIntegerField(default=-1)
    recovery_hashes=models.JSONField(default=list)
    pending_secret=models.TextField(default='')
    pending_nonce=models.CharField(max_length=64,default='')
    pending_until=models.DateTimeField(null=True)
    failures=models.PositiveIntegerField(default=0)
    locked_until=models.DateTimeField(null=True)

class SecurityEvent(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    action=models.CharField(max_length=60)
    created_at=models.DateTimeField(auto_now_add=True)

class Interview(models.Model):
    instance=models.ForeignKey(QuestionnaireInstance,on_delete=models.PROTECT)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    help_revision=models.ForeignKey(HelpRevision,on_delete=models.PROTECT)
    answer_etag=models.PositiveIntegerField()
    etag=models.PositiveIntegerField(default=0)
    items=models.JSONField(default=list)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['instance','owner'],name='interview_owner_instance')]

class InterviewTurn(models.Model):
    interview=models.ForeignKey(Interview,on_delete=models.PROTECT,related_name='turns')
    version=models.PositiveIntegerField()
    client_key=models.UUIDField()
    payload_hash=models.CharField(max_length=64)
    action=models.CharField(max_length=30)
    snapshot=models.JSONField()
    help_revision=models.ForeignKey(HelpRevision,on_delete=models.PROTECT)
    answer_etag=models.PositiveIntegerField()
    applied_revision=models.ForeignKey(AnswerRevision,null=True,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['interview','client_key'],name='interview_retry_key'),models.UniqueConstraint(fields=['interview','version'],name='interview_turn_version')]

class Decision(models.Model):
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    task=models.ForeignKey(Task,null=True,on_delete=models.PROTECT)
    task_snapshot=models.JSONField(default=dict)
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    title=models.CharField(max_length=250)
    question=models.TextField()
    alternatives=models.TextField()
    due=models.DateField()
    state=models.CharField(max_length=20,default='pending')
    etag=models.PositiveIntegerField(default=1)
    resolution=models.TextField(default='')
    resolved_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    resolved_at=models.DateTimeField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(due__gte=date(2026,10,1)),name='decision_plan_start')]

class DecisionEvent(models.Model):
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    decision=models.ForeignKey(Decision,on_delete=models.PROTECT,related_name='events')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    client_key=models.UUIDField()
    payload_hash=models.CharField(max_length=64)
    version=models.PositiveIntegerField()
    action=models.CharField(max_length=20)
    note=models.TextField()
    snapshot=models.JSONField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['service','actor','client_key'],name='decision_operation_key'),models.UniqueConstraint(fields=['decision','version'],name='decision_event_version')]

class CapacityDay(models.Model):
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    person=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    day=models.DateField()
    etag=models.PositiveIntegerField(default=0)
    confirmed=models.BooleanField(default=False)
    minutes=models.PositiveIntegerField(default=0)
    unavailable_minutes=models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','person','day'],name='capacity_person_day'),models.CheckConstraint(condition=Q(minutes__lte=1440)&Q(unavailable_minutes__lte=F('minutes'))&Q(day__gte=date(2026,10,1)),name='capacity_day_bounds')]

class CapacityAllocation(models.Model):
    capacity=models.ForeignKey(CapacityDay,on_delete=models.PROTECT,related_name='allocations')
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    minutes=models.PositiveIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['capacity','service'],name='capacity_service_unique'),models.CheckConstraint(condition=Q(minutes__gt=0)&Q(minutes__lte=1440),name='capacity_allocation_bounds')]

class CapacityChange(models.Model):
    capacity=models.ForeignKey(CapacityDay,on_delete=models.PROTECT,related_name='changes')
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    client_key=models.UUIDField()
    payload_hash=models.CharField(max_length=64)
    expected_etag=models.PositiveIntegerField()
    proposal=models.JSONField()
    previous=models.JSONField()
    rationale=models.TextField()
    state=models.CharField(max_length=20,default='pending')
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    review_reason=models.TextField(default='')
    reviewed_at=models.DateTimeField(null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','requested_by','client_key'],name='capacity_change_key')]

class SavedReport(models.Model):
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    client_key = models.UUIDField()
    start = models.DateField()
    content = models.JSONField()
    content_hash = models.CharField(max_length=64)
    state = models.CharField(max_length=16, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True)
    rationale = models.TextField(default='')
    reviewed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['service','created_by','client_key'],name='unique_saved_report_retry')]

class ReportDisposition(models.Model):
    report = models.OneToOneField(SavedReport, on_delete=models.PROTECT, related_name='disposition')
    replacement = models.ForeignKey(SavedReport, on_delete=models.PROTECT, null=True, related_name='replaces')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    rationale = models.TextField()
    expected_state = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=~models.Q(report=models.F('replacement')),name='report_cannot_replace_itself')]

class DecisionNoticeReceipt(models.Model):
    coverage_ids=models.JSONField(default=list)
    decision = models.ForeignKey(Decision, on_delete=models.PROTECT, related_name='notice_receipts')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision_version = models.PositiveIntegerField()
    calendar_version = models.PositiveIntegerField()
    stage = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['decision','recipient','decision_version','calendar_version','stage'],name='unique_decision_notice_receipt')]

class ReportSchedule(models.Model):
    service=models.OneToOneField(Service,on_delete=models.PROTECT)
    authorized_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    enabled=models.BooleanField(default=False)
    version=models.PositiveIntegerField(default=1)
    first_period=models.DateField()
    rationale=models.TextField()
    last_checked=models.DateTimeField(null=True)
    last_status=models.CharField(max_length=30,default='not_run')

class ScheduledReportRun(models.Model):
    generation_mode=models.CharField(max_length=16,default="scheduled")
    rationale=models.TextField(default="")
    schedule=models.ForeignKey(ReportSchedule,on_delete=models.PROTECT,related_name='runs')
    period=models.DateField()
    schedule_version=models.PositiveIntegerField()
    report=models.OneToOneField(SavedReport,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['schedule','period'],name='unique_scheduled_report_period')]

class ReportDelivery(models.Model):
    report=models.ForeignKey(SavedReport,on_delete=models.PROTECT,related_name='deliveries')
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    sender=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    acknowledged_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['report','recipient'],name='unique_report_recipient_delivery')]

class TimeCorrection(models.Model):
    entry=models.ForeignKey(TimeEntry,on_delete=models.PROTECT,related_name='corrections')
    version=models.PositiveIntegerField()
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    minutes=models.PositiveIntegerField()
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['entry','version'],name='time_correction_version'),models.CheckConstraint(condition=Q(minutes__lte=1440)&Q(version__gt=0),name='time_correction_bounds')]


class PlanningPolicy(models.Model):
    institution=models.OneToOneField(Institution,on_delete=models.PROTECT)
    enforced=models.BooleanField(default=False)
    etag=models.PositiveIntegerField(default=0)
    base_minutes=models.PositiveIntegerField(default=0)
    reserve_minutes=models.PositiveIntegerField(default=0)

class TaskReservation(models.Model):
    task=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='reservations')
    person=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    day=models.DateField()
    minutes=models.PositiveIntegerField()
    capacity_version=models.PositiveIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['task','person','day'],name='task_person_day_reservation'),models.CheckConstraint(condition=Q(minutes__gt=0)&Q(minutes__lte=1440),name='task_reservation_minutes')]


class QuestionSourceChange(models.Model):
    instance=models.ForeignKey(QuestionnaireInstance,on_delete=models.PROTECT,related_name='source_changes')
    source_from=models.ForeignKey(QuestionVersion,on_delete=models.PROTECT,related_name='+')
    source_to=models.ForeignKey(QuestionVersion,on_delete=models.PROTECT,related_name='+')
    expected_etag=models.PositiveIntegerField()
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    rationale=models.TextField()
    review_reason=models.TextField(default='')
    state=models.CharField(max_length=20,default='pending')
    created_at=models.DateTimeField(auto_now_add=True)
    reviewed_at=models.DateTimeField(null=True)

class AdministrativeTimeCorrection(models.Model):
    entry=models.ForeignKey(TimeEntry,on_delete=models.PROTECT,related_name='administrative_requests')
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    client_key=models.UUIDField()
    expected_version=models.PositiveIntegerField()
    previous_minutes=models.PositiveIntegerField()
    minutes=models.PositiveIntegerField()
    rationale=models.TextField()
    state=models.CharField(max_length=12,default='pending',choices=[('pending','Pendiente'),('approved','Aprobada'),('rejected','Rechazada')])
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+',null=True)
    review_reason=models.TextField(blank=True)
    correction=models.OneToOneField(TimeCorrection,on_delete=models.PROTECT,null=True,related_name='administrative_request')
    created_at=models.DateTimeField(auto_now_add=True)
    reviewed_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['entry','requested_by','client_key'],name='admin_time_request_key'),models.CheckConstraint(condition=Q(minutes__lte=1440)&Q(previous_minutes__lte=1440),name='admin_time_request_bounds')]

class ExceptionalMFARecovery(models.Model):
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    target=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+',null=True)
    client_key=models.UUIDField()
    expected_generation=models.PositiveIntegerField()
    requester_generation=models.PositiveIntegerField()
    reviewer_generation=models.PositiveIntegerField(null=True)
    approved_generation=models.PositiveIntegerField(null=True)
    rationale=models.TextField()
    verification_reference=models.CharField(max_length=250)
    review_reason=models.TextField(blank=True)
    review_reference=models.CharField(max_length=250,blank=True)
    state=models.CharField(max_length=12,default='pending',choices=[('pending','Pendiente'),('approved','Aprobada'),('rejected','Rechazada'),('consumed','Código canjeado'),('completed','Completada'),('revoked','Revocada')])
    token_hash=models.CharField(max_length=64,blank=True)
    expires_at=models.DateTimeField()
    created_at=models.DateTimeField(auto_now_add=True)
    reviewed_at=models.DateTimeField(null=True)
    consumed_at=models.DateTimeField(null=True)
    completed_at=models.DateTimeField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['requested_by','client_key'],name='exceptional_mfa_request_key')]


class PatientProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='patient_profile')
    email_normalized=models.EmailField(max_length=254,unique=True)
    phone=models.CharField(max_length=20)
    created_at=models.DateTimeField(auto_now_add=True)

class AppointmentRequest(models.Model):
    public_id=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    patient=models.ForeignKey(PatientProfile,on_delete=models.PROTECT,related_name='appointment_requests')
    service_slug=models.CharField(max_length=40)
    site_preference=models.CharField(max_length=20)
    preferred_day=models.DateField(null=True)
    status=models.CharField(max_length=15,default='pending',choices=[('pending','Pendiente'),('confirmed','Confirmada'),('declined','No disponible'),('withdrawn','Retirada')])
    confirmed_start=models.DateTimeField(null=True)
    confirmed_site=models.CharField(max_length=20,blank=True)
    reviewed_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    reviewed_at=models.DateTimeField(null=True)
    client_key=models.UUIDField()
    etag=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['patient','client_key'],name='patient_appointment_retry_key'),models.UniqueConstraint(fields=['patient','service_slug'],condition=Q(status='pending'),name='one_pending_appointment_per_service')]


class AcademicCycle(models.Model):
    school=models.ForeignKey(School,null=True,blank=True,on_delete=models.PROTECT)
    revision=models.PositiveIntegerField(default=1)
    closed_at=models.DateTimeField(null=True)
    closed_report=models.ForeignKey('AcademicCycleReport',null=True,on_delete=models.PROTECT,related_name='+')
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    code=models.CharField(max_length=60)
    name=models.CharField(max_length=160)
    starts=models.DateField()
    ends=models.DateField()
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','code'],condition=Q(school__isnull=True),name='academic_legacy_cycle_code'),models.UniqueConstraint(fields=['school','code'],condition=Q(school__isnull=False),name='academic_school_cycle_code'),models.CheckConstraint(condition=Q(starts__lte=F('ends')),name='academic_cycle_dates')]


class AcademicStudent(models.Model):
    school=models.ForeignKey(School,null=True,blank=True,on_delete=models.PROTECT)
    institution=models.ForeignKey(Institution,on_delete=models.PROTECT)
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='academic_student')
    enrollment=models.CharField(max_length=60)
    program=models.CharField(max_length=160)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['institution','enrollment'],name='academic_student_enrollment')]


class AcademicPlacement(models.Model):
    student=models.ForeignKey(AcademicStudent,on_delete=models.PROTECT,related_name='placements')
    cycle=models.ForeignKey(AcademicCycle,on_delete=models.PROTECT,related_name='placements')
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    supervisor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='academic_placements')
    group=models.CharField(max_length=80)
    starts=models.DateField()
    ends=models.DateField()
    target_minutes=models.PositiveIntegerField(null=True,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    created_at=models.DateTimeField(auto_now_add=True)
    revoked_at=models.DateTimeField(null=True)
    revocation_reason=models.TextField(blank=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(starts__lte=F('ends')),name='academic_placement_dates'),models.CheckConstraint(condition=Q(target_minutes__isnull=True)|Q(target_minutes__gt=0),name='academic_target_positive')]


class AcademicPractice(models.Model):
    placement=models.ForeignKey(AcademicPlacement,on_delete=models.PROTECT,related_name='practices')
    client_key=models.UUIDField()
    title=models.CharField(max_length=200)
    performed_on=models.DateField()
    minutes=models.PositiveIntegerField()
    competency=models.CharField(max_length=300)
    evidence_reference=models.CharField(max_length=500)
    activity_reference=models.CharField(max_length=100,blank=True)
    status=models.CharField(max_length=20,default='submitted',choices=[('submitted','Por revisar'),('returned','Devuelta'),('validated','Validada'),('void','Anulada')])
    etag=models.PositiveIntegerField(default=1)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['placement','client_key'],name='academic_practice_retry'),models.CheckConstraint(condition=Q(minutes__gt=0)&Q(minutes__lte=1440),name='academic_practice_minutes')]


class AcademicPracticeEvent(models.Model):
    practice=models.ForeignKey(AcademicPractice,on_delete=models.PROTECT,related_name='events')
    version=models.PositiveIntegerField()
    action=models.CharField(max_length=30)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    rationale=models.TextField(blank=True)
    snapshot=models.JSONField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['practice','version'],name='academic_practice_event_version')]


class AcademicCompetency(models.Model):
    cycle=models.ForeignKey(AcademicCycle,on_delete=models.PROTECT,related_name='competencies')
    service=models.ForeignKey(Service,on_delete=models.PROTECT)
    program=models.CharField(max_length=160,blank=True)
    code=models.CharField(max_length=60)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['cycle','service','program','code'],name='academic_competency_code')]

class AcademicRubric(models.Model):
    competency=models.ForeignKey(AcademicCompetency,on_delete=models.PROTECT,related_name='rubrics')
    version=models.PositiveIntegerField()
    title=models.CharField(max_length=200)
    criterion=models.TextField()
    levels=models.JSONField()
    required_level=models.PositiveIntegerField()
    required=models.BooleanField(default=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    rationale=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['competency','version'],name='academic_rubric_version')]

class AcademicEvaluation(models.Model):
    placement=models.ForeignKey(AcademicPlacement,on_delete=models.PROTECT,related_name='evaluations')
    competency=models.ForeignKey(AcademicCompetency,on_delete=models.PROTECT)
    rubric=models.ForeignKey(AcademicRubric,on_delete=models.PROTECT)
    version=models.PositiveIntegerField()
    score=models.PositiveIntegerField()
    rationale=models.TextField()
    evidence=models.JSONField()
    evaluator=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['placement','competency','version'],name='academic_evaluation_version')]

class AcademicCycleReport(models.Model):
    cycle=models.ForeignKey(AcademicCycle,on_delete=models.PROTECT,related_name='reports')
    sequence=models.PositiveIntegerField()
    source_revision=models.PositiveIntegerField()
    snapshot=models.JSONField()
    digest=models.CharField(max_length=64)
    client_key=models.UUIDField()
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    created_at=models.DateTimeField(auto_now_add=True)
    closed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,related_name='+')
    closed_at=models.DateTimeField(null=True)
    close_reason=models.TextField(blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['cycle','sequence'],name='academic_cycle_report_sequence'),models.UniqueConstraint(fields=['cycle','client_key'],name='academic_report_retry')]
