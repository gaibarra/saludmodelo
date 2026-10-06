import os
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ['DJANGO_SECRET_KEY']
DEBUG=os.getenv('DEBUG','0')=='1'
ALLOWED_HOSTS=os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','rest_framework','drf_spectacular','core']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware']
ROOT_URLCONF='config.urls'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('PGDATABASE','salud_modelo'),'USER':os.getenv('PGUSER','salud_modelo'),'PASSWORD':os.getenv('PGPASSWORD',''),'HOST':os.getenv('PGHOST','127.0.0.1'),'PORT':os.getenv('PGPORT','5432')}}
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
USE_TZ=True
TIME_ZONE='America/Merida'
LANGUAGE_CODE='es-mx'
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SESSION_COOKIE_SAMESITE='Lax'
CSRF_TRUSTED_ORIGINS=os.getenv('CSRF_TRUSTED_ORIGINS','http://localhost:3000').split(',')
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY='same-origin'
MEDIA_ROOT=Path(os.getenv('PRIVATE_STORAGE',str(BASE_DIR/'private')))
FILE_UPLOAD_PERMISSIONS=0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o700
FILE_UPLOAD_MAX_MEMORY_SIZE=1024*1024
DATA_UPLOAD_MAX_MEMORY_SIZE=12*1024*1024
REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['core.authentication.MFASessionAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'],'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema','DEFAULT_PAGINATION_CLASS':'rest_framework.pagination.PageNumberPagination','PAGE_SIZE':50,'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.UserRateThrottle'],'DEFAULT_THROTTLE_RATES':{'user':'120/min','anon':'10/min'}}
SPECTACULAR_SETTINGS={'TITLE':'Salud Modelo','VERSION':'0.35.0','ENUM_NAME_OVERRIDES':{'AIActionEnum':['suggest','explain','interview','extract','review','contradictions','report'],'AIProviderEnum':['openai','deepseek'],'ComplianceDecisionEnum':['approved','returned'],'PatientSitePreferenceEnum':['casita','cholul','indistinta']}}

DATABASES['default']['TEST']={'CHARSET':'UTF8','TEMPLATE':'template0'}

# Gunicorn must remain on loopback behind the trusted reverse proxy.
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')

AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}}, {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]

# Binary documents fail closed until a dedicated, current signature bundle is configured.
DOCUMENT_SIGNATURES=os.getenv('DOCUMENT_SIGNATURES','')
DOCUMENT_SCAN_CERTIFICATES=os.getenv('DOCUMENT_SCAN_CERTIFICATES','/etc/clamav/certs')
DOCUMENT_OCR_RUNTIME=os.getenv('DOCUMENT_OCR_RUNTIME','')

# Explicit deployment and institutional policy are both required for outbound AI.
import json
AI_EXTERNAL_ENABLED=os.getenv('AI_EXTERNAL_ENABLED','0')=='1'
AI_MODELS=json.loads(os.getenv('AI_MODELS_JSON','{}'))
AI_KEYS={'openai':os.getenv('OPENAI_API_KEY',''),'deepseek':os.getenv('DEEPSEEK_API_KEY','')}

# Independent Fernet key; never derive MFA encryption from the Django session key.
MFA_ENCRYPTION_KEY=os.getenv('MFA_ENCRYPTION_KEY','')
MFA_REQUIRE_PRIVILEGED=os.getenv('MFA_REQUIRE_PRIVILEGED','1')=='1'

# Requires an institutionally approved identity-verification and secure-delivery procedure.
EXCEPTIONAL_MFA_RECOVERY_ENABLED=os.getenv('EXCEPTIONAL_MFA_RECOVERY_ENABLED','0')=='1'

# Patient registration and appointments require explicit institutional activation.
PATIENT_PORTAL_ENABLED=os.getenv('PATIENT_PORTAL_ENABLED','0')=='1'

# Temporary, explicit demonstration mode; never active with patient intake.
MFA_DEMO_PASSWORD_ONLY=os.getenv('MFA_DEMO_PASSWORD_ONLY','0')=='1'

# Explicitly authorized persistent-registration pilot; reversible, off by default.
MFA_PASSWORD_ONLY_PILOT=os.getenv('MFA_PASSWORD_ONLY_PILOT','0')=='1'
