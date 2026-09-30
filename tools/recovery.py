"""Project-only encrypted backups and disposable restore rehearsals; no deployment."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
PG_BIN = Path('/usr/lib/postgresql/16/bin')
MAX_BYTES = 1024 * 1024 * 1024  # Deliberate rehearsal bound; not a production capacity claim.
MAX_FILES = 100_000


def utcnow():
    return datetime.now(timezone.utc)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def private_dir(path):
    path = Path(path)
    info = path.stat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('Se requiere directorio propio sin acceso de grupo/otros.')
    return path.resolve()


def environment(socket, database, user):
    # Do not inherit PGOPTIONS, PGSERVICE, preload settings or another project's PGHOST.
    env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
    env.update(PGHOST=str(socket), PGPORT='5432', PGDATABASE=database, PGUSER=user,
               PGCONNECT_TIMEOUT='10', PGOPTIONS='-c statement_timeout=300000 -c lock_timeout=5000')
    return env


def run(command, *, env=None, stdout=subprocess.DEVNULL):
    result = subprocess.run([str(x) for x in command], env=env, stdout=stdout,
                            stderr=subprocess.PIPE, timeout=300)
    if result.returncode:
        # SQL errors may contain records or secrets. Do not surface raw stderr.
        raise RuntimeError(f'{Path(command[0]).name}: fallo ({result.returncode}); no se publicó un resultado válido.')


def connect(socket, database, user):
    return psycopg.connect(host=str(socket), port=5432, dbname=database, user=user,
                           connect_timeout=10, options='-c statement_timeout=300000 -c lock_timeout=5000')


def inventory(conn):
    conn.execute("SET LOCAL TIME ZONE 'UTC'")
    conn.execute("SET LOCAL DateStyle TO 'ISO, YMD'")
    foreign = conn.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('public', 'information_schema') AND nspname NOT LIKE 'pg_%'").fetchall()
    if foreign:
        raise ValueError('La base contiene esquemas ajenos al proyecto.')
    tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
    if not {'core_evidencedocument', 'core_answerrevision', 'core_roleassignment', 'core_task', 'django_migrations'} <= set(tables):
        raise ValueError('No es una base del gestor Salud Modelo con el esquema esperado.')
    if any(not name.startswith(('core_', 'auth_', 'django_')) for name in tables):
        raise ValueError('La base contiene tablas ajenas al esquema del proyecto.')
    result = {}
    for table in tables:
        query = sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text COLLATE "C"').format(sql.Identifier('public', table))
        count, h = 0, hashlib.sha256()
        with conn.cursor(name='recovery_rows') as cursor:
            cursor.execute(query)
            for row in cursor:
                raw = row[0].encode()
                h.update(len(raw).to_bytes(8, 'big'))
                h.update(raw)
                count += 1
        result[table] = {'rows': count, 'sha256': h.hexdigest()}
    return result


def evidence_refs(conn):
    result = {}
    for name, expected in conn.execute('SELECT file, sha256 FROM core_evidencedocument ORDER BY file'):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not name.startswith('evidence/') or str(path) != name or not re.fullmatch('[a-f0-9]{64}', expected):
            raise ValueError('Referencia de adjunto inválida.')
        if name in result and result[name] != expected:
            raise ValueError('Un archivo tiene huellas contradictorias.')
        result[name] = expected
    return result


def copy_evidence(storage, name, expected, destination):
    source = storage / name
    # Reject symlinks in every component and non-regular originals.
    if source.resolve() != source or not source.is_relative_to(storage):
        raise ValueError('Adjunto fuera del almacenamiento privado o enlace simbólico.')
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 10 * 1024 * 1024:
            raise ValueError('Adjunto no regular o superior al límite del gestor.')
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with os.fdopen(fd, 'rb', closefd=False) as src, destination.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        if digest(destination) != expected:
            raise ValueError('El adjunto no coincide con la huella registrada; respaldo cancelado.')
    finally:
        os.close(fd)


def backup(socket, database, user, storage, recipient, output, pg_bin=PG_BIN):
    started = time.monotonic()
    socket = private_dir(socket)
    storage = private_dir(storage)
    if not re.fullmatch(r'salud_[a-zA-Z0-9_]+', database):
        raise ValueError('La base debe identificarse explícitamente con prefijo salud_.')
    if not re.fullmatch(r'age1[0-9a-z]{58}', recipient):
        raise ValueError('Use un destinatario público age nativo X25519.')
    if output.exists():
        raise FileExistsError('El destino ya existe; no se sobrescriben respaldos.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.salud-backup-', dir=output.parent) as tmp:
        stage = Path(tmp)
        plain = stage / 'plain'
        plain.mkdir(mode=0o700)
        with connect(socket, database, user) as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            snapshot = conn.execute('SELECT pg_export_snapshot()').fetchone()[0]
            snapshot_at = utcnow().isoformat()
            tables = inventory(conn)
            refs = evidence_refs(conn)
            run([pg_bin/'pg_dump', '--format=custom', '--no-owner', '--no-acl', '--lock-wait-timeout=5000',
                 '--snapshot='+snapshot, '--file', plain/'database.dump'], env=environment(socket, database, user))
            for name, expected in refs.items():
                copy_evidence(storage, name, expected, plain/'private'/name)
        for filename, target in [('Plan_Trabajo_Escuela_Salud_Modelo.docx', 'plan.docx'), ('Prompt_Maestro_Salud_Modelo_IA (1).md', 'prompt.md')]:
            (plain/'sources').mkdir(exist_ok=True, mode=0o700)
            shutil.copyfile(ROOT/filename, plain/'sources'/target)
        members = {str(p.relative_to(plain)): {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(plain.rglob('*')) if p.is_file()}
        if len(members) > MAX_FILES - 1 or sum(m['bytes'] for m in members.values()) > MAX_BYTES:
            raise ValueError('El paquete supera el límite de ensayo de 1 GiB/100000 archivos.')
        manifest = {'format': 1, 'project': 'salud-modelo', 'snapshot_at': snapshot_at,
                    'files': members, 'tables': tables, 'evidence': refs,
                    'scope': 'Base y originales referenciados; sin secretos, roles globales ni configuración del VPS.',
                    'requirements_sha256': digest(ROOT/'backend/requirements.lock')}
        (plain/'manifest.json').write_bytes(json_bytes(manifest))
        archive = stage/'payload.tar'
        with tarfile.open(archive, 'w') as tar:
            for name in [*members, 'manifest.json']:
                tar.add(plain/name, arcname=name, recursive=False)
        published = stage/'result'
        published.mkdir(mode=0o700)
        encrypted = published/'backup.tar.age'
        run(['age', '--encrypt', '--recipient', recipient, '--output', encrypted, archive])
        receipt = {'format': 1, 'status': 'encrypted_local_only', 'snapshot_at': snapshot_at,
                   'completed_at': utcnow().isoformat(), 'duration_seconds': round(time.monotonic()-started, 3),
                   'encrypted_sha256': digest(encrypted), 'encrypted_bytes': encrypted.stat().st_size,
                   'table_count': len(tables), 'document_count': len(refs),
                   'offsite_verified': False, 'restoration_verified': False}
        (published/'receipt.json').write_bytes(json_bytes(receipt))
        if output.exists():
            raise FileExistsError('El destino se creó durante la operación.')
        published.rename(output)
    return receipt


def unpack_checked(archive, target):
    total, seen = 0, set()
    with tarfile.open(archive, 'r:') as tar:
        for member in tar:
            name = member.name
            p = PurePosixPath(name)
            allowed = name in {'manifest.json', 'database.dump', 'sources/plan.docx', 'sources/prompt.md'} or name.startswith('private/evidence/')
            if not allowed or p.is_absolute() or '..' in p.parts or str(p) != name or not member.isfile() or name in seen:
                raise ValueError('Archivo de respaldo con ruta, tipo o duplicado no permitido.')
            seen.add(name)
            total += member.size
            if total > MAX_BYTES or len(seen) > MAX_FILES or member.size < 0:
                raise ValueError('Archivo de respaldo supera los límites del ensayo.')
            destination = target/name
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tar.extractfile(member) as src, destination.open('xb') as dst:
                shutil.copyfileobj(src, dst)
    manifest = json.loads((target/'manifest.json').read_text())
    if manifest.get('format') != 1 or manifest.get('project') != 'salud-modelo':
        raise ValueError('Manifiesto incompatible.')
    if seen != set(manifest['files']) | {'manifest.json'} or 'database.dump' not in seen:
        raise ValueError('Inventario del respaldo incompleto.')
    for name, meta in manifest['files'].items():
        path = target/name
        if path.stat().st_size != meta['bytes'] or digest(path) != meta['sha256']:
            raise ValueError('Huella del archivo restaurado inconsistente.')
    return manifest


@contextmanager
def isolated_cluster(work, pg_bin=PG_BIN):
    """Only create/start/stop our new cluster; never accept an existing PGDATA."""
    socket, data = work/'socket', work/'pg'
    socket.mkdir(mode=0o700)
    if data.exists():
        raise FileExistsError('No se reutiliza un clúster existente.')
    run([pg_bin/'initdb', '-D', data, '-A', 'trust', '--username=recovery_owner', '--no-locale', '--encoding=UTF8'])
    started = False
    try:
        run([pg_bin/'pg_ctl', '-D', data, '-l', work/'pg.log', '-o', f'-k {socket} -h "" -p 5432', 'start'])
        started = True
        yield socket
    finally:
        if started or (data/'postmaster.pid').exists():
            run([pg_bin/'pg_ctl', '-D', data, 'stop', '-m', 'fast'])


def restore_check(archive, expected_sha256, identity, report_path, pg_bin=PG_BIN, verifier=None):
    started = time.monotonic()
    if report_path.exists():
        raise FileExistsError('El informe ya existe; use otro destino.')
    if not re.fullmatch('[a-f0-9]{64}', expected_sha256) or digest(archive) != expected_sha256:
        raise ValueError('El respaldo no coincide con la huella de procedencia confiable.')
    info = identity.stat()
    if identity.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('La identidad de recuperación debe ser un archivo propio con permisos 0600.')
    # Restrict this tool to a native identity; no SSH files, plugins or interactive passphrases.
    lines = [s.strip() for s in identity.read_text().splitlines() if s.strip() and not s.startswith('#')]
    if len(lines) != 1 or not re.fullmatch(r'AGE-SECRET-KEY-1[0-9A-Z]+', lines[0]):
        raise ValueError('Se requiere una identidad age nativa X25519.')
    if archive.stat().st_size > MAX_BYTES + 64*1024*1024:
        raise ValueError('Respaldo demasiado grande para este ensayo.')
    with tempfile.TemporaryDirectory(prefix='salud-restore-') as tmp:
        work = Path(tmp)
        plain = work/'plain'
        plain.mkdir(mode=0o700)
        payload = work/'payload.tar'
        run(['age', '--decrypt', '--identity', identity, '--output', payload, archive])
        manifest = unpack_checked(payload, plain)
        with isolated_cluster(work, pg_bin) as socket:
            env = environment(socket, 'salud_restore', 'recovery_owner')
            run([pg_bin/'createdb', 'salud_restore'], env=env)
            run([pg_bin/'pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--no-acl',
                 '--dbname=salud_restore', plain/'database.dump'], env=env)
            with connect(socket, 'salud_restore', 'recovery_owner') as conn:
                actual = inventory(conn)
                refs = evidence_refs(conn)
                if actual != manifest['tables'] or refs != manifest['evidence']:
                    raise ValueError('La base restaurada no coincide con tablas, registros o referencias del respaldo.')
            for name, expected in refs.items():
                if digest(plain/'private'/name) != expected:
                    raise ValueError('Un adjunto restaurado no coincide con su registro.')
            # Optional local integration-test callback, not loaded from the archive or CLI.
            if verifier:
                verifier(socket, plain/'private')
        report = {'format': 1, 'status': 'isolated_restore_verified', 'verified_at': utcnow().isoformat(),
                  'snapshot_at': manifest['snapshot_at'], 'encrypted_sha256': expected_sha256,
                  'duration_seconds': round(time.monotonic()-started, 3), 'table_count': len(actual),
                  'row_count': sum(t['rows'] for t in actual.values()), 'document_count': len(refs),
                  'tcp_enabled': False, 'workers_started': False, 'offsite_verified': False,
                  'production_rpo_rto_demonstrated': False,
                  'notice': 'Ensayo local; clúster y copias descifradas retirados. Sin promoción ni reenvío de eventos.'}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('xb') as out:
        out.write(json_bytes(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('backup')
    for name in ['socket', 'storage', 'output']:
        b.add_argument('--'+name, required=True, type=Path)
    for name in ['database', 'user', 'recipient']:
        b.add_argument('--'+name, required=True)
    r = sub.add_parser('restore-check')
    for name in ['archive', 'identity', 'report']:
        r.add_argument('--'+name, required=True, type=Path)
    r.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == 'backup':
            result = backup(args.socket, args.database, args.user, args.storage, args.recipient, args.output)
        else:
            result = restore_check(args.archive, args.expected_sha256, args.identity, args.report)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired, psycopg.Error, tarfile.TarError, KeyError) as error:
        # Avoid leaking DB connection strings, identities or SQL through unexpected errors.
        parser.exit(1, f'Operación cancelada ({type(error).__name__}); no se acredita respaldo o restauración.\n')


if __name__ == '__main__':
    main()
