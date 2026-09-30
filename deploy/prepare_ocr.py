"""Recreate the private OCR runtime from pinned Debian packages; never install globally."""
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
root=ROOT/'backend/vendor/ocr'
packages=root/'packages';runtime=root/'runtime'
packages.mkdir(parents=True,exist_ok=True);runtime.mkdir(parents=True,exist_ok=True)
for entry in json.loads((root/'manifest.json').read_text()):
    target=packages/entry['file']
    if not target.exists():
        subprocess.run(['apt-get','download',entry['package']+'='+entry['version']],cwd=packages,check=True)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Package hash mismatch: '+entry['file'])
    subprocess.run(['dpkg-deb','-x',str(target),str(runtime)],check=True)
print('Private OCR runtime:',runtime)
