from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.utils import timezone
from core import test_administration
from core.models import RoleAssignment,InstitutionMember,GovernanceEvent
from core.access import scopes

class SubstitutionTests(TestCase):
    def setUp(self):
        test_administration.AdministrationTests.setUp(self)
        self.sub=get_user_model().objects.create_user('temporary-substitute')
        InstitutionMember.objects.create(user=self.sub,institution=self.institution)
        self.source=RoleAssignment.objects.get(user=self.writer,role='contributor')
        self.url='/api/v1/administration/assignments/'
        self.payload={'user':self.sub.pk,'service':self.service.pk,'role':'contributor','starts':str(self.start),'ends':str(self.end),'rationale':'Authorized synthetic coverage','substitutes':self.source.pk}
    def create(self,**extra):return self.client.post(self.url,{**self.payload,**extra},format='json')
    def revoke(self,pk):return self.client.post(f'{self.url}{pk}/revoke/',{'rationale':'Synthetic revocation'},format='json')
    def test_grant_expiry_and_cascade_preserve_history(self):
        r=self.create();self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data['substitutes'],self.source.pk);self.assertIn(self.service.pk,scopes(self.sub))
        with patch('core.access.timezone.localdate',return_value=self.end+timedelta(days=1)):self.assertNotIn(self.service.pk,scopes(self.sub))
        self.assertEqual(self.revoke(self.source.pk).status_code,200)
        self.assertNotIn(self.service.pk,scopes(self.sub));self.assertEqual(RoleAssignment.objects.filter(pk__in=[r.data['id'],self.source.pk]).count(),2)
        self.assertEqual(self.revoke(self.source.pk).status_code,200)
        self.assertEqual(GovernanceEvent.objects.filter(action='assignment.substitution_revoked').count(),1)
    def test_bounds_same_role_different_person_and_no_chain(self):
        for extra in [{'role':'manager'},{'user':self.writer.pk},{'starts':str(self.start-timedelta(days=1))},{'ends':str(self.end+timedelta(days=1))}]:
            self.assertEqual(self.create(**extra).status_code,400)
        r=self.create().data
        self.assertEqual(self.create(user=self.reviewer.pk,substitutes=r['id']).status_code,400)
        self.assertEqual(self.create().status_code,400)
    def test_foreign_self_authorization_and_technical_account(self):
        foreign=RoleAssignment.objects.get(user=self.outsider)
        self.assertEqual(self.create(substitutes=foreign.pk).status_code,404)
        self.assertEqual(self.create(user=self.director.pk).status_code,400)
        self.client.force_authenticate(self.operator);self.assertEqual(self.create().status_code,404)
    def test_substitute_revocation_does_not_revoke_original(self):
        r=self.create().data;self.assertEqual(self.revoke(r['id']).status_code,200)
        self.source.refresh_from_db();self.assertIsNone(self.source.revoked_at)
        self.assertIn(self.service.pk,scopes(self.writer));self.assertNotIn(self.service.pk,scopes(self.sub))
    def test_inactive_revoked_or_already_expired_source(self):
        self.writer.is_active=False;self.writer.save();self.assertEqual(self.create().status_code,400)
        self.writer.is_active=True;self.writer.save()
        self.assertEqual(self.create(starts=str(self.start),ends=str(self.start)).status_code,400)
        self.revoke(self.source.pk);self.assertEqual(self.create().status_code,400)

class ConcurrentSubstitutionTests(TransactionTestCase):
    def test_grant_racing_with_source_revocation_leaves_no_active_substitution(self):
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        SubstitutionTests.setUp(self)
        def act(revoke):
            try:
                c=APIClient();c.force_authenticate(self.director)
                path=f'{self.url}{self.source.pk}/revoke/' if revoke else self.url
                return c.post(path,{'rationale':'Concurrent revocation'} if revoke else self.payload,format='json').status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(act,[False,True]))
        self.assertIn(results[0],[201,400]);self.assertEqual(results[1],200)
        self.assertFalse(RoleAssignment.objects.filter(substitutes=self.source,revoked_at__isnull=True).exists())
