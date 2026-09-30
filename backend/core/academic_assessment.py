"""Versioned competency evaluations and preserved, scoped cycle closing reports."""
import hashlib
import json
from django.db import transaction
from django.db.models import Q, Max, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import (AcademicCycle, AcademicStudent, AcademicPlacement, AcademicPractice, AcademicCompetency,
                     AcademicRubric, AcademicEvaluation, AcademicCycleReport, Service)
from .academic import AcademicView, AcademicReasonInput, data, placements, can_review, snapshot
from .academic_cycle import lock_open, changed
from .admin_serializers import StrictSerializer
from .governance import managed_institutions, require_institution, record
from .workflow import Conflict
from .school_access import owned,can_manage_academic,can_read_academic


def latest_rubrics():
    latest=AcademicRubric.objects.filter(competency_id=OuterRef('competency_id')).order_by('-version').values('pk')[:1]
    return AcademicRubric.objects.filter(pk=Subquery(latest)).select_related('competency__service','created_by')

def rubric_item(r):
    return {'id':r.pk,'competency':r.competency_id,'cycle':r.competency.cycle_id,'service':r.competency.service_id,
        'service_name':r.competency.service.name,'program':r.competency.program,'code':r.competency.code,'version':r.version,
        'title':r.title,'criterion':r.criterion,'levels':r.levels,'required_level':r.required_level,'required':r.required,
        'author':r.created_by.get_full_name() or r.created_by.username,'rationale':r.rationale,'created_at':r.created_at.isoformat()}

def evaluation_item(e):
    return {'id':e.pk,'placement':e.placement_id,'competency':e.competency_id,'rubric':e.rubric_id,'version':e.version,
        'score':e.score,'rationale':e.rationale,'evidence':e.evidence,'evaluator':e.evaluator.get_full_name() or e.evaluator.username,
        'created_at':e.created_at.isoformat(),'rubric_snapshot':rubric_item(e.rubric)}

def evaluation_state(r,e,practice_map):
    if not e:return 'not_evaluated'
    if e.rubric_id!=r.pk:return 'needs_review'
    if not all(v['practice'] in practice_map and practice_map[v['practice']].status=='validated' and practice_map[v['practice']].etag==v['version'] for v in e.evidence):return 'needs_review'
    return 'achieved' if e.score>=r.required_level else 'not_achieved'

class RubricLevel(StrictSerializer):
    label=serializers.CharField(max_length=80)
    description=serializers.CharField(max_length=1000)

class AcademicRubricInput(StrictSerializer):
    cycle=serializers.IntegerField(min_value=1)
    service=serializers.IntegerField(min_value=1)
    program=serializers.CharField(max_length=160,allow_blank=True,default='')
    code=serializers.CharField(max_length=60)
    version=serializers.IntegerField(min_value=0)
    title=serializers.CharField(max_length=200)
    criterion=serializers.CharField(max_length=3000)
    levels=RubricLevel(many=True,min_length=2,max_length=6)
    required_level=serializers.IntegerField(min_value=1,max_value=6)
    required=serializers.BooleanField()
    rationale=serializers.CharField(min_length=5,max_length=2000)
    def validate_code(self,v):
        value=v.strip().upper()
        if len(value)>60:raise ValidationError('El código normalizado excede 60 caracteres.')
        return value
    def validate(self,v):
        if v['required_level']>len(v['levels']):raise ValidationError('El nivel requerido debe pertenecer a la escala.')
        if len({r['label'].casefold() for r in v['levels']})!=len(v['levels']):raise ValidationError('Cada nivel debe tener un nombre distinto.')
        return v

class EvaluationEvidence(StrictSerializer):
    practice=serializers.IntegerField(min_value=1)
    version=serializers.IntegerField(min_value=1)

class AcademicEvaluationInput(StrictSerializer):
    rubric=serializers.IntegerField(min_value=1)
    version=serializers.IntegerField(min_value=0)
    score=serializers.IntegerField(min_value=1,max_value=6)
    rationale=serializers.CharField(min_length=5,max_length=4000)
    evidence=EvaluationEvidence(many=True,min_length=1,max_length=100)

