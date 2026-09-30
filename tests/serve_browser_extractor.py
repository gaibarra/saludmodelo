"""Extraction worker used only inside the owned browser-test database."""
import os
import time
from pathlib import Path
import django
django.setup()
from django.conf import settings
from core.documents import process_one
sandbox=Path(os.environ['E2E_WORKDIR']).resolve()
if not sandbox.name.startswith('salud-e2e-') or settings.DATABASES['default']['HOST']!=str(sandbox/'socket') or settings.DATABASES['default']['NAME']!='salud_e2e':
    raise RuntimeError('Browser extractor disabled outside isolated test database')
while True:
    if not process_one():time.sleep(.2)
