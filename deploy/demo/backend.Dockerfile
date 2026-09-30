FROM python:3.10-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings
WORKDIR /app/backend
COPY backend/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock && useradd --uid 1002 --create-home salud && mkdir /private && chown salud:salud /private
COPY backend/config ./config
COPY backend/core ./core
COPY backend/manage.py ./manage.py
COPY imports /app/imports
COPY Plan_Trabajo_Escuela_Salud_Modelo.docx /app/
COPY deploy/demo/seed.py /app/demo_seed.py
USER salud
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