class ReportCreateInput(StrictSerializer):
    client_key=serializers.UUIDField()

class ReportCloseInput(AcademicReasonInput):
    accept_pending=serializers.BooleanField(default=False)

class CycleReopenInput(AcademicReasonInput):
    report=serializers.IntegerField(min_value=1)

class AcademicRubrics(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request):
        ps=placements(request.user)
        # Match cycle/service/program as a tuple, not independent sets that expand supervisor scope.
        # Explicit tuple predicate for the authorized assignments, including service-wide criteria.
        predicate=owned(request.user,'competency__cycle__',read=True)
        for p in ps:
            predicate|=Q(competency__cycle_id=p.cycle_id,competency__service_id=p.service_id,competency__program__in=['',p.student.program])
        return self.page(request,latest_rubrics().filter(predicate).distinct().order_by('competency_id'),rubric_item)

    @extend_schema(request=AcademicRubricInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request):
        v=data(AcademicRubricInput,request)
        c=get_object_or_404(AcademicCycle.objects.filter(owned(request.user)),pk=v['cycle'])
        c=lock_open(c.pk)
        service=get_object_or_404(Service,pk=v['service'],confirmed=True,site__campus__institution_id=c.institution_id,school_id=c.school_id)
        competency=AcademicCompetency.objects.filter(cycle=c,service=service,program=v['program'],code=v['code']).first()
        previous=competency.rubrics.order_by('-version').first() if competency else None
        if v['version']!=(previous.version if previous else 0):raise Conflict()
        if not competency:competency=AcademicCompetency.objects.create(cycle=c,service=service,program=v['program'],code=v['code'])
        r=AcademicRubric.objects.create(competency=competency,version=v['version']+1,created_by=request.user,
            **{f:v[f] for f in ['title','criterion','levels','required_level','required','rationale']})
        changed(c);record(request.user,c.institution_id,'academic.rubric.created',r.pk,v['rationale'],service)
        return Response(rubric_item(r),status=201)

class AcademicEvaluations(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,placement):
        p=get_object_or_404(placements(request.user),pk=placement)
        rs=latest_rubrics().filter(competency__cycle_id=p.cycle_id,competency__service_id=p.service_id,competency__program__in=['',p.student.program]).order_by('competency_id')
        pm={x.pk:x for x in p.practices.all()}
        results=[]
        for r in rs:
            e=p.evaluations.filter(competency=r.competency).select_related('evaluator','rubric__created_by','rubric__competency__service').order_by('-version').first()
            results.append({'rubric':rubric_item(r),'evaluation':evaluation_item(e) if e else None,'state':evaluation_state(r,e,pm)})
        return Response({'placement':p.pk,'can_evaluate':can_review(request.user,p),'results':results})

    @extend_schema(request=AcademicEvaluationInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,placement):
        v=data(AcademicEvaluationInput,request)
        p=get_object_or_404(placements(request.user),pk=placement)
        c=lock_open(p.cycle_id)
        AcademicStudent.objects.select_for_update().get(pk=p.student_id)
        Service.objects.select_for_update().get(pk=p.service_id)
        p=placements(request.user).get(pk=p.pk)
        if not can_review(request.user,p):raise PermissionDenied('Sólo el supervisor asignado con nombramiento vigente puede evaluar.')
        r=get_object_or_404(latest_rubrics(),pk=v['rubric'],competency__cycle_id=p.cycle_id,competency__service_id=p.service_id,competency__program__in=['',p.student.program])
        previous=p.evaluations.filter(competency=r.competency).order_by('-version').first()
        if v['version']!=(previous.version if previous else 0):raise Conflict()
        if v['score']>len(r.levels):raise ValidationError('El nivel elegido no pertenece a esta rúbrica.')
        ids=[e['practice'] for e in v['evidence']]
        if len(set(ids))!=len(ids):raise ValidationError('No repita prácticas en la evidencia.')
        pm={x.pk:x for x in p.practices.filter(pk__in=ids,status='validated')}
        if any(e['practice'] not in pm or pm[e['practice']].etag!=e['version'] for e in v['evidence']):raise ValidationError('Cada evidencia debe ser una práctica validada de esta rotación en su versión actual.')
        e=AcademicEvaluation.objects.create(placement=p,competency=r.competency,rubric=r,version=v['version']+1,score=v['score'],rationale=v['rationale'],evidence=v['evidence'],evaluator=request.user)
        changed(c);record(request.user,c.institution_id,'academic.evaluation.created',e.pk,v['rationale'],p.service)
        return Response(evaluation_item(e),status=201)

