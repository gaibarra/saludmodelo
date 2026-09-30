from datetime import timedelta
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from threading import Thread
from http.server import BaseHTTPRequestHandler,HTTPServer
from unittest.mock import patch
import uuid
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes,serialization
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase,TransactionTestCase,override_settings
from django.utils import timezone
from . import monitoring as m
from .models import *
from . import tests as fixtures
from .workflow import save_answer

class LocalMonitoringTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='salud-monitor-test-');self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name);self.now=timezone.now()

    def test_unknown_not_healthy_and_database_failure_is_sanitized(self):
        with patch.object(m,'db_checks',side_effect=RuntimeError('SECRET-database-password')),override_settings(MEDIA_ROOT=self.work):
            report=m.collect(self.work)
        values={c['key']:c for c in report['checks']}
        self.assertEqual(values['database']['status'],'critical')
        self.assertEqual(values['documents']['status'],'unknown')
        self.assertEqual(values['worker']['status'],'unknown')
        self.assertEqual(values['backend_http']['status'],'unknown')
        self.assertNotIn('SECRET',json.dumps(report))
        self.assertEqual(report['exit_code'],2)

    def test_heartbeat_expiry_failure_future(self):
        for state,age,expected in [('ok',60,'ok'),('ok',2701,'critical'),('running',30,'ok'),('failed',10,'critical'),('ok',-60,'critical')]:
            m.write_json(self.work/'worker.json',{'state':state,'updated_at':(self.now-timedelta(seconds=age)).isoformat()})
            self.assertEqual(m.heartbeat_check(self.work,self.now)['status'],expected)

    def test_transitions_deduplicated_recovery_bounded_and_stale_report_rejected(self):
        report={'observed_at':self.now.isoformat(),'checks':[m.observation('database','critical','Unavailable')]}
        first=m.persist(self.work,report);second=m.persist(self.work,report)
        self.assertEqual(first['transitions'],second['transitions'])
        report['checks'][0]['status']='ok'
        result=m.persist(self.work,report)
        self.assertEqual(result['transitions'][-1]['previous'],'critical')
        self.assertEqual(len(result['transitions']),2)
        self.assertEqual((self.work/'monitor.json').stat().st_mode&0o777,0o600)
        report['observed_at']=(self.now-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError):m.persist(self.work,report)
        result['transitions']=[{'synthetic':True}]*205
        m.write_json(self.work/'monitor.json',result)
        report['observed_at']=self.now.isoformat()
        self.assertEqual(len(m.persist(self.work,report)['transitions']),200)

    def test_private_directory_lock_and_corrupt_report(self):
        public=self.work/'public';public.mkdir(mode=0o755)
        with self.assertRaises(ValueError):m.private_directory(public)
        with m.lock(self.work,'worker.lock'):
            with self.assertRaises(BlockingIOError),m.lock(self.work,'worker.lock'):pass
        (self.work/'monitor.json').write_text('not json')
        with self.assertRaises(ValueError):m.persist(self.work,{'checks':[]})

    def test_disk_thresholds(self):
        from collections import namedtuple
        Usage=namedtuple('Usage','total used free')
        for free,expected in [(512*1024**2,'critical'),(8*1024**3,'warning'),(20*1024**3,'ok')]:
            with patch.object(m.shutil,'disk_usage',return_value=Usage(100*1024**3,0,free)):
                self.assertEqual(m.disk_check(self.work)['status'],expected)

    def test_certificate_real_pem_expired_warning_and_valid(self):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        name=x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME,'synthetic.invalid')])
        for days,expected in [(-1,'critical'),(5,'critical'),(20,'warning'),(90,'ok')]:
            cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(self.now-timedelta(days=10)).not_valid_after(self.now+timedelta(days=days)).sign(key,hashes.SHA256())
            path=self.work/'cert.pem';path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            self.assertEqual(m.certificate_check(path,self.now)['status'],expected)
        path.write_bytes(b'bad');self.assertEqual(m.certificate_check(path,self.now)['status'],'critical')

    def test_backup_integrity_age_and_restore_binding(self):
        archive=self.work/'backup.tar.age';archive.write_bytes(b'age-encryption.org/v1\nsynthetic-envelope-only')
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        receipt={'status':'encrypted_local_only','snapshot_at':self.now.isoformat(),'completed_at':self.now.isoformat(),'encrypted_sha256':digest,'encrypted_bytes':archive.stat().st_size,'offsite_verified':True}
        m.write_json(self.work/'receipt.json',receipt)
        report={'status':'isolated_restore_verified','encrypted_sha256':digest,'verified_at':self.now.isoformat()}
        m.write_json(self.work/'restore.json',report)
        values=m.backup_check(self.work,self.work/'restore.json',self.now)
        self.assertEqual([c['status'] for c in values],['ok','ok','unknown'])
        self.assertEqual(m.backup_check(self.work,None,self.now+timedelta(hours=2))[0]['status'],'critical')
        report['encrypted_sha256']='different';m.write_json(self.work/'restore.json',report)
        self.assertEqual(m.backup_check(self.work,self.work/'restore.json',self.now)[1]['status'],'unknown')
        archive.write_bytes(b'tampered')
        self.assertEqual(m.backup_check(self.work,None,self.now)[0]['status'],'critical')

    def test_http_only_explicit_loopback_and_no_redirect(self):
        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(200 if self.path=='/' else 302)
                self.send_header('Location','https://example.invalid/');self.end_headers()
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}'
            self.assertEqual(m.http_check('frontend',url+'/','/')['status'],'ok')
            self.assertEqual(m.http_check('backend',url+'/api/v1/session/','/api/v1/session/')['metrics']['http_status'],302)
            with patch.object(m.http.client,'HTTPConnection') as conn:
                self.assertEqual(m.http_check('bad','http://example.invalid/','/')['status'],'critical');conn.assert_not_called()
        finally:server.shutdown();server.server_close();thread.join()

    def test_worker_cycle_records_success_and_sanitized_failure(self):
        target='core.management.commands.worker_cycle.call_command'
        with patch(target) as commands:
            call_command('worker_cycle',state_dir=str(self.work),stdout=io.StringIO())
            self.assertEqual([args.args[0] for args in commands.call_args_list],['tracking_reminders','worker','extract_evidence','process_ai','scheduled_reports'])
        previous=m.read_json(self.work/'worker.json');self.assertEqual(previous['state'],'ok')
        with patch(target,side_effect=RuntimeError('SENSITIVE-CONTENT')):
            with self.assertRaises(CommandError):call_command('worker_cycle',state_dir=str(self.work),stdout=io.StringIO())
        current=m.read_json(self.work/'worker.json')
        self.assertEqual(current['state'],'failed');self.assertEqual(current['last_success'],previous['last_success'])
        self.assertNotIn('SENSITIVE',json.dumps(current))

    def test_command_nonzero_for_unknown_and_persists_private_report(self):
        report={'observed_at':self.now.isoformat(),'status':'attention','exit_code':1,'checks':[m.observation('worker','unknown','Missing')]}
        with patch('core.management.commands.monitor_health.collect',return_value=report):
            with self.assertRaises(CommandError) as error:call_command('monitor_health',state_dir=self.work,stdout=io.StringIO())
        self.assertEqual(error.exception.returncode,1)
        self.assertEqual(m.read_json(self.work/'monitor.json')['status'],'attention')


