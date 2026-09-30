import os
from pathlib import Path
from config.settings import *

work=Path(os.environ['E2E_WORKDIR']).resolve()
if not work.name.startswith('salud-e2e-') or DATABASES['default']['HOST']!=str(work/'socket') or DATABASES['default']['NAME']!='salud_e2e':
    raise RuntimeError('Browser settings are allowed only for the isolated synthetic database.')
REST_FRAMEWORK={**REST_FRAMEWORK,'DEFAULT_THROTTLE_RATES':{'user':'1000/min','anon':'120/min'}}
