"""Run backend checks in a private, disposable PostgreSQL cluster with no TCP port.

Usage: python3 tests/run_backend.py [Django test labels...]
Defaults to the complete core suite. Existing databases and services are never used.
"""
import os
import getpass
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG_BIN = Path(os.environ.get('TEST_PG_BIN', '/usr/lib/postgresql/16/bin'))
PYTHON = ROOT / 'backend/.venv/bin/python'


def main():
    with tempfile.TemporaryDirectory(prefix='salud-backend-') as folder:
        work = Path(folder)
        (work / 'socket').mkdir(mode=0o700)
        env = {
            **{key: value for key, value in os.environ.items() if not key.startswith('PG')},
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(48),
            'PGHOST': str(work / 'socket'),
            'PGPORT': '5432',
            'PGDATABASE': 'salud_backend_checks',
            'PGUSER': getpass.getuser(),
            'PGPASSWORD': '',
            'AI_EXTERNAL_ENABLED': '0',
            'AI_MODELS_JSON': '{}',
            'OPENAI_API_KEY': '',
            'DEEPSEEK_API_KEY': '',
            'PRIVATE_STORAGE': str(work / 'private'),
            'MFA_REQUIRE_PRIVILEGED': '0',
        }
        started = False
        try:
            subprocess.run([str(PG_BIN / 'initdb'), '-D', str(work / 'pg'), '-A', 'trust', '--no-locale', '--encoding=UTF8'], check=True, stdout=subprocess.DEVNULL)
            subprocess.run([str(PG_BIN / 'pg_ctl'), '-D', str(work / 'pg'), '-l', str(work / 'postgres.log'), '-o', f'-k {work}/socket -h ""', 'start'], check=True, stdout=subprocess.DEVNULL)
            started = True
            subprocess.run([str(PG_BIN / 'createdb'), env['PGDATABASE']], env=env, check=True)
            checks = [
                ['check'],
                ['makemigrations', '--check', '--dry-run'],
                ['test', *(sys.argv[1:] or ['core']), '--noinput'],
                ['spectacular', '--file', str(work / 'openapi.yaml'), '--validate', '--fail-on-warn'],
            ]
            for command in checks:
                subprocess.run([str(PYTHON), 'backend/manage.py', *command], cwd=ROOT, env=env, check=True)
        finally:
            if started:
                subprocess.run([str(PG_BIN / 'pg_ctl'), '-D', str(work / 'pg'), 'stop', '-m', 'fast'], check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