class DatabaseMonitoringTests(TransactionTestCase):
    def setUp(self):
        self.fixture=fixtures.WorkflowTests();self.fixture.setUp();self.now=timezone.now()
        self.answer=save_answer(self.fixture.author,self.fixture.answer.pk,0,'Synthetic monitor data','unknown')
        self.doc=EvidenceDocument.objects.create(answer=self.answer,revision=self.answer.revisions.get(),file='evidence/synthetic.txt',sha256='a'*64,uploader=self.fixture.author,original_name='DO-NOT-EXPOSE.txt')
        self.job=EvidenceExtraction.objects.create(document=self.doc,state='running',leased_until=self.now-timedelta(seconds=1))

    def test_queue_metrics_do_not_consume_jobs_or_leak_content(self):
        checks=m.db_checks(self.now);values={c['key']:c for c in checks}
        self.assertEqual(values['documents']['status'],'critical')
        self.assertEqual(values['outbox']['metrics']['pending'],1)
        self.job.refresh_from_db();self.assertEqual(self.job.state,'running')
        self.assertIsNone(OutboxEvent.objects.get().delivered_at)
        serialized=json.dumps(checks)
        self.assertNotIn('DO-NOT-EXPOSE',serialized);self.assertNotIn('Synthetic monitor data',serialized)

    def test_ai_budget_and_security_thresholds(self):
        policy=AIServicePolicy.objects.create(service=self.fixture.service,approved_by=self.fixture.admin,enabled=True,monthly_calls=10,monthly_tokens=100,monthly_cost_limit=Decimal('1'))
        request=AIRequest.objects.create(instance=self.fixture.instance,requested_by=self.fixture.author,provider='openai',client_key=uuid.uuid4(),answer_etag=self.answer.etag,state='running',started_at=self.now-timedelta(minutes=3),reserved_tokens=80,reserved_cost=Decimal('.8'))
        SecurityEvent.objects.bulk_create([SecurityEvent(user=self.fixture.author,action='mfa.failed') for _ in range(20)])
        values={c['key']:c for c in m.db_checks(timezone.now())}
        self.assertEqual(values['ai_queue']['status'],'critical')
        self.assertEqual(values['ai_budget']['status'],'warning')
        self.assertEqual(values['mfa_attempts']['status'],'critical')
        request.reserved_cost=Decimal('1');request.save()
        values={c['key']:c for c in m.db_checks(timezone.now())}
        self.assertEqual(values['ai_budget']['status'],'critical')

    def test_real_worker_cycle_preserves_monitor_separation(self):
        self.job.state='ready';self.job.save()
        with tempfile.TemporaryDirectory(prefix='salud-worker-test-') as tmp:
            call_command('worker_cycle',state_dir=tmp,stdout=io.StringIO())
            self.assertEqual(m.read_json(Path(tmp)/'worker.json')['state'],'ok')
            self.assertEqual(Notification.objects.count(),1)
            values={c['key']:c for c in m.db_checks(timezone.now())}
            self.assertEqual(values['outbox']['status'],'ok')
