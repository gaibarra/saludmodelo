"""Real age + PostgreSQL restore in owned private-socket clusters."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import recovery as r
from cryptography.fernet import Fernet
TEST_MFA_KEY=Fernet.generate_key().decode()


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mask = os.umask(0o077)
        cls.temp = tempfile.TemporaryDirectory(prefix='salud-recovery-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.addClassCleanup(os.umask, cls.mask)
        cls.work = Path(cls.temp.name)
        cls.storage = cls.work/'private'
        cls.storage.mkdir(mode=0o700)
        cls.cluster = r.isolated_cluster(cls.work)
        cls.socket = cls.cluster.__enter__()
        cls.addClassCleanup(cls.cluster.__exit__, None, None, None)
        cls.env = cls.app_env(cls.socket, 'salud_recovery_test', cls.storage)
        r.run([r.PG_BIN/'createdb', 'salud_recovery_test'], env=cls.env)
        r.run([sys.executable, ROOT/'backend/manage.py', 'migrate', '--noinput'], env=cls.env)
        r.run([sys.executable, ROOT/'tests/recovery_fixture.py', 'seed'], env=cls.env)
        cls.identity = cls.work/'identity.txt'
        r.run(['age-keygen', '-o', cls.identity])
        cls.recipient = subprocess.check_output(['age-keygen', '-y', cls.identity], text=True).strip()
        cls.output = cls.work/'backup'
        cls.receipt = r.backup(cls.socket, 'salud_recovery_test', 'recovery_owner', cls.storage, cls.recipient, cls.output)
        cls.archive = cls.output/'backup.tar.age'

    @staticmethod
    def app_env(socket, database, storage):
        return {**r.environment(socket, database, 'recovery_owner'), 'DJANGO_SECRET_KEY':'synthetic-recovery-only',
                'MFA_ENCRYPTION_KEY':TEST_MFA_KEY,'DJANGO_SETTINGS_MODULE':'config.settings', 'DEBUG':'1', 'PRIVATE_STORAGE':str(storage),
                'AI_EXTERNAL_ENABLED':'0', 'OPENAI_API_KEY':'', 'DEEPSEEK_API_KEY':'', 'AI_MODELS_JSON':'{}',
                'DOCUMENT_SIGNATURES':'', 'DOCUMENT_OCR_RUNTIME':''}

    def test_real_restore_content_history_and_authorization(self):
        def verify(socket, storage):
            env = self.app_env(socket, 'salud_restore', storage)
            r.run([sys.executable, ROOT/'tests/recovery_fixture.py', 'verify'], env=env)
        report = r.restore_check(self.archive, self.receipt['encrypted_sha256'], self.identity, self.work/'report.json', verifier=verify)
        self.assertEqual(report['status'], 'isolated_restore_verified')
        self.assertEqual(report['document_count'], 1)
        self.assertGreater(report['table_count'], 30)
        self.assertFalse(report['production_rpo_rto_demonstrated'])
        self.assertEqual(self.archive.stat().st_mode & 0o777, 0o600)
        # Save only non-sensitive measurements, never keys, raw dumps or restored files.
        (ROOT/'docs/recovery-test-report.json').write_text(json.dumps({**report, 'fixture':'synthetic_only', 'application_checks':['answer_history','help_reviews','document_bytes','authorized_download','foreign_service_denied','technical_superuser_denied','pending_outbox_preserved','next_id_allocation','mfa_restored_with_separate_key','interview_memory_and_history']}, indent=2)+'\n')

    def test_encrypted_payload_and_corruption_fail_closed(self):
        raw = self.archive.read_bytes()
        self.assertTrue(raw.startswith(b'age-encryption.org/v1'))
        self.assertNotIn(b'Synthetic recovery evidence', raw)
        corrupt = self.work/'corrupt.age'
        corrupt.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        target = self.work/'corrupt-report.json'
        with self.assertRaisesRegex(ValueError, 'huella'):
            r.restore_check(corrupt, self.receipt['encrypted_sha256'], self.identity, target)
        with self.assertRaises(RuntimeError):
            r.restore_check(corrupt, r.digest(corrupt), self.identity, target)
        self.assertFalse(target.exists())

    def test_wrong_identity_fails_without_success_report(self):
        key = self.work/'wrong-key.txt'
        r.run(['age-keygen', '-o', key])
        report = self.work/'wrong-key-report.json'
        with self.assertRaises(RuntimeError):
            r.restore_check(self.archive, self.receipt['encrypted_sha256'], key, report)
        self.assertFalse(report.exists())

    def test_missing_or_changed_evidence_aborts_backup(self):
        original = next(self.storage.rglob('*.txt'))
        raw = original.read_bytes()
        try:
            original.write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'huella'):
                r.backup(self.socket, 'salud_recovery_test', 'recovery_owner', self.storage, self.recipient, self.work/'bad-backup')
            self.assertFalse((self.work/'bad-backup').exists())
        finally:
            original.write_bytes(raw)
        moved = original.with_suffix('.saved')
        original.rename(moved)
        try:
            with self.assertRaises(FileNotFoundError):
                r.backup(self.socket, 'salud_recovery_test', 'recovery_owner', self.storage, self.recipient, self.work/'missing-backup')
            self.assertFalse((self.work/'missing-backup').exists())
        finally:
            moved.rename(original)

    def test_no_overwrite_no_tcp_and_no_existing_cluster(self):
        with self.assertRaises(FileExistsError):
            r.backup(self.socket, 'salud_recovery_test', 'recovery_owner', self.storage, self.recipient, self.output)
        with self.assertRaises(OSError):
            r.backup(Path('127.0.0.1'), 'salud_recovery_test', 'recovery_owner', self.storage, self.recipient, self.work/'tcp')
        with r.connect(self.socket, 'salud_recovery_test', 'recovery_owner') as conn:
            self.assertEqual(conn.execute('SHOW listen_addresses').fetchone()[0], '')
        blocked = self.work/'existing'
        blocked.mkdir()
        (blocked/'pg').mkdir()
        with self.assertRaises(FileExistsError), r.isolated_cluster(blocked):
            self.fail('Must never reuse an existing cluster')

    def test_archive_paths_links_duplicates_and_manifest_hashes(self):
        for number, kind in enumerate(('traversal', 'link', 'duplicate', 'hash')):
            archive = self.work/f'bad-{number}.tar'
            with tarfile.open(archive, 'w') as tar:
                member = tarfile.TarInfo('../escape' if kind == 'traversal' else 'database.dump')
                if kind == 'link':
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/etc/passwd'
                    tar.addfile(member)
                else:
                    member.size = 1
                    tar.addfile(member, io.BytesIO(b'x'))
                    if kind == 'duplicate':
                        tar.addfile(member, io.BytesIO(b'x'))
                    if kind == 'hash':
                        raw = r.json_bytes({'format':1, 'project':'salud-modelo', 'files':{'database.dump':{'bytes':1,'sha256':'0'*64}}})
                        meta = tarfile.TarInfo('manifest.json')
                        meta.size = len(raw)
                        tar.addfile(meta, io.BytesIO(raw))
            destination = self.work/f'bad-unpack-{number}'
            destination.mkdir()
            with self.assertRaises(ValueError):
                r.unpack_checked(archive, destination)
        self.assertFalse((self.work/'escape').exists())

    def test_rejects_foreign_schema(self):
        with r.connect(self.socket, 'salud_recovery_test', 'recovery_owner') as conn:
            conn.execute('CREATE SCHEMA unrelated_synthetic')
        try:
            with self.assertRaisesRegex(ValueError, 'esquemas ajenos'):
                r.backup(self.socket, 'salud_recovery_test', 'recovery_owner', self.storage, self.recipient, self.work/'foreign-schema')
        finally:
            with r.connect(self.socket, 'salud_recovery_test', 'recovery_owner') as conn:
                conn.execute('DROP SCHEMA unrelated_synthetic')

    def test_snapshot_excludes_later_writes(self):
        original = r.inventory
        inserted = []
        def concurrent(conn):
            result = original(conn)
            with r.connect(self.socket, 'salud_recovery_test', 'recovery_owner') as writer:
                inserted.append(writer.execute("INSERT INTO core_institution (name) VALUES ('Concurrent synthetic row') RETURNING id").fetchone()[0])
            return result
        output = self.work/'concurrent'
        try:
            with patch.object(r, 'inventory', side_effect=concurrent):
                receipt = r.backup(self.socket, 'salud_recovery_test', 'recovery_owner', self.storage, self.recipient, output)
            # The dump must use the exported snapshot, otherwise table fingerprints disagree.
            r.restore_check(output/'backup.tar.age', receipt['encrypted_sha256'], self.identity, self.work/'concurrent-report.json')
        finally:
            with r.connect(self.socket, 'salud_recovery_test', 'recovery_owner') as conn:
                for pk in inserted:
                    conn.execute('DELETE FROM core_institution WHERE id=%s', [pk])


if __name__ == '__main__':
    unittest.main()
