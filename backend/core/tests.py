import io,json,tempfile
from pathlib import Path
from datetime import date,timedelta
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError,PermissionDenied
from .models import *
from .workflow import save_answer,transition,Conflict
from .publication import publish,HELP_FIELDS,save_help,review_help
from .importer import parse
class WorkflowTests(TestCase):
    def setUp(self):
        U=get_user_model();self.author=U.objects.create_user('author',password='synthetic-only');self.reviewer=U.objects.create_user('reviewer');self.other=U.objects.create_user('other');self.admin=U.objects.create_superuser('bootstrap',password='synthetic-only')
        i=Institution.objects.create(name='Synthetic');c=Campus.objects.create(institution=i,name='Campus');s=Site.objects.create(campus=c,name='Site')
        self.service=Service.objects.create(site=s,name='Dental',confirmed=True);self.foreign=Service.objects.create(site=s,name='Psychology')
        today=timezone.localdate()
        for user,service,role in [(self.author,self.service,'contributor'),(self.reviewer,self.service,'manager'),(self.other,self.foreign,'contributor')]:RoleAssignment.objects.create(user=user,service=service,role=role,starts=today-timedelta(days=1),ends=today+timedelta(days=10),approved_by=self.admin)
        b=ImportBatch.objects.create(digest='a'*64,filename='synthetic');src=SourceRecord.objects.create(batch=b,stable_id='Q1',locator='p1',section='test',text='Synthetic question',kind='question_original')
        q=Question.objects.create(stable_id='Q1');v=QuestionVersion.objects.create(question=q,source=src,version=1)
        self.help=QuestionHelpVersion.objects.create(question_version=v,author=self.author,reviewed_by=self.reviewer,reviewed_at=timezone.now(),content={k:'Synthetic guidance' for k in HELP_FIELDS})
        self.instance=QuestionnaireInstance.objects.create(service=self.service,question_version=v)
        help_instance=save_help(self.author,self.instance.pk,0,{k:'Synthetic guidance' for k in HELP_FIELDS})
        help_instance=review_help(self.reviewer,self.instance.pk,help_instance.etag,'approved','Synthetic review')
        publish(self.reviewer,self.instance.pk,help_instance.etag);self.answer=Answer.objects.get(instance=self.instance)
    def test_save_resume_conflict_and_four_eyes(self):
        a=save_answer(self.author,self.answer.pk,0,'Declared operation','known')
        with self.assertRaises(Conflict):save_answer(self.author,a.pk,0,'Stale','known')
        a=transition(self.author,a.pk,a.etag,'submitted','')
        with self.assertRaises(PermissionDenied):transition(self.author,a.pk,a.etag,'validated','self')
        a=transition(self.reviewer,a.pk,a.etag,'validated','Reviewed declaration sufficient')
        a=save_answer(self.author,a.pk,a.etag,'Corrected operation','known')
        self.assertEqual(a.state,'draft');self.assertEqual(a.revisions.count(),2);self.assertEqual(Review.objects.count(),1)
    def test_unknown_outbox_idempotency(self):
        a=save_answer(self.author,self.answer.pk,0,'','unknown');save_answer(self.author,a.pk,a.etag,'','unknown')
        self.assertEqual(Task.objects.count(),1)
        call_command('worker');call_command('worker');self.assertEqual(Notification.objects.count(),1)
    def test_not_applicable_cannot_validate(self):
        a=save_answer(self.author,self.answer.pk,0,'Reason','not_applicable');a=transition(self.author,a.pk,a.etag,'submitted','')
        with self.assertRaises(ValidationError):transition(self.reviewer,a.pk,a.etag,'validated','review')
    def test_cross_service_api_and_dashboard(self):
        c=APIClient();c.force_authenticate(self.other)
        self.assertEqual(c.get(f'/api/v1/answers/{self.answer.pk}/').status_code,404)
        self.assertEqual(c.post(f'/api/v1/answers/{self.answer.pk}/save/',{'version':0,'content':'x','knowledge':'known'}).status_code,404)
        d=c.get('/api/v1/dashboard/').json();self.assertEqual(d['validated']['denominator'],0)
        self.assertEqual(d['validated']['label'],'Sin alcance definido')
    def test_expired_assignment(self):
        RoleAssignment.objects.filter(user=self.author).update(starts=date(2020,1,1),ends=date(2020,1,2))
        with self.assertRaises(PermissionDenied):save_answer(self.author,self.answer.pk,0,'x','known')
    def test_publication_requires_help(self):
        self.instance.refresh_from_db()
        save_help(self.author,self.instance.pk,self.instance.etag,{k:'' for k in HELP_FIELDS})
        with self.assertRaises(ValidationError):publish(self.reviewer,self.instance.pk)
    def test_private_evidence(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        a=save_answer(self.author,self.answer.pk,0,'Statement','known');c=APIClient();c.force_authenticate(self.author)
        with tempfile.TemporaryDirectory() as folder,override_settings(MEDIA_ROOT=folder):
            r=c.post(f'/api/v1/answers/{a.pk}/evidence/',{'version':a.etag,'file':SimpleUploadedFile('statement.txt',b'Declaration')},format='multipart');self.assertEqual(r.status_code,201,r.data)
            url=r.data['evidence'][0]['url'];c.force_authenticate(self.other);self.assertEqual(c.get(url).status_code,404)
            c.force_authenticate(self.author);response=c.get(url);self.assertEqual(response.status_code,200);self.assertIn('attachment',response['Content-Disposition'])
    def test_login_csrf(self):
        # Other tests use the same synthetic client IP; do not inherit their throttles.
        from django.core.cache import cache
        cache.clear()
        c=APIClient(enforce_csrf_checks=True);self.assertEqual(c.post('/api/v1/session/',{'username':'author','password':'synthetic-only'}).status_code,403)
    def test_import_is_idempotent_and_source_counts(self):
        path=Path(__file__).resolve().parents[2]/'Plan_Trabajo_Escuela_Salud_Modelo.docx'
        records,report=parse(path);self.assertEqual(report['counts']['question_original'],120);self.assertEqual(report['counts']['question_compliance'],54);self.assertEqual(report['counts']['regulation'],60)
        self.assertEqual(len({r['stable_id'] for r in records}),len(records))
        out=io.StringIO()
        for _ in range(2):call_command('import_plan',str(path),approve_sha=report['sha256'],actor='bootstrap',stdout=out)
        self.assertEqual(ImportBatch.objects.filter(digest=report['sha256']).count(),1)
        self.assertEqual(Question.objects.count(),178)
        self.assertTrue(any(r['links'] for r in records))