class AcademicEvaluationHistory(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,placement):
        p=get_object_or_404(placements(request.user),pk=placement)
        qs=p.evaluations.select_related('evaluator','rubric__created_by','rubric__competency__service').order_by('-id')
        return self.page(request,qs,evaluation_item)


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def empty_totals():return {s:{'participations':0,'minutes':0} for s in ['submitted','returned','validated','void']}

def merge_totals(target,source):
    for status,t in source.items():
        target[status]['participations']+=t['participations'];target[status]['minutes']+=t['minutes']

def build_snapshot(cycle):
    """Caller holds the cycle lock; every academic writer takes the same lock."""
    students={};totals=empty_totals();all_issues=[];services={}
    rubrics=list(latest_rubrics().filter(competency__cycle=cycle).order_by('competency_id'))
    ps=AcademicPlacement.objects.filter(cycle=cycle).select_related('student__user','supervisor','service__site').prefetch_related('practices__events__actor','evaluations__evaluator','evaluations__rubric__created_by','evaluations__rubric__competency__service').order_by('student_id','id')
    for p in ps:
        student=students.setdefault(p.student_id,{'id':p.student_id,'name':p.student.user.get_full_name() or p.student.user.username,'enrollment':p.student.enrollment,'program':p.student.program,'placements':[],'totals':empty_totals(),'issues':[]})
        pr=list(p.practices.all());pm={x.pk:x for x in pr};pt=empty_totals();issues=[]
        for row in pr:
            pt[row.status]['participations']+=1;pt[row.status]['minutes']+=row.minutes
            if row.status in ['submitted','returned']:issues.append(f'Práctica {row.pk} pendiente de revisión o corrección.')
        rs=[r for r in rubrics if r.competency.service_id==p.service_id and r.competency.program in ['',p.student.program]]
        evs=list(p.evaluations.all());evaluations=[]
        for r in rs:
            history=sorted([e for e in evs if e.competency_id==r.competency_id],key=lambda e:e.version)
            current=history[-1] if history else None
            state=evaluation_state(r,current,pm)
            evaluations.append({'rubric':rubric_item(r),'evaluation':evaluation_item(current) if current else None,'state':state,'history':[evaluation_item(e) for e in history]})
            if not p.revoked_at and r.required and state!='achieved':issues.append(f'Competencia {r.competency.code}: '+{'not_evaluated':'sin evaluar','needs_review':'requiere revisión','not_achieved':'nivel requerido no alcanzado'}[state]+'.')
        if not p.revoked_at:
            if not rs:issues.append('Sin rúbricas configuradas para esta rotación.')
            if p.target_minutes and pt['validated']['minutes']<p.target_minutes:issues.append('Meta de minutos validados pendiente.')
        practice_rows=[]
        for row in pr:
            practice_rows.append({'id':row.pk,'version':row.etag,**snapshot(row),'history':[{'version':e.version,'action':e.action,'actor':e.actor.get_full_name() or e.actor.username,'rationale':e.rationale,'snapshot':e.snapshot,'created_at':e.created_at.isoformat()} for e in sorted(row.events.all(),key=lambda e:e.version)]})
        entry={'id':p.pk,'service':p.service_id,'service_name':p.service.name,'site_name':p.service.site.name,'group':p.group,'supervisor':p.supervisor.get_full_name() or p.supervisor.username,'starts':p.starts.isoformat(),'ends':p.ends.isoformat(),'target_minutes':p.target_minutes,'revoked_at':p.revoked_at.isoformat() if p.revoked_at else None,'revocation_reason':p.revocation_reason,'totals':pt,'practices':practice_rows,'competencies':evaluations,'issues':issues}
        student['placements'].append(entry);merge_totals(student['totals'],pt);merge_totals(totals,pt)
        context=[f'{p.service.name} / rotación {p.pk}: {issue}' for issue in issues];student['issues'].extend(context)
        all_issues.extend([f'{p.student.enrollment}: {issue}' for issue in context])
        service=services.setdefault(p.service_id,{'id':p.service_id,'name':p.service.name,'site_name':p.service.site.name,'totals':empty_totals(),'student_ids':set()})
        service['student_ids'].add(p.student_id);merge_totals(service['totals'],pt)
    for service in services.values():service['students']=len(service.pop('student_ids'))
    return {'cycle':{'id':cycle.pk,'institution':cycle.institution.name,'school':cycle.school_id,'school_name':cycle.school.name if cycle.school_id else 'Sin clasificar','code':cycle.code,'name':cycle.name,'starts':cycle.starts.isoformat(),'ends':cycle.ends.isoformat(),'source_revision':cycle.revision},'students':list(students.values()),'services':list(services.values()),'totals':totals,'issues':all_issues,'rubrics':[rubric_item(r) for r in rubrics],'automatic_accreditation':False,'coverage':'Alumnos con rotaciones registradas en este ciclo; participaciones individuales, no pacientes ni actividades únicas.'}


