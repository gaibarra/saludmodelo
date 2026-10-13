import io
from django.core.management import call_command,CommandError
from django.test import TestCase,override_settings
from .test_schools import SchoolTests
from .test_public_portal import PatientPortalTests
from .models import Service,RoleAssignment,AcademicPractice,GovernanceEvent
from .access import scopes
from .governance import managed_services
from .cash import managers,eligible

@override_settings(MFA_REQUIRE_PRIVILEGED=False)
class ServiceArchiveTests(TestCase):
    setUp=SchoolTests.setUp
    client_for=SchoolTests.client_for

    def archive(self,apply=True):
        self.dental.name='Odontología · DEMO';self.dental.save()
        self.approver.is_superuser=True;self.approver.save()
        call_command('archive_demo_service',service=self.dental.pk,expected_name=self.dental.name,actor=self.approver.username,apply=apply,stdout=io.StringIO())

    def test_dry_run_preserves_service_and_archive_preserves_history(self):
        original=Service.objects.get(pk=self.dental.pk)
        self.archive(False)
        self.dental.refresh_from_db();self.assertIsNone(self.dental.archived_at)
        roles=list(RoleAssignment.objects.values());practices=list(AcademicPractice.objects.values())
        foreign=Service.objects.get(pk=self.physio.pk).__dict__.copy();foreign.pop('_state')
        self.archive()
        self.dental.refresh_from_db();self.assertIsNotNone(self.dental.archived_at)
        self.assertFalse(self.dental.confirmed);self.assertEqual(self.dental.etag,original.etag+1)
        self.assertEqual(list(RoleAssignment.objects.values()),roles)
        self.assertEqual(list(AcademicPractice.objects.values()),practices)
        after=Service.objects.get(pk=self.physio.pk).__dict__.copy();after.pop('_state');self.assertEqual(after,foreign)
        self.archive();self.assertEqual(GovernanceEvent.objects.filter(action='service.archived').count(),1)

    def test_hidden_from_selectors_permissions_and_direct_assignment(self):
        self.archive()
        c=self.client_for(self.director)
        self.assertEqual(c.get(f'/api/v1/schools/{self.dent.pk}/management/').data['services'],[])
        self.assertNotIn(self.dental.pk,scopes(self.director))
        self.assertFalse(managed_services(self.director).filter(pk=self.dental.pk).exists())
        self.assertFalse(managers(self.director).filter(pk=self.dental.pk).exists())
        self.assertFalse(eligible(self.student_user).filter(pk=self.dental.pk).exists())
        self.assertEqual(c.get(f'/api/v1/tracking/services/{self.dental.pk}/').status_code,404)
        self.assertEqual(c.post(f'/api/v1/administration/services/{self.dental.pk}/confirm/',{'version':1,'rationale':'Reactivar'},format='json').status_code,404)
        payload={'service':self.dental.pk,'user':self.supervisor.pk,'role':'manager','starts':str(self.start),'ends':str(self.end),'rationale':'Asignación nueva'}
        self.assertEqual(c.post('/api/v1/administration/assignments/',payload,format='json').status_code,404)
        self.assertEqual(c.get(f'/api/v1/schools/{self.health.pk}/management/').status_code,404)

    def test_cannot_archive_real_service(self):
        self.approver.is_superuser=True;self.approver.save()
        with self.assertRaises(CommandError):
            call_command('archive_demo_service',service=self.dental.pk,expected_name=self.dental.name,actor=self.approver.username,apply=True,stdout=io.StringIO())
        self.dental.refresh_from_db();self.assertIsNone(self.dental.archived_at)

@override_settings(PATIENT_PORTAL_ENABLED=True)
class ArchivedPublicServiceTests(TestCase):
    setUp=PatientPortalTests.setUp
    register=PatientPortalTests.register
    request=PatientPortalTests.request

    def test_archived_service_cannot_receive_requests_even_if_confirmed(self):
        from django.utils import timezone
        from .public_portal import available_slugs
        self.dental.archived_at=timezone.now();self.dental.save()
        self.assertNotIn('odontologia',available_slugs())
        self.assertIn('psicologia',available_slugs())
        self.register(self.client,'archive-test@example.org')
        self.assertEqual(self.request(self.client).status_code,400)
