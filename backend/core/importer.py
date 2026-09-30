"""Read DOCX as data; never execute document instructions or fetch links."""
import hashlib,re,zipfile,collections
import xml.etree.ElementTree as ET
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
def parse(path):
    raw=path.read_bytes()
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist())>50_000_000: raise ValueError('Documento demasiado grande')
        xml=ET.fromstring(z.read('word/document.xml'))
        rels={e.attrib['Id']:e.attrib['Target'] for e in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
        records=[];section='Portada';section_id='p00001';group='';counts=collections.Counter()
        for i,p in enumerate(xml.iter(W+'p'),1):
            text=''.join(e.text or '' for e in p.iter(W+'t'))
            if not text: continue
            style=p.find(W+'pPr/'+W+'pStyle')
            is_heading=style is not None and style.get(W+'val','').lower().startswith(('heading','ttulo','titulo'))
            if is_heading:
                section=text;section_id=f'p{i:05d}'
            if text=='Preguntas comunes para todas las unidades' or text.startswith(('Unidad de ','Ciencias del deporte y readaptación','Atención y prevención de la salud','Servicios comunitarios laborales y educativos','Vinculación con el despacho jurídico','Recepción administración docencia y recursos')) or (is_heading and re.match(r'C\d{2} ',text)):
                group=text
            numbered=re.match(r'^(\d+)\.\s+¿',text)
            coded=re.match(r'^([A-Z]{2}C\d{2})\s+¿',text)
            kind='text';stable=f'p{i:05d}'
            if numbered:
                kind='question_original';stable=group+'::'+numbered[1]
            elif coded:
                kind='question_compliance';stable=coded[1]
            elif '¿' in text:
                kind='question_additional';stable=section_id+f'::p{i:05d}'
            elif re.fullmatch(r'N\d{2}',text):kind='regulation'
            elif re.fullmatch(r'R\d{2}',text):kind='requirement'
            elif is_heading and re.match(r'C\d{2} ',text):kind='annex'
            elif re.search(r'\b(?:OD|FI|NU|PS|DE|AP|SC|JU|TR)\d{2} ',text):kind='processes'
            links=[rels.get(e.get(R+'id'),'') for e in p.iter(W+'hyperlink')]
            records.append(dict(stable_id=stable,locator=f'word/document.xml paragraph {i}',text=text,section=group+' / '+section,kind=kind,links=links))
            counts[kind]+=1
        report={'sha256':hashlib.sha256(raw).hexdigest(),'counts':dict(counts),'question_sections':dict(collections.Counter(r['section'] for r in records if r['kind'].startswith('question'))),'expected_original':120,'expected_compliance':54,'original_matches':counts['question_original']==120,'compliance_matches':counts['question_compliance']==54,'help_reviewed':0,'notes':['Preguntas compuestas conservadas como un registro original.','Preguntas adicionales y de cierre preservadas sin inventar códigos.','C27 aparece en dos encabezados: ambos se conservan.','Vigencia normativa por verificar; importar no demuestra cumplimiento.']}
        return records,report
