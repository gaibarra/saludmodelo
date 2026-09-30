"""Read OOXML as bounded ZIP/XML data inside the document sandbox. No macros."""
import io
import json
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
S='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def extract(raw,kind):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries=archive.infolist();names={entry.filename for entry in entries}
        if len(entries)>1000 or len(names)!=len(entries):raise ValueError('archive_limit')
        if sum(e.file_size for e in entries)>30_000_000:raise ValueError('archive_limit')
        for e in entries:
            if e.flag_bits&1:raise ValueError('encrypted_document')
            if e.file_size>10_000_000 or e.file_size/max(1,e.compress_size)>200:raise ValueError('archive_limit')
            if e.filename.startswith('/') or '..' in e.filename.split('/') or '\\' in e.filename:raise ValueError('invalid_archive')
            if any(x in e.filename.lower() for x in ['vbaproject','embeddings/','activex/']):raise ValueError('active_content')
        def xml(name):
            data=archive.read(name).decode('utf-8-sig')
            if '<!DOCTYPE' in data.upper() or '<!ENTITY' in data.upper():raise ValueError('unsafe_xml')
            return ET.fromstring(data)
        # Reject external relationships; do not retrieve anything from URLs or local paths.
        for name in names:
            if name.endswith('.rels'):
                for rel in xml(name):
                    if rel.get('TargetMode')=='External':raise ValueError('external_reference')
        fragments=[];characters=0
        def add(locator,text,cells=None):
            nonlocal characters
            if not text.strip():return
            characters+=len(text)
            if characters>2_000_000 or len(fragments)>=10_000:raise ValueError('text_limit')
            if len(locator)>120:raise ValueError('locator_limit')
            fragments.append({'ordinal':len(fragments)+1,'locator':locator,'text':text,'cells':cells})
        if kind=='docx':
            if xml('word/document.xml').find(W+'body') is None:raise ValueError('invalid_office')
            parts=['word/document.xml']+sorted(name for name in names if re.fullmatch(r'word/(header[0-9]+|footer[0-9]+|footnotes|endnotes|comments)\.xml',name))
            # XML positions remain explicit; never manufacture physical page numbers.
            for part in parts:
                for number,p in enumerate(xml(part).iter(W+'p'),1):
                    text=''.join(node.text or '' if node.tag==W+'t' else '[Texto eliminado: '+(node.text or '')+']' if node.tag==W+'delText' else '\t' if node.tag==W+'tab' else '\n' if node.tag in {W+'br',W+'cr'} else '' for node in p.iter())
                    add(f'{part} · párrafo {number}',text)
        elif kind=='xlsx':
            workbook=xml('xl/workbook.xml');rels={r.get('Id'):r.get('Target') for r in xml('xl/_rels/workbook.xml.rels')}
            shared=[]
            if 'xl/sharedStrings.xml' in names:
                shared=[''.join(n.text or '' for n in item.iter(S+'t')) for item in xml('xl/sharedStrings.xml')]
            for sheet in workbook.iter(S+'sheet'):
                title=sheet.get('name','');target=rels.get(sheet.get(R+'id'),'')
                path=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join('xl',target))
                if not path.startswith('xl/worksheets/') or path not in names:raise ValueError('invalid_office')
                for cell in xml(path).iter(S+'c'):
                    ref=cell.get('r','')
                    if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}',ref):raise ValueError('invalid_office')
                    formula=cell.find(S+'f');value=cell.findtext(S+'v','');typ=cell.get('t','')
                    if formula is not None:
                        # Preserve formula literally; cached values are not recalculated facts.
                        text='Fórmula sin evaluar: ='+(formula.text or '')
                        if value:text+='\nValor almacenado sin recalcular: '+value
                    elif typ=='s':text=shared[int(value)]
                    elif typ=='inlineStr':text=''.join(n.text or '' for n in cell.iter(S+'t'))
                    else:text=value
                    add(f'Hoja {title} · celda {ref}',text)
        else:raise ValueError('unsupported_format')
        if not fragments:raise ValueError('empty_document')
        return {'fragments':fragments}

if __name__=='__main__':
    try:result=extract(open('/input/document','rb').read(10_000_001),sys.argv[1])
    except (KeyError,IndexError,ET.ParseError,zipfile.BadZipFile):result={'error':'invalid_office'}
    except ValueError as error:result={'error':str(error) if str(error) in {'archive_limit','encrypted_document','invalid_archive','active_content','unsafe_xml','external_reference','text_limit','locator_limit','invalid_office','unsupported_format','empty_document'} else 'invalid_office'}
    print(json.dumps(result,ensure_ascii=True))
