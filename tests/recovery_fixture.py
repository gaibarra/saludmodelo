"""Synthetic fixture and authorization checks, only in owned recovery clusters."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from rest_framework.test import APIClient
from core.models import Answer, AnswerRevision, EvidenceDocument, OutboxEvent, Task, HelpReview, Institution
from core.tests import WorkflowTests
from core.workflow import save_answer

host = Path(settings.DATABASES['default']['HOST'])
if not host.parent.name.startswith(('salud-recovery-test-', 'salud-restore-')) or host.name != 'socket' or settings.DATABASES['default']['NAME'] not in {'salud_recovery_test', 'salud_restore'}:
    raise RuntimeError('Fixture limitado a clúster de recuperación propio.')

if sys.argv[1] == 'seed':
    fixture = WorkflowTests()
    fixture.setUp()
    answer = save_answer(fixture.author, fixture.answer.pk, 0, 'Información sintética pendiente', 'unknown')
    answer = save_answer(fixture.author, answer.pk, answer.etag, 'Declaración sintética con revisión anterior', 'known')
    client = APIClient()
    client.force_authenticate(fixture.author)
    response = client.post(f'/api/v1/answers/{answer.pk}/evidence/', {'version':answer.etag, 'file':SimpleUploadedFile('synthetic.txt', b'Synthetic recovery evidence\n')}, format='multipart')
    assert response.status_code == 201, response.status_code
    answer.refresh_from_db()
    import uuid
    interview_url=f'/api/v1/interviews/{fixture.instance.pk}/'
    opened=client.post(interview_url,{'action':'open','version':0,'answer_version':answer.etag,'client_key':str(uuid.uuid4())},format='json')
    assert opened.status_code==200
    replied=client.post(interview_url,{'action':'reply','version':opened.data['etag'],'answer_version':answer.etag,'client_key':str(uuid.uuid4()),'item_id':opened.data['items'][0]['id'],'reply':'Synthetic resumed interview','knowledge':'known'},format='json')
    assert replied.status_code==200
    from core.models import MFADevice
    from cryptography.fernet import Fernet
    import pyotp
    MFADevice.objects.create(user=fixture.author,enabled=True,secret=Fernet(settings.MFA_ENCRYPTION_KEY.encode()).encrypt(pyotp.random_base32().encode()).decode())
else:
    U = get_user_model()
    author, other, technical = [U.objects.get(username=name) for name in ('author','other','bootstrap')]
    answer = Answer.objects.get()
    doc = EvidenceDocument.objects.get()
    assert AnswerRevision.objects.count() == 2
    assert HelpReview.objects.filter(decision='approved').count() == 1
    assert Task.objects.count() == 1 and OutboxEvent.objects.filter(delivered_at__isnull=True).count() == 1
    client = APIClient()
    url = f'/api/v1/evidence/{doc.pk}/download/'
    for denied in (other, technical):
        client.force_authenticate(denied)
        assert client.get(url).status_code == 404
        assert client.get(f'/api/v1/answers/{answer.pk}/').status_code == 404
    client.force_authenticate(author)
    response = client.get(url)
    assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'Synthetic recovery evidence\n'
    assert client.get(f'/api/v1/answers/{answer.pk}/').status_code == 200
    from core.models import MFADevice
    from cryptography.fernet import Fernet
    import pyotp
    device=MFADevice.objects.get(user=author)
    secret=Fernet(settings.MFA_ENCRYPTION_KEY.encode()).decrypt(device.secret.encode()).decode()
    real=APIClient()
    assert real.post('/api/v1/session/',{'username':'author','password':'synthetic-only'},format='json').status_code==200
    assert real.get('/api/v1/services/').status_code==403
    assert real.post('/api/v1/mfa/',{'action':'verify','code':pyotp.TOTP(secret).now()},format='json').status_code==200
    assert real.get('/api/v1/services/').status_code==200
    resumed=real.get(f'/api/v1/interviews/{answer.instance_id}/')
    assert resumed.status_code==200 and resumed.data['items'][0]['reply']=='Synthetic resumed interview'
    assert resumed.data['next']==[] and len(resumed.data['history'])==2
    # Verify nextval works after restoration rather than checking row counts alone.
    Institution.objects.create(name='Synthetic post-restore insert')
connection.close()
