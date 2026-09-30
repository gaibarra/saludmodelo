"""Compile authored question-specific draft guidance. No network calls or approvals."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
rows=json.loads((ROOT/'imports/source-inventory.json').read_text())
by_id={r['stable_id']:r for r in rows}
# Source evidence paragraphs are proposals in the plan, not facts about the institution.
contexts=[
 ('Preguntas comunes para todas las unidades','p00610','responsable del servicio, recepción y enlace administrativo'),
 ('Unidad de odontología','p00072','coordinación odontológica, docente supervisor y recepción'),
 ('Unidad de fisioterapia','p00094','coordinación de fisioterapia, terapeutas y supervisores'),
 ('Unidad de nutrición','p00116','responsable de nutrición de la sede y Finanzas cuando corresponda'),
 ('Unidad de psicología clínica','p00138','coordinación de psicología y responsable de privacidad'),
 ('Ciencias del deporte y readaptación','p00160','coordinación del laboratorio, profesional competente y encargado de equipos'),
 ('Atención y prevención de la salud','p00182','coordinación de UAPS y responsable clínico o de referencia'),
 ('Servicios comunitarios laborales y educativos','p00204','coordinación comunitaria, vinculación y responsable de cada convenio'),
 ('Vinculación con el despacho jurídico','p00226','responsable jurídico y encargado de custodia documental'),
 ('Recepción administración docencia y recursos','p00248','enlace del área administrativa, Finanzas, coordinación académica o recursos según el caso'),
 ('ODC','p00701','coordinación odontológica y responsable sanitario'),
 ('FIC','p00719','coordinación de fisioterapia y responsable clínico'),
 ('NUC','p00737','coordinación de nutrición y responsable de la actividad confirmada'),
 ('PSC','p00755','coordinación de psicología y responsable de privacidad o jurídico'),
 ('DEC','p00773','coordinación deportiva y profesional competente para la prueba'),
 ('UAC','p00791','coordinación UAPS y responsable sanitario'),
 ('COC','p00809','coordinación comunitaria, vinculación y responsable del convenio'),
 ('JUC','p00826','responsable jurídico con competencia en el asunto'),
 ('ADC','p00845','Dirección y enlace administrativo, académico o de recursos competente'),
 ('p00885::p00887','p00886','seguridad, mantenimiento y responsable del servicio'),
 ('p00898::p00900','p00899','responsable sanitario y encargado del seguimiento de incidentes'),
 ('p00930::p00931','p00938','responsable de privacidad, Jurídico y TI dentro de sus funciones'),
]
context={key:(by_id[ref],role) for key,ref,role in contexts}
groups={};group=None
for line in (ROOT/'imports/editorial/topics.txt').read_text().splitlines():
 if not line.strip():continue
 if line.startswith('['):group=line[1:-1];groups[group]=[]
 else:
  parts=line.split('|')
  assert len(parts)==3,line
  groups[group].append(parts)
entries={}
for group,items in groups.items():
 evidence,role=context[group]
 for i,(topic,fields,example) in enumerate(items,1):
  key=group if group.startswith('p0') else f'{group}{i:02}' if len(group)==3 else f'{group}::{i}'
  source=by_id[key];assert source['kind'].startswith('question'),key
  steps='\n'.join(f'{n}. Indique {field.strip()}.' for n,field in enumerate(fields.split(';'),1))
  applicability='Confirme la modalidad y sede donde ocurre esta actividad. Una pregunta no demuestra que el servicio exista ni que una norma aplique. Si considera que no aplica, documente el motivo y solicite revisión competente.'
  if group in ['Vinculación con el despacho jurídico','JUC']:applicability='Dirección debe confirmar la inclusión del servicio jurídico. No presuponga representación, jurisdicción ni plazos. Documente el supuesto y solicite revisión jurídica antes de convertirlo en regla.'
  content={
   'plain_explanation':f'Necesitamos conocer {topic}. Describa la operación observada de su servicio; separe los cambios que propone.',
   'purpose':f'Sirve para acordar qué datos, responsables y decisiones debe registrar o comprobar el sistema respecto de {topic}.',
   'knower':f'Consulte por función a {role}. Confirme quién ejerce esas funciones en su sede; el plan no acredita un nombramiento individual.',
   'where_to_find':'El plan propone solicitar los siguientes materiales (seleccione los pertinentes a esta pregunta):\n'+evidence['text'],
   'steps':steps+'\nDespués, describa una excepción relevante e indique dónde se registra la decisión. Si falta un dato, use No lo sé, No existe actualmente o Está por confirmar; no complete por suposición.',
   'fictional_example':'Ejemplo ficticio, no es información institucional confirmada: '+example,
   'evidence':'Vincule el formato vacío, procedimiento, registro anonimizado o declaración documentada que permita comprobar los campos de esta pregunta. El párrafo de materiales del plan es una propuesta de búsqueda, no una lista automática de archivos obligatorios. El validador confirma qué alternativa es suficiente y si necesita verificación en sitio.',
   'sufficiency':f'La revisión debe poder identificar {fields.replace(";", ",")}, el responsable de la información y los puntos todavía pendientes. Evite mezclar una propuesta con la operación observada, omitir la excepción o presentar un documento desactualizado como vigente. Una respuesta breve puede ser suficiente; no se evalúa por extensión.',
   'applicability':applicability,
   'escalation':f'Si persiste la duda, abra las consultas privadas y seleccione una persona autorizada del servicio. Lleve la pregunta, lo que sabe y la discrepancia concreta a {role}. Si dos fuentes difieren, conserve ambas versiones para revisión humana. La consulta del gestor no atiende una urgencia clínica.',
  }
  refs=[source,evidence]
  entries[key]={'question_text':source['text'],'question_sha256':hashlib.sha256(source['text'].encode()).hexdigest(),'content':content,'references':[{'stable_id':r['stable_id'],'locator':r['locator'],'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest()} for r in refs]}
questions=[r for r in rows if r['kind'].startswith('question')]
assert {r['stable_id'] for r in questions}==set(entries),'Coverage mismatch'
assert len(entries)==177
raw=(ROOT/'Plan_Trabajo_Escuela_Salud_Modelo.docx').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='72108682be8b63f71c15d70d8d43fa370a033f04fd8af4526b4acf10b0e236be', 'Source changed: re-import and review editorial mappings before generating proposals'
catalog={'version':'editorial-1','status':'draft_requires_human_review','method':'question_specific_editorial_drafts','source_sha256':hashlib.sha256(raw).hexdigest(),'questions':entries}
(ROOT/'imports/help-drafts-v1.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
report={'drafts':len(entries),'original':120,'compliance':54,'additional_paragraphs':3,'complete_fields_per_draft':10,'institutionally_reviewed':0,'institutionally_published':0,'source_sha256':catalog['source_sha256'],'notes':['Cobertura de propuestas, no de ayudas institucionalmente aprobadas.','Redacción editorial específica; sin llamadas a OpenAI o DeepSeek.','La propuesta sólo se ofrece si coincide texto y hash de fuente importada.']}
(ROOT/'imports/help-drafts-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
