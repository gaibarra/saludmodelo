"""Synthetic documents and a private signature fixture. Never production data."""
import hashlib
import io
import shutil
import zipfile
from pathlib import Path
BLOCKED=b'SYNTHETIC BLOCKED DOCUMENT FOR SALUD TEST'

def signatures(folder):
    path=Path(folder);path.mkdir(parents=True,exist_ok=True)
    # Read-only copy of public definitions; never modify ClamAV's own files/services.
    shutil.copyfile('/var/lib/clamav/daily.cld',path/'daily.cld')
    (path/'synthetic.hdb').write_text(f'{hashlib.md5(BLOCKED).hexdigest()}:{len(BLOCKED)}:Salud.Test.Signature\n')
    return str(path)

def office(kind='docx',extra=None):
    out=io.BytesIO()
    files={'[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'}
    if kind=='docx':files['word/document.xml']='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Declaración sintética del documento</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Celda sintética</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
    else:
        files['xl/workbook.xml']='<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Prueba" sheetId="1" r:id="rId1"/></sheets></workbook>'
        files['xl/_rels/workbook.xml.rels']='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml"/></Relationships>'
        files['xl/worksheets/sheet1.xml']='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Dato sintético</t></is></c><c r="B1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>'
    files.update(extra or {})
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,text in files.items():archive.writestr(name,text)
    return out.getvalue()

def pdf(text='Synthetic PDF evidence'):
    stream=f'BT /F1 12 Tf 40 700 Td ({text}) Tj ET'.encode()
    parts=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data=b'%PDF-1.4\n';offsets=[0]
    for i,part in enumerate(parts,1):offsets.append(len(data));data+=f'{i} 0 obj\n'.encode()+part+b'\nendobj\n'
    offset=len(data);data+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{n:010} 00000 n \n'.encode() for n in offsets[1:])
    data+=b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(offset).encode()+b'\n%%EOF\n'
    return data