def accessible_reports(user):
    student_id=AcademicStudent.objects.filter(user=user).values_list('id',flat=True).first()
    personal=Q(closed_at__isnull=False,snapshot__students__contains=[{'id':student_id}]) if student_id else Q(pk__in=[])
    return AcademicCycleReport.objects.filter(owned(user,'cycle__',read=True)|personal).select_related('cycle','created_by','closed_by').distinct()

def report_snapshot(row,user,selected=None):
    manager=can_manage_academic(user,row.cycle)
    if not can_read_academic(user,row.cycle):
        student=get_object_or_404(AcademicStudent,user=user)
        if selected and selected!=student.pk:raise PermissionDenied('Sólo puede consultar su informe individual.')
        selected=student.pk
    if selected:
        s=next((s for s in row.snapshot['students'] if s['id']==selected),None)
        if not s:raise ValidationError('El alumno no aparece en esta versión del informe.')
        return {'cycle':row.snapshot['cycle'],'students':[s],'totals':s['totals'],'issues':s['issues'],'services':[],
            'automatic_accreditation':False,'coverage':'Informe individual de las rotaciones incluidas en la versión conservada.'},'individual'
    return row.snapshot,'consolidated'

def report_item(row,user,selected=None,detail=False):
    if digest(row.snapshot)!=row.digest:raise ValidationError('La integridad del informe no pudo verificarse.')
    content,kind=report_snapshot(row,user,selected)
    manager=can_manage_academic(user,row.cycle)
    result={'school':row.cycle.school_id,'school_name':row.cycle.school.name if row.cycle.school_id else 'Sin clasificar','id':row.pk,'cycle':row.cycle_id,'cycle_name':row.snapshot['cycle']['name'],'sequence':row.sequence,'source_revision':row.source_revision,'kind':kind,'created_at':row.created_at,'created_by':row.created_by.get_full_name() or row.created_by.username,'closed_at':row.closed_at,'closed_by':row.closed_by.get_full_name() or row.closed_by.username if row.closed_by else None,'close_reason':row.close_reason if manager else ('Cierre documental autorizado por Dirección.' if row.closed_at else ''),'current_closure':row.cycle.closed_report_id==row.pk,'stale':not row.closed_at and row.cycle.revision!=row.source_revision,'issues_count':len(content['issues']),'can_close':manager and not row.closed_at and not row.cycle.closed_at and row.cycle.revision==row.source_revision,'can_reopen':manager and row.cycle.closed_report_id==row.pk,'digest':digest(content)}
    if detail:result['snapshot']=content
    return result

