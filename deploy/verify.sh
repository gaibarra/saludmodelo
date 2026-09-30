#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
backend/.venv/bin/python backend/manage.py check
backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
backend/.venv/bin/python backend/manage.py test core --noinput
(cd frontend && npm run build)
