from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HelpMigrationTests(TransactionTestCase):
    def test_legacy_publication_and_answer_are_preserved_per_service(self):
        previous = [('core', '0003_alter_sourcerecord_section')]
        executor = MigrationExecutor(connection)
        # Restore the actual current schema so later tests never inherit an old version.
        current = executor.loader.graph.leaf_nodes('core')
        try:
            executor.migrate(previous)
            apps = executor.loader.project_state(previous).apps
            User = apps.get_model('auth', 'User')
            author = User.objects.create(username='migration-author')
            reviewer = User.objects.create(username='migration-reviewer')
            institution = apps.get_model('core', 'Institution').objects.create(name='Synthetic migration')
            campus = apps.get_model('core', 'Campus').objects.create(institution=institution, name='Campus')
            site = apps.get_model('core', 'Site').objects.create(campus=campus, name='Site')
            batch = apps.get_model('core', 'ImportBatch').objects.create(digest='f'*64, filename='synthetic')
            source = apps.get_model('core', 'SourceRecord').objects.create(batch=batch, stable_id='legacy', locator='paragraph 1', section='Synthetic', text='Legacy question', kind='question_original')
            question = apps.get_model('core', 'Question').objects.create(stable_id='legacy')
            version = apps.get_model('core', 'QuestionVersion').objects.create(question=question, source=source, version=1)
            from django.utils import timezone
            apps.get_model('core', 'QuestionHelpVersion').objects.create(question_version=version, author=author, reviewed_by=reviewer, reviewed_at=timezone.now(), content={'plain_explanation': 'Legacy content preserved verbatim'})
            ids=[]
            for name in ['First service', 'Second service']:
                service=apps.get_model('core', 'Service').objects.create(site=site, name=name, confirmed=True)
                apps.get_model('core', 'RoleAssignment').objects.create(user=author, service=service, role='contributor', starts=timezone.localdate(), ends=timezone.localdate(), approved_by=reviewer)
                instance=apps.get_model('core', 'QuestionnaireInstance').objects.create(service=service, question_version=version, published=True)
                answer=apps.get_model('core', 'Answer').objects.create(instance=instance, state='validated', version=1)
                apps.get_model('core', 'AnswerRevision').objects.create(answer=answer, version=1, content='Retained answer', author=author)
                ids.append(instance.pk)
            executor=MigrationExecutor(connection)
            executor.migrate(current)
            apps=executor.loader.project_state(current).apps
            instances=list(apps.get_model('core', 'QuestionnaireInstance').objects.filter(pk__in=ids))
            self.assertEqual(len({i.published_help_id for i in instances}),2)
            self.assertTrue(all(i.published for i in instances))
            self.assertTrue(apps.get_model('core', 'InstitutionMember').objects.filter(user_id=author.pk, institution_id=institution.pk).exists())
            for instance in instances:
                help_revision=apps.get_model('core', 'HelpRevision').objects.get(pk=instance.published_help_id)
                self.assertEqual(help_revision.content['plain_explanation'],'Legacy content preserved verbatim')
                answer=apps.get_model('core','Answer').objects.get(instance_id=instance.pk)
                self.assertEqual(answer.state,'validated')
                revision=apps.get_model('core','AnswerRevision').objects.get(answer_id=answer.pk)
                self.assertEqual(revision.content,'Retained answer')
                self.assertEqual(revision.help_revision_id,help_revision.pk)
        finally:
            MigrationExecutor(connection).migrate(current)
