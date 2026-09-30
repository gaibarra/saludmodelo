from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import *
from .publication import HELP_FIELDS

class AdministrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.operator = User.objects.create_superuser('operator', password='synthetic-test-password')
        self.director = User.objects.create_user('director')
        self.writer = User.objects.create_user('writer')
        self.reviewer = User.objects.create_user('reviewer')
        self.outsider = User.objects.create_user('outsider')
        self.institution = Institution.objects.create(name='Institution A synthetic')
        self.foreign = Institution.objects.create(name='Institution B synthetic')
        self.campus = Campus.objects.create(institution=self.institution, name='Campus A')
        self.site = Site.objects.create(campus=self.campus, name='Site A')
        self.service = Service.objects.create(site=self.site, name='Dental', confirmed=True)
        other_campus = Campus.objects.create(institution=self.foreign, name='Campus B')
        other_site = Site.objects.create(campus=other_campus, name='Site B')
        self.other_service = Service.objects.create(site=other_site, name='Psychology', confirmed=True)
        self.start = timezone.localdate() - timedelta(days=1)
        self.end = timezone.localdate() + timedelta(days=10)
        InstitutionMandate.objects.create(institution=self.institution, user=self.director, approved_by=self.operator, starts=self.start, ends=self.end, rationale='Synthetic authorization')
        for user in [self.director, self.writer, self.reviewer]: InstitutionMember.objects.create(institution=self.institution, user=user)
        InstitutionMember.objects.create(institution=self.foreign, user=self.outsider)
        for user,service,role in [(self.writer,self.service,'contributor'),(self.reviewer,self.service,'manager'),(self.outsider,self.other_service,'manager')]:
            RoleAssignment.objects.create(user=user,service=service,role=role,starts=self.start,ends=self.end,approved_by=self.director)
        batch=ImportBatch.objects.create(digest='b'*64,filename='synthetic.docx')
        CatalogAccess.objects.create(institution=self.institution,batch=batch,granted_by=self.operator)
        source=SourceRecord.objects.create(batch=batch,stable_id='Q-synthetic',locator='paragraph 1',section='Synthetic',text='How is the appointment confirmed?',kind='question_original')
        question=Question.objects.create(stable_id='Q-synthetic')
        self.qv=QuestionVersion.objects.create(question=question,source=source,version=1)
        self.client=APIClient();self.client.force_authenticate(self.director)

    def post(self,path,data,status=200):
        response=self.client.post('/api/v1/'+path,data,format='json')
        self.assertEqual(response.status_code,status,response.data)
        return response.data

    def select(self):
        self.client.force_authenticate(self.director)
        self.post('questionnaires/select/',{'service':self.service.pk,'question_versions':[self.qv.pk],'rationale':'Confirmed scope'})
        return QuestionnaireInstance.objects.get(service=self.service,question_version=self.qv)

    def help_cycle(self,instance):
        self.client.force_authenticate(self.writer)
        result=self.post(f'questionnaires/{instance.pk}/help/',{'version':instance.etag,'content':{k:'Specific synthetic guidance' for k in HELP_FIELDS}})
        self.client.force_authenticate(self.reviewer)
        result=self.post(f'questionnaires/{instance.pk}/review/',{'version':result['etag'],'decision':'approved','rationale':'Complete, appropriate and sufficient'})
        return self.post(f'questionnaires/{instance.pk}/publish/',{'version':result['etag']})

    def test_authority_and_cross_institution_boundaries(self):
        data=self.client.get('/api/v1/administration/setup/').data
        self.assertEqual([i['id'] for i in data['institutions']],[self.institution.pk])
        self.assertNotIn(self.outsider.pk,[u['id'] for u in data['users']])
        self.post('administration/sites/',{'campus':self.other_service.site.campus_id,'name':'Forbidden'},404)
        self.post(f'administration/services/{self.other_service.pk}/confirm/',{'version':0,'rationale':'Forbidden'},404)
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.get('/api/v1/administration/setup/').data['institutions'],[])
        self.post('administration/campuses/',{'institution':self.institution.pk,'name':'Not authorized'},403)

    def test_create_confirm_and_conflict(self):
        c=self.post('administration/campuses/',{'institution':self.institution.pk,'name':'New campus'},201)
        site=self.post('administration/sites/',{'campus':c['id'],'name':'New site','timezone':'America/Merida'},201)
        service=self.post('administration/services/',{'site':site['id'],'name':'New service','kind':'service'},201)
        self.assertFalse(service['confirmed'])
        self.post(f"administration/services/{service['id']}/confirm/",{'version':0,'rationale':'Institution confirms operation'})
        self.post(f"administration/services/{service['id']}/confirm/",{'version':0,'rationale':'Stale'},409)
        self.assertEqual(GovernanceEvent.objects.filter(action='service.confirmed').count(),1)

    def test_user_password_and_no_privilege_injection(self):
        base={'institution':self.institution.pk,'username':'new-user','first_name':'Synthetic','password':'N4tive-Test-Only!726'}
        self.post('administration/users/',{**base,'is_superuser':True},400)
        self.post('administration/users/',{**base,'password':'1234'},400)
        result=self.post('administration/users/',base,201)
        user=get_user_model().objects.get(pk=result['id'])
        self.assertFalse(user.is_superuser);self.assertTrue(user.check_password(base['password']))
        self.assertFalse(RoleAssignment.objects.filter(user=user).exists())

    def test_assignments_self_foreign_overlap_and_revocation(self):
        base={'user':self.writer.pk,'service':self.service.pk,'role':'auditor','starts':str(self.start),'ends':str(self.end),'rationale':'Role authorized for test'}
        self.post('administration/assignments/',{**base,'user':self.director.pk},400)
        self.post('administration/assignments/',{**base,'user':self.outsider.pk},404)
        self.post('administration/assignments/',{**base,'starts':str(self.end),'ends':str(self.start)},400)
        grant=self.post('administration/assignments/',base,201)
        self.post('administration/assignments/',base,400)
        self.post(f"administration/assignments/{grant['id']}/revoke/",{'rationale':'Appointment ended'})
        self.assertIsNotNone(RoleAssignment.objects.get(pk=grant['id']).revoked_at)
        contributor=RoleAssignment.objects.get(user=self.writer,role='contributor')
        self.post(f'administration/assignments/{contributor.pk}/revoke/',{'rationale':'Revoked capture'})
        self.client.force_authenticate(self.writer)
        self.assertEqual(self.client.get('/api/v1/services/').data['count'],0)

    def test_catalog_grants_and_selection_are_scoped_and_idempotent(self):
        self.assertEqual(len(self.client.get(f'/api/v1/administration/catalog/?service={self.service.pk}').data['questions']),1)
        self.assertEqual(self.client.get(f'/api/v1/administration/catalog/?service={self.other_service.pk}').status_code,404)
        instance=self.select();self.select()
        self.assertEqual(QuestionnaireInstance.objects.count(),1)
        self.assertEqual(GovernanceEvent.objects.filter(action='questionnaire.scope_added').count(),1)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(f'/api/v1/questionnaires/{instance.pk}/').status_code,404)
        self.post(f'questionnaires/{instance.pk}/help/',{'version':0,'content':{k:'Forbidden' for k in HELP_FIELDS}},404)

    def test_help_review_publication_and_answer_invalidation(self):
        instance=self.select();result=self.help_cycle(instance)
        answer=Answer.objects.get(instance=instance)
        self.client.force_authenticate(self.writer)
        a=self.post(f'answers/{answer.pk}/save/',{'version':0,'content':'Confirmed declaration','knowledge':'known'})
        a=self.post(f'answers/{answer.pk}/transition/',{'version':a['etag'],'target':'submitted'})
        self.client.force_authenticate(self.reviewer)
        a=self.post(f'answers/{answer.pk}/transition/',{'version':a['etag'],'target':'validated','rationale':'Declaration sufficient'})
        old_help=QuestionnaireInstance.objects.get(pk=instance.pk).published_help_id
        self.client.force_authenticate(self.writer)
        draft=self.post(f'questionnaires/{instance.pk}/help/',{'version':result['etag'],'content':{k:'Changed synthetic guidance' for k in HELP_FIELDS}})
        self.assertEqual(Answer.objects.get(pk=answer.pk).state,'validated')
        self.assertEqual(QuestionnaireInstance.objects.get(pk=instance.pk).published_help_id,old_help)
        self.client.force_authenticate(self.reviewer)
        reviewed=self.post(f'questionnaires/{instance.pk}/review/',{'version':draft['etag'],'decision':'approved','rationale':'New guidance reviewed'})
        self.post(f'questionnaires/{instance.pk}/publish/',{'version':reviewed['etag']})
        answer.refresh_from_db();self.assertEqual(answer.state,'draft');self.assertGreater(answer.etag,a['etag'])
        self.assertEqual(Review.objects.count(),1)
        self.assertEqual(answer.revisions.get().help_revision_id,old_help)
        self.assertEqual(HelpRevision.objects.filter(instance=instance).count(),2)
        self.assertEqual(self.client.get('/api/v1/dashboard/').data['validated']['numerator'],0)

    def test_incomplete_self_review_and_stale_edits_are_rejected(self):
        instance=self.select();self.client.force_authenticate(self.reviewer)
        content={k:'' for k in HELP_FIELDS}
        draft=self.post(f'questionnaires/{instance.pk}/help/',{'version':0,'content':content})
        self.post(f'questionnaires/{instance.pk}/review/',{'version':draft['etag'],'decision':'approved','rationale':'Self'},400)
        self.post(f'questionnaires/{instance.pk}/help/',{'version':0,'content':content},409)
        RoleAssignment.objects.create(user=self.writer,service=self.service,role='manager',starts=self.start,ends=self.end,approved_by=self.director)
        self.client.force_authenticate(self.writer)
        self.post(f'questionnaires/{instance.pk}/review/',{'version':draft['etag'],'decision':'approved','rationale':'Incomplete'},400)
        self.post(f'questionnaires/{instance.pk}/publish/',{'version':draft['etag']},400)

    def test_help_does_not_leak_to_same_question_in_other_service(self):
        instance=self.select();self.help_cycle(instance)
        other=QuestionnaireInstance.objects.create(service=self.other_service,question_version=self.qv)
        self.client.force_authenticate(self.outsider)
        data=self.client.get(f'/api/v1/questionnaires/{other.pk}/').data
        self.assertEqual(data['revisions'],[]);self.assertFalse(data['published'])
        self.post(f'questionnaires/{other.pk}/publish/',{'version':0},400)

    def test_expired_mandate_and_denominator_include_unpublished(self):
        instance=self.select()
        self.client.force_authenticate(self.reviewer)
        data=self.client.get('/api/v1/dashboard/').data
        self.assertEqual(data['validated']['denominator'],1);self.assertEqual(data['validated']['numerator'],0)
        InstitutionMandate.objects.filter(user=self.director).update(starts=self.start-timedelta(days=5),ends=self.start)
        self.client.force_authenticate(self.director)
        self.post('administration/campuses/',{'institution':self.institution.pk,'name':'Expired'},403)

    def test_publish_requires_complete_coverage_of_selected_scope(self):
        instance=self.select()
        source=SourceRecord.objects.create(batch=self.qv.source.batch,stable_id='second',locator='p2',section='Synthetic',text='Second synthetic question',kind='question_original')
        question=Question.objects.create(stable_id='second')
        version=QuestionVersion.objects.create(question=question,source=source,version=1)
        QuestionnaireInstance.objects.create(service=self.service,question_version=version)
        self.client.force_authenticate(self.writer)
        draft=self.post(f'questionnaires/{instance.pk}/help/',{'version':0,'content':{k:'Synthetic guidance' for k in HELP_FIELDS}})
        self.client.force_authenticate(self.reviewer)
        reviewed=self.post(f'questionnaires/{instance.pk}/review/',{'version':draft['etag'],'decision':'approved','rationale':'Specific guidance reviewed'})
        self.post(f'questionnaires/{instance.pk}/publish/',{'version':reviewed['etag']},400)
        self.assertEqual(Answer.objects.count(),0)

    def test_institutional_dashboard_does_not_grant_answer_access(self):
        instance=self.select();self.help_cycle(instance)
        self.client.force_authenticate(self.director)
        dashboard=self.client.get('/api/v1/dashboard/').data
        self.assertEqual(dashboard['validated']['denominator'],1)
        answer=Answer.objects.get(instance=instance)
        self.assertEqual(self.client.get(f'/api/v1/answers/{answer.pk}/').status_code,404)