class AcademicReports(AcademicView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self,request,cycle):
        qs=accessible_reports(request.user).filter(cycle_id=cycle).order_by('-sequence')
        return self.page(request,qs,lambda r:report_item(r,request.user))

    @extend_schema(request=ReportCreateInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,cycle):
        v=data(ReportCreateInput,request)
        c=get_object_or_404(AcademicCycle.objects.filter(owned(request.user)),pk=cycle);c=lock_open(c.pk)
        previous=c.reports.filter(client_key=v['client_key']).first()
        if previous:return Response(report_item(previous,request.user,detail=True))
        content=build_snapshot(c)
        if not content['students']:raise ValidationError('El ciclo no tiene alumnos con rotaciones registradas.')
        sequence=(c.reports.aggregate(n=Max('sequence'))['n'] or 0)+1
        r=AcademicCycleReport.objects.create(cycle=c,sequence=sequence,source_revision=c.revision,snapshot=content,digest=digest(content),client_key=v['client_key'],created_by=request.user)
        record(request.user,c.institution_id,'academic.report.created',r.pk,'Informe conservado de cierre; versión '+str(sequence))
        return Response(report_item(r,request.user,detail=True),status=201)

class AcademicReportDetail(AcademicView):
    @extend_schema(parameters=[OpenApiParameter('student',OpenApiTypes.INT,required=False)],responses=OpenApiTypes.OBJECT)
    def get(self,request,pk):
        row=get_object_or_404(accessible_reports(request.user),pk=pk)
        selected=request.query_params.get('student')
        if selected:
            try:selected=int(selected)
            except ValueError:raise ValidationError('Alumno inválido.')
            if selected<1:raise ValidationError('Alumno inválido.')
        result=report_item(row,request.user,selected,True)
        if not can_manage_academic(request.user,row.cycle) and can_read_academic(request.user,row.cycle):record(request.user,row.cycle.institution_id,'school.academic.report_consulted',row.pk,'Consulta académica compartida de versión conservada')
        return Response(result)

class AcademicReportClose(AcademicView):
    @extend_schema(request=ReportCloseInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,pk):
        v=data(ReportCloseInput,request)
        r=get_object_or_404(AcademicCycleReport.objects.filter(owned(request.user,'cycle__')),pk=pk)
        c=lock_open(r.cycle_id)
        if r.closed_at or r.source_revision!=c.revision:raise Conflict()
        if digest(r.snapshot)!=r.digest:raise ValidationError('La integridad del informe no pudo verificarse.')
        if c.ends>timezone.localdate():raise ValidationError('Puede preparar informes durante el ciclo; el cierre requiere que llegue su fecha de término.')
        if r.snapshot['issues'] and not v['accept_pending']:raise ValidationError('El informe tiene pendientes. Debe reconocerlos explícitamente para cerrar con pendientes.')
        r.closed_at=timezone.now();r.closed_by=request.user;r.close_reason=v['rationale'];r.save(update_fields=['closed_at','closed_by','close_reason'])
        c.closed_at=r.closed_at;c.closed_report=r;c.revision+=1;c.save(update_fields=['closed_at','closed_report','revision'])
        r.cycle=c
        record(request.user,c.institution_id,'academic.cycle.closed',r.pk,v['rationale'])
        return Response(report_item(r,request.user,detail=True))

class AcademicCycleReopen(AcademicView):
    @extend_schema(request=CycleReopenInput,responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self,request,cycle):
        v=data(CycleReopenInput,request)
        c=get_object_or_404(AcademicCycle.objects.select_for_update().filter(owned(request.user)),pk=cycle)
        if not c.closed_at or c.closed_report_id!=v['report']:raise Conflict()
        previous=c.closed_report_id;c.closed_at=None;c.closed_report=None;c.revision+=1;c.save(update_fields=['closed_at','closed_report','revision'])
        record(request.user,c.institution_id,'academic.cycle.reopened',previous,v['rationale'])
        return Response({'id':c.pk,'revision':c.revision,'closed_at':None})
