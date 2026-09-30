"""Build a source-checked offline review pack. No DB, network or approvals."""
import argparse
import collections
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from core.importer import parse

DOCX = 'Plan_Trabajo_Escuela_Salud_Modelo.docx'
PROMPT = 'Prompt_Maestro_Salud_Modelo_IA (1).md'
SOURCE_SHA = '72108682be8b63f71c15d70d8d43fa370a033f04fd8af4526b4acf10b0e236be'
PROMPT_SHA = '5d24b46114443a9654e19fc8e679d3449efd13bbd73e6c7fc84f47986d421926'
FIELDS = {
    'plain_explanation': 'Qué significa', 'purpose': 'Para qué se pregunta',
    'knower': 'Quién conoce la respuesta', 'where_to_find': 'Dónde buscar',
    'steps': 'Cómo responder', 'fictional_example': 'Ejemplo ficticio',
    'evidence': 'Evidencia y alternativas', 'sufficiency': 'Suficiencia y errores',
    'applicability': 'Aplicabilidad', 'escalation': 'Consulta y escalamiento',
}
# These are proposed review topics, not institutionally approved rules.
RULES = [
    ('Alcance y sedes', 'Confirmar oferta real, exclusiones, sedes y vinculación jurídica; justificar selecciones por servicio.', '1 Fuentes y alcance', 'C03–C11'),
    ('Responsables y separación de funciones', 'Confirmar nombramientos, competencias, suplencias, vigencias y aprobador distinto del autor.', '3 Roles y permisos', 'C27'),
    ('Fichas y suficiencia', 'Adaptar diez apartados, alternativas de evidencia y condiciones de aplicabilidad por servicio.', '4 Experiencia de formularios sin ambigüedad', 'C27'),
    ('Evidencia y privacidad', 'Confirmar clasificación, acceso, vigencia, retención y cotejo de documentos; usar casos anonimizados.', '6 Automatización de documentos y respuestas', 'C13,C15,C16'),
    ('Revisión y cambios', 'Confirmar competencias para revisar, devolver y aceptar; conservar historial e invalidar decisiones afectadas.', '7 Flujo de trabajo y decisiones', 'C18,C27'),
    ('Aplicabilidad normativa', 'Asignar revisión competente de numeral, versión, fuente oficial y supuestos reales. Una norma listada no implica aplicación.', '8 Compliance integrado', 'C01–C20'),
    ('Uso de IA', 'Decidir proveedores, política de salida, autorizaciones, cuotas y corpus de evaluación antes de habilitar llamadas.', '9 Integración OpenAI y DeepSeek', 'C25,C27'),
    ('Capacidad e indicadores', 'Confirmar denominadores, criterios de aceptación y distribución de 295 h base más 59 h de reserva, aún provisionales.', '10 Dashboard y métricas comprobables', 'C21–C26'),
    ('Calendario y avisos', 'Confirmar días laborables, ausencias, suplentes, coordinadores y avisos internos a dos/tres días hábiles.', '11 Automatizaciones de seguimiento', 'C22,C26'),
    ('Seguridad y recuperación', 'Acordar responsables, MFA, retención, respaldos, restauración y criterios operativos antes de producción.', '14 Seguridad y despliegue en VPS', 'C15,C18'),
    ('Usabilidad y aceptación', 'Observar un caso normal y dos excepciones con directivos de cada servicio; corregir dudas y repetir.', '16 Pruebas y criterios de aceptación', 'C18,C27'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8') + b'\n'


def checked_sources(root):
    if sha((root / DOCX).read_bytes()) != SOURCE_SHA or sha((root / PROMPT).read_bytes()) != PROMPT_SHA:
        raise ValueError('Las fuentes cambiaron: requiere conciliación explícita de versión.')
    records, report = parse(root / DOCX)
    if records != json.loads((root / 'imports/source-inventory.json').read_text()):
        raise ValueError('El inventario no coincide literalmente con el DOCX.')
    by_id = {r['stable_id']: r for r in records}
    if len(by_id) != len(records):
        raise ValueError('Identificadores duplicados en el inventario.')
    drafts = json.loads((root / 'imports/help-drafts-v1.json').read_text())
    questions = [r for r in records if r['kind'].startswith('question_')]
    counts = collections.Counter(q['kind'] for q in questions)
    if counts != {'question_original': 120, 'question_compliance': 54, 'question_additional': 3}:
        raise ValueError('La conciliación 120 + 54 + 3 no coincide.')
    if drafts['source_sha256'] != SOURCE_SHA or set(drafts['questions']) != {q['stable_id'] for q in questions}:
        raise ValueError('El catálogo de fichas no coincide con las 177 preguntas fuente.')
    if drafts['status'] != 'draft_requires_human_review':
        raise ValueError('Se esperaba un catálogo editorial en borrador.')
    result = []
    for q in questions:
        entry = drafts['questions'][q['stable_id']]
        if entry['question_text'] != q['text'] or entry['question_sha256'] != sha(q['text'].encode()):
            raise ValueError('Texto o huella de pregunta inconsistente: ' + q['stable_id'])
        if set(entry['content']) != set(FIELDS) or any(not isinstance(v, str) or not v.strip() for v in entry['content'].values()):
            raise ValueError('Ficha incompleta: ' + q['stable_id'])
        refs = []
        for ref in entry['references']:
            source = by_id.get(ref['stable_id'])
            if source is None or source['locator'] != ref['locator'] or sha(source['text'].encode()) != ref['text_sha256']:
                raise ValueError('Referencia inconsistente: ' + q['stable_id'])
            refs.append(source)
        if q['stable_id'] not in {r['stable_id'] for r in refs}:
            raise ValueError('La ficha debe citar su propia pregunta.')
        result.append({**q, 'content': entry['content'], 'references': refs,
                       'draft_sha256': sha(encoded(entry)), 'status': 'pendiente_revision_institucional'})
    return records, result, drafts['version']


def csv_bytes(headers, rows):
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    # Neutralize spreadsheet formula prefixes, including after leading whitespace.
    def cell(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
    writer.writerow(headers)
    writer.writerows([[cell(v) for v in row] for row in rows])
    return out.getvalue().encode('utf-8-sig')


def render_html(questions, version):
    e = html.escape
    groups = collections.defaultdict(list)
    for index, q in enumerate(questions, 1):
        groups[q['section']].append((index, q))
    nav = ''.join(f'<li><a href="#grupo-{n}">{e(section)} ({len(items)})</a></li>' for n, (section, items) in enumerate(groups.items(), 1))
    sections = []
    for n, (section, items) in enumerate(groups.items(), 1):
        cards = []
        for index, q in items:
            fields = ''.join(f'<h4>{e(label)}</h4><p>{e(q["content"][key])}</p>' for key, label in FIELDS.items())
            refs = ''.join(f'<li><strong>{e(r["locator"])}</strong><p>{e(r["text"])}</p></li>' for r in q['references'])
            cards.append(f'<article id="ficha-{index}"><h3>{index}. {e(q["stable_id"])}</h3><p class="status">Borrador · pendiente de revisión institucional</p><blockquote>{e(q["text"])}</blockquote><p>{e(q["locator"])}</p>{fields}<details><summary>Referencias literales</summary><ul>{refs}</ul></details><p class="hash">Huella de ficha: {q["draft_sha256"]}</p><a href="#indice">Volver al índice</a></article>')
        sections.append(f'<section id="grupo-{n}"><h2>{e(section)}</h2>{"".join(cards)}</section>')
    return ('''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Salud Modelo · 177 fichas para revisión</title><style>body{font:18px/1.6 system-ui,sans-serif;color:#172d39;background:#f5f7f8;max-width:960px;margin:2rem auto;padding:0 1rem}article{background:white;border:1px solid #bccbd2;border-radius:8px;padding:1.5rem;margin:1.5rem 0}h1,h2,h3{line-height:1.25;overflow-wrap:anywhere}h4{margin-bottom:0}p,blockquote{white-space:pre-wrap}a{color:#075882}.status{font-weight:bold;color:#704700}.hash{overflow-wrap:anywhere;font-size:14px}summary{cursor:pointer}article{scroll-margin-top:1rem}@media print{body{max-width:none;background:white;font-size:11pt}nav{display:none}article{break-before:page;border:none}a{color:inherit}details{display:block}}</style><main><h1>177 fichas para revisión institucional</h1><p>120 preguntas originales + 54 de cumplimiento + 3 párrafos compuestos. Este catálogo editorial no consulta el estado del sistema: no acredita ninguna aprobación. Los ejemplos son ficticios.</p><p>Use el índice o la búsqueda del navegador (Ctrl+F). Abra las referencias para cotejarlas. Registre observaciones en revision_fichas.csv; duplique cada fila para cada servicio y sede que deba revisarla. Los archivos no guardan cambios en el gestor.</p>'''
            + f'<p>Catálogo: {e(version)} · DOCX v3.1 · SHA-256: <span class="hash">{SOURCE_SHA}</span></p>'
            + '<nav id="indice" aria-label="Secciones"><h2>Índice</h2><ul>' + nav + '</ul></nav>'
            + ''.join(sections) + '</main></html>').encode()


def build(root, output):
    if output.exists():
        raise FileExistsError('El destino ya existe; use una carpeta nueva para preservar anotaciones e historial.')
    records, questions, version = checked_sources(root)
    prompt = (root / PROMPT).read_text()
    units = [r for r in records if r['kind'] == 'processes']
    if len(units) != 9:
        raise ValueError('Se esperaban nueve referencias de procesos por unidad.')
    prepared = datetime.now(timezone.utc)
    files = {}
    files['fichas.html'] = render_html(questions, version)
    files['fichas.json'] = encoded({'catalog_version': version, 'source_sha256': SOURCE_SHA,
                                   'scope': 'catalogo_editorial_sin_datos_del_gestor', 'questions': questions})
    headers = ['pregunta_id', 'seccion_fuente', 'localizador', 'huella_ficha', 'institucion', 'campus', 'sede', 'servicio', 'seleccion_propuesta', 'fundamento_alcance', 'autor_adaptacion', 'revisor_competente', 'observaciones', 'cambios_por_apartado', 'evidencia_suficiente', 'fecha_revision', 'version_guardada_gestor', 'decision_en_gestor', 'estado_paquete']
    files['revision_fichas.csv'] = csv_bytes(headers, [[q['stable_id'], q['section'], q['locator'], q['draft_sha256']] + [''] * 14 + ['pendiente'] for q in questions])
    files['servicios.csv'] = csv_bytes(['unidad_referida_en_plan', 'localizador', 'procesos_literales', 'institucion', 'campus', 'sede', 'servicio_real', 'oferta_y_exclusiones', 'poblacion', 'decision_inclusion', 'fundamento', 'responsable_confirmacion', 'fecha', 'estado'], [[r['section'], r['locator'], r['text']] + [''] * 10 + ['pendiente'] for r in units])
    files['responsables.csv'] = csv_bytes(['institucion', 'campus', 'sede', 'servicio', 'persona', 'funcion', 'competencia_acreditada', 'rol_gestor', 'inicio', 'fin', 'suplente', 'inicio_suplencia', 'fin_suplencia', 'aprobador_distinto', 'fundamento_nombramiento', 'registro_gestor', 'estado'], [[''] * 16 + ['pendiente']])
    rules = []
    for topic, decision, heading, annex in RULES:
        marker = '## ' + heading + '\n'
        if marker not in prompt:
            raise ValueError('Sección del prompt ausente: ' + heading)
        literal = prompt.split(marker, 1)[1].split('\n## ', 1)[0].strip()
        rules.append({'tema': topic, 'decision_por_confirmar': decision, 'referencia_prompt': heading,
                      'texto_prompt': literal, 'anexos_orientativos': annex, 'estado': 'pendiente'})
    files['reglas_fuente.json'] = encoded({'prompt_sha256': PROMPT_SHA, 'rules': rules})
    files['reglas.csv'] = csv_bytes(['tema', 'decision_por_confirmar', 'referencia_prompt', 'anexos_orientativos', 'alcance', 'propuesta_institucional', 'autor', 'revisor_competente', 'fundamento', 'evidencia_o_acta', 'fecha', 'version', 'estado'], [[r['tema'], r['decision_por_confirmar'], r['referencia_prompt'], r['anexos_orientativos']] + [''] * 8 + ['pendiente'] for r in rules])
    files['usabilidad.csv'] = csv_bytes(['unidad_referida_en_plan', 'campus', 'sede', 'servicio', 'participante_por_funcion', 'observador', 'tipo_caso', 'descripcion_anonimizada', 'preguntas_y_versiones', 'resultado_esperado_acordado', 'resultado_observado', 'dudas_persistentes', 'correccion_propuesta', 'repeticion_y_resultado', 'fecha', 'decision_competente', 'estado'], [[r['section']] + [''] * 5 + [case] + [''] * 9 + ['pendiente'] for r in units for case in ('normal', 'excepcion_1', 'excepcion_2')])
    files['acta_modelo.md'] = (root / 'docs/validacion/ACTA_MODELO.md').read_bytes()
    files['LEEME.md'] = (root / 'docs/validacion/GUIA.md').read_bytes()
    files['manifest.json'] = encoded({
        'format_version': 1, 'status': 'preparacion_sin_aprobaciones',
        'author': 'Generador técnico Salud Modelo; sin firma institucional',
        'prepared_at': prepared.isoformat(), 'scope': 'Fuentes editoriales; sin consulta de datos institucionales',
        'catalog_version': version, 'counts': {'original': 120, 'compliance': 54, 'compound': 3, 'total': 177, 'unit_references': 9, 'usability_template_cases': 27},
        'sources': {DOCX: SOURCE_SHA, PROMPT: PROMPT_SHA, 'imports/help-drafts-v1.json': sha((root / 'imports/help-drafts-v1.json').read_bytes())},
        'files': {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in files.items()},
        'notice': 'Las huellas permiten cotejar integridad, no acreditan firma, identidad, aprobación ni estado actual del gestor.',
    })
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.revision-', dir=output.parent))
    try:
        for name, raw in files.items():
            (stage / name).write_bytes(raw)
        with zipfile.ZipFile(stage / 'paquete_revision.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in files.items():
                info = zipfile.ZipInfo(name, date_time=prepared.timetuple()[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, raw)
        # Recheck rather than knowingly overwrite any existing review folder.
        if output.exists():
            raise FileExistsError('El destino se creó durante la generación; no se reemplaza.')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return len(questions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Carpeta nueva; nunca reemplaza revisiones previas.')
    args = parser.parse_args()
    try:
        count = build(ROOT, args.output.resolve())
    except (ValueError, FileExistsError) as error:
        parser.exit(1, str(error) + '\n')
    print(f'Paquete preparado: {count} fichas en borrador. Sin aprobaciones ni cambios al gestor. {args.output}')
