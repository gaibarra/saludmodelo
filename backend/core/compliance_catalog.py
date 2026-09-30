"""Preserve literal normative table rows; import never verifies law or applicability."""
import re,zipfile,hashlib
import xml.etree.ElementTree as ET
from .models import NormativeEntry
from .importer import W,R

def table_entries(path):
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read('word/document.xml'))
        rels={e.attrib['Id']:e.attrib['Target'] for e in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
        rows=[]
        for row in root.iter(W+'tr'):
            cells=['\n'.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in cell.iter(W+'p')) for cell in row.findall(W+'tc')]
            if len(cells)==4 and re.fullmatch(r'N\d{2}',cells[0]):
                rows.append({'code':cells[0],'title':cells[1],'subject':cells[2],'scope_text':cells[3],'links':[rels[e.get(R+'id')] for e in row.iter(W+'hyperlink') if e.get(R+'id') in rels]})
        return rows

def enrich(batch,path):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=batch.digest:raise ValueError('Fuente distinta al lote.')
    for row in table_entries(path):
        source=batch.sourcerecord_set.get(kind='regulation',text=row['code'])
        NormativeEntry.objects.get_or_create(source=source,defaults=row)
