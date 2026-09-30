# Salud Modelo — incremento 0.31

Implementación inicial del gestor basada en `Prompt_Maestro_Salud_Modelo_IA (1).md` y `Plan_Trabajo_Escuela_Salud_Modelo.docx` v3.1. **Es una entrega parcial en desarrollo; no es el sistema clínico terminado ni está desplegada.**

Incluye Next.js/TypeScript/Tailwind, API Django/DRF, migraciones PostgreSQL, importador trazable, sesiones con CSRF, permisos vigentes por servicio, respuestas/revisiones, control de concurrencia, declaraciones privadas TXT/CSV, revisión por otra persona, indicador inicial, pendientes y outbox interno. La entrega 0.2 añade administración de campus/sedes/servicios, usuarios y nombramientos, selección de preguntas, ayudas versionadas por servicio, revisión y publicación desde la interfaz.

## Ejecutar localmente

Requiere Python compatible con Django 5.2, Node compatible con Next.js 16 y PostgreSQL. Crear base y usuario propios de desarrollo; no usar bases existentes de otros proyectos.

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.lock
cd frontend
npm ci
cd ..
cp .env.example .env
# Editar .env: clave única, PostgreSQL propio, DEBUG=1,
# ALLOWED_HOSTS=localhost,127.0.0.1 y CSRF_TRUSTED_ORIGINS=http://localhost:3000
set -a
source .env
set +a
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py createsuperuser
backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
# Otra terminal con el mismo entorno:
cd frontend
npm run dev
```

Abrir http://localhost:3000. La cuenta técnica no recibe automáticamente asignaciones de servicio. No se precargan usuarios o datos institucionales. La ruta `/administracion` permite configurar servicios y nombramientos, seleccionar preguntas, preparar ayudas y publicarlas después de revisión. Primero registre el mandato inicial de Dirección con el procedimiento siguiente. No reinicie ni reutilice aplicaciones existentes del VPS 194.113.64.91; los puertos de ejemplo son sólo para un entorno propio, previamente comprobado.

## Importar la fuente

```bash
backend/.venv/bin/python backend/manage.py import_plan 'Plan_Trabajo_Escuela_Salud_Modelo.docx' > imports/preview.json
# Revisar conteos, diferencias y SHA256. Confirmar el hash exacto y actor autorizado:
backend/.venv/bin/python backend/manage.py import_plan 'Plan_Trabajo_Escuela_Salud_Modelo.docx' --approve-sha HASH_REVISADO --actor USUARIO_AUTORIZADO
```

La importación guarda inventario y versiones en PostgreSQL sin sobrescribir respuestas. No publica preguntas ni aprueba ayudas. La vista previa necesita conexión a PostgreSQL para comparar contra el último lote.

Conciliación: 120 preguntas originales, 54 de cumplimiento y tres párrafos adicionales con preguntas compuestas; N01–N60 y R01–R12 conservados. Los encabezados C19, C20 y C27 se repiten en la fuente y se preservan. Ver `imports/preview.json` y `imports/source-inventory.json`.

## Alta inicial y autorización del inventario

Después de importar y revisar la fuente, un operador técnico autorizado registra el nombramiento institucional real. El comando exige un usuario de Dirección distinto del aprobador y un periodo explícito. Si la cuenta de Dirección no existe, solicita su contraseña de forma interactiva; no admite contraseñas en argumentos.

```bash
backend/.venv/bin/python backend/manage.py bootstrap_institution \
  --institution-name 'NOMBRE_INSTITUCIONAL_CONFIRMADO' \
  --director USUARIO_DIRECCION \
  --approver USUARIO_TECNICO \
  --starts FECHA_INICIO_YYYY-MM-DD --ends FECHA_FIN_YYYY-MM-DD \
  --rationale 'FUNDAMENTO_DEL_NOMBRAMIENTO_CONFIRMADO' \
  --catalog-batch ID_DEL_LOTE_IMPORTADO
```

Para una institución existente use `--institution ID` en lugar de `--institution-name`. El permiso de catálogo sólo habilita la fuente indicada. La cuenta técnica no recibe acceso a respuestas por ser superusuario. El mandato institucional permite configurar organización, usuarios y nombramientos y consultar indicadores agregados; las acciones de captura y revisión requieren roles de servicio explícitos. No autoasignarse permisos.

En la interfaz, Dirección crea campus → sede → servicio, confirma el alcance, crea usuarios y aprueba nombramientos. Después selecciona preguntas del catálogo autorizado. El colaborador o responsable prepara cada ficha; otra persona con permiso revisa y publica. Las diez secciones de todas las fichas seleccionadas del servicio deben estar completas y revisadas antes de publicar. La plantilla inicial vacía no se considera una ayuda suficiente.

El incremento 0.3 incorpora 177 borradores editoriales específicos en `imports/help-drafts-v1.json`, con diez apartados y referencias literales. En el editor, use «Comparar borrador de la fuente», revise la comparación y elija «Usar propuesta en el editor». Esto sólo cambia el texto local: guardar, revisar y publicar siguen siendo pasos independientes. La propuesta exige coincidencia exacta del lote y texto importados; las referencias se comprueban en el servidor. Si la fuente cambia, continúa disponible la edición manual. **Cero ayudas cuentan con revisión institucional real.**

Las consultas privadas permiten elegir otro revisor vigente del servicio, indicar una duda y fecha esperada, intercambiar mensajes y confirmar su resolución. Se abren desde la ficha o la captura; `/consultas` reúne las propias. Sólo sus dos participantes con acceso vigente pueden leerlas. Conservan las versiones de ayuda y respuesta al abrirse. Resolverlas no cambia aprobaciones.

Para regenerar el catálogo desde la redacción editable: `python3 imports/editorial/build_catalog.py`. Los temas, campos y ejemplos por pregunta están en `imports/editorial/topics.txt`; el reporte está en `imports/help-drafts-report.json`. No requiere servicios de IA.

Una nueva ayuda conserva su historial. Guardar un borrador no reemplaza la ficha publicada. Publicar un cambio conserva respuestas y revisiones previas, retira la validación vigente afectada y exige una revisión nueva. La migración 0005 conserva las ayudas publicadas del incremento anterior por servicio; una ayuda histórica sin autor verificable queda retirada de publicación, conservando sus respuestas para revisión.

## Extracción y revisión documental

Desde una respuesta guardada en borrador, adjunte TXT o CSV UTF-8 (coma como separador) de hasta 10 MB. El original queda privado y vinculado a esa versión de respuesta. La extracción mantiene líneas TXT y filas/celdas CSV, incluidas filas con saltos de línea. Las fórmulas se conservan como texto; no se ejecutan.

Ejecute el trabajador con el entorno de la **base propia del proyecto**:

```bash
backend/.venv/bin/python backend/manage.py extract_evidence
```

Procesa hasta diez trabajos y termina. «Ver texto y revisión» muestra fragmentos paginados, estado e historial; «Actualizar documento» consulta el progreso. Otra persona con permiso de revisión puede aceptar con fundamento y fecha de vigencia, o devolver con observaciones. Se señala vigencia vencida y evidencia vinculada a una respuesta anterior. Aceptar evidencia no valida la respuesta ni acredita cumplimiento normativo.

Límites de extracción: dos millones de caracteres, diez mil fragmentos, doscientas columnas CSV y doscientos mil caracteres por celda. Se rechaza el exceso completo; no se presenta una extracción parcial como completa. El proceso recibe los bytes por entrada estándar, sin credenciales de Django, con 256 MiB, 4 segundos de CPU y 8 segundos de tiempo total. Sin firmas configuradas se conserva únicamente esta ruta básica de TXT/CSV. El incremento 0.5 añade la ruta binaria aislada descrita a continuación. No se invocan proveedores de IA.

Los trabajos interrumpidos pueden recuperarse al vencer su arrendamiento de 180 segundos. Un token impide que un trabajador antiguo publique resultados después de su reemplazo. Hay hasta tres intentos; un fallo puede reintentarse expresamente desde la ficha mientras queden intentos. Los registros heredados se ponen en cola sin reemplazar originales. La plantilla del temporizador incluye el comando, pero no está instalada.

## PDF, Office y OCR (0.5)

Configure `DOCUMENT_SIGNATURES` con un directorio exclusivo de firmas ClamAV actuales y `DOCUMENT_SCAN_CERTIFICATES` con los certificados públicos del motor. El sistema no ejecuta FreshClam ni modifica sus servicios. Si el motor, las firmas o el aislamiento fallan, el documento sigue bloqueado. PDF/DOCX/XLSX se habilitan únicamente con esta configuración; las descargas esperan el análisis y comprueban integridad. Los TXT/CSV nuevos también se analizan cuando está habilitado.

Para preparar OCR sin instalar paquetes globales:

```bash
python3 deploy/prepare_ocr.py
# Configurar en el entorno propio de la aplicación:
# DOCUMENT_OCR_RUNTIME=/RUTA/DEL/PROYECTO/backend/vendor/ocr/runtime
```

Esto habilita PNG/JPEG y OCR de PDF escaneado. Los binarios y datos se reconstruyen desde paquetes fijados en `backend/vendor/ocr/manifest.json`. Verifique compatibilidad y actualizaciones antes de producción.

La interfaz muestra páginas PDF, párrafos DOCX o celdas XLSX, estado de seguridad y texto OCR con confianza orientativa. La aceptación de OCR exige «Comparé el texto OCR con el original» y una persona revisora distinta. Las fórmulas XLSX se conservan sin evaluar; los valores almacenados no se recalculan. Se rechazan macros, objetos activos, documentos cifrados, referencias externas y archivos fuera de límites.

Límites: PDF textual hasta 200 páginas; OCR hasta diez páginas y cincuenta segundos por documento; imágenes hasta dieciséis megapíxeles; Office expandido hasta 30 MB y mil entradas. No se admiten DOC/XLS antiguos ni interpretación de gráficos o imágenes incrustadas en Office. El original sigue disponible tras un análisis limpio aunque la extracción requiera corregir el formato; contenido activo o detecciones mantienen el bloqueo.

## Asistencia IA con documentos (0.6)

Adaptadores OpenAI/DeepSeek, políticas por servicio, autorización independiente de fragmentos, cuotas y comprobación literal de citas. Propuestas comparables con el texto actual; usarlas crea un borrador pendiente de confirmación. La salida externa permanece deshabilitada. Consulte [configuración, límites y pendientes](docs/ENTREGA_0_6.md); no se efectuaron llamadas reales ni se enviaron documentos institucionales.

## Matriz de cumplimiento (0.7)

En «Cumplimiento», vincule norma/numeral, control, proceso, pregunta, respuesta versionada, evidencia, prueba y revisión independiente. Se conservan N01–N60 y encabezados C01–C20 del plan. La importación no verifica vigencia ni aplicabilidad. Consulte [recorrido y límites](docs/ENTREGA_0_7.md).

## Seguimiento y calendario (0.8)

«Seguimiento» incorpora propuestas de tarea, aprobación independiente de línea base, tablero por estado, filtros, calendario con dependencias y fechas propuestas, tiempo real, cierre independiente y avisos internos con calendario confirmado. La capacidad de 354 horas permanece como referencia institucional provisional. Consulte [reglas y límites](docs/ENTREGA_0_8.md).

## Verificar

```bash
bash deploy/verify.sh
# Ensayo de navegador aislado (PostgreSQL local y Chromium de Playwright):
python3 tests/run_browser.py
```

Las pruebas Django requieren PostgreSQL y permiso para crear una base de pruebas. Sólo usan datos sintéticos. El ensayo de navegador crea y destruye un clúster temporal y reserva sus propios sockets de loopback; nunca reutiliza servidores existentes. Requiere los binarios de PostgreSQL 16 (o `TEST_PG_BIN` compatible) y el navegador Chromium de la versión instalada de Playwright. Si falta, instalarlo en un directorio privado de pruebas mediante `PLAYWRIGHT_BROWSERS_PATH=/tmp/salud-browser-cache npx playwright install chromium` desde frontend, y conservar esa variable para ejecutar el ensayo. No instalar dependencias del sistema ni alterar navegadores de otras aplicaciones. OpenAPI autenticado: `/api/v1/schema/`; explorador: `/api/v1/docs/`. El trabajador `python backend/manage.py worker` crea notificaciones internas idempotentes, sin enviar mensajes externos.

## Estado y continuidad

- [Decisiones y limitaciones](docs/DECISIONES.md)
- [Backlog trazable completo](docs/BACKLOG.md)
- [Manual por función y recuperación](docs/OPERACION.md)
- [Entrega 0.8: seguimiento y calendario](docs/ENTREGA_0_8.md)
- [Entrega 0.7: matriz de cumplimiento](docs/ENTREGA_0_7.md)
- [Entrega 0.6: asistencia con documentos](docs/ENTREGA_0_6.md)
- [Entrega 0.5 y verificación](docs/ENTREGA_0_5.md)
- [Entrega 0.4 histórica](docs/ENTREGA_0_4.md)
- [Entrega 0.3 histórica](docs/ENTREGA_0_3.md)
- [Entrega 0.2 histórica](docs/ENTREGA_0_2.md)

Pendientes principales: adaptación y revisión institucional de las 177 propuestas; suplencias y ampliaciones administrativas; importación de cambios con invalidación explícita; corpus documental y retención; completar entrevista y evaluación IA; revisión normativa institucional; métricas/calendario completos; módulos clínicos; MFA; ampliación de pruebas de navegador a los siguientes módulos; respaldos/restauración y despliegue. No confundir pruebas del recorrido inicial con aceptación integral del prompt.


## Validación institucional — paquete preparado

Disponible [el paquete ZIP](entregas/validacion-institucional-2026-09-24/paquete_revision.zip) y [el catálogo navegable de 177 fichas](entregas/validacion-institucional-2026-09-24/fichas.html), con hojas de revisión por servicio, responsables, reglas, plantillas de usabilidad y acta. Abrir localmente, sin servidor. Todas las decisiones están pendientes; no consulta ni modifica aprobaciones del gestor.

Ver [guía de revisión](docs/validacion/GUIA.md) y [entrega del punto 5](docs/ENTREGA_VALIDACION_INSTITUCIONAL.md) para generación, pruebas, registro de resultados y límites. La preparación del paquete no acredita validación institucional ni aceptación clínica.


## Respaldo y ensayo de recuperación

Herramienta `tools/recovery.py`: respaldo cifrado con age y restauración comprobada en un clúster temporal por socket privado. Ocho pruebas con datos sintéticos aprobaron integridad, historial, permisos, pendientes y escritura concurrente. Consultar [RECUPERACION.md](docs/RECUPERACION.md) y [medición del ensayo](docs/recovery-test-report.json). No se instala ni activa nada en el VPS; MFA, monitoreo, copia externa y RPO/RTO de producción siguen pendientes.


## Autenticación en dos pasos (0.9)

MFA obligatorio para perfiles privilegiados y para cuentas que lo activen. Incluye enrolamiento, sustitución y códigos de recuperación de un uso desde Seguridad de la cuenta. La clave `MFA_ENCRYPTION_KEY` es independiente y debe configurarse antes del acceso privilegiado; no hay una clave de producción precargada. [Entrega, operación y pruebas](docs/ENTREGA_0_9.md). Monitoreo y pendientes operativos siguen en BACKLOG.


## Monitoreo local

`monitor_health` observa base, colas, trabajador, disco, certificados, respaldos, MFA y reservas IA; registra alertas privadas sin enviar mensajes ni modificar datos de negocio. `worker_cycle` añade señal al procesamiento existente. [Operación, pruebas y límites](docs/MONITOREO.md). Plantillas sin instalar; supervisión externa y operación institucional pendientes.


## Entrevista persistente (0.10)

Desde cada pregunta publicada, guarde declaraciones por apartado, retome su avance e incorpore aclaraciones de solicitudes IA autorizadas. La memoria permanece privada en el gestor y sólo pasa a respuesta mediante un traslado explícito a borrador por confirmar. [Entrega, límites y pruebas](docs/ENTREGA_0_10.md). Evaluación institucional de IA pendiente.

Evaluación de IA: [corpus sintético, ejecutor offline y rúbrica humana](docs/EVALUACION_IA.md). 54 casos; sin llamadas reales ni aceptación institucional.

Acciones explícitas de IA y autorización por servicio: [entrega 0.11](docs/ENTREGA_0_11.md).

Revisión de respuestas con autorización independiente y confirmación de envío: [entrega 0.12](docs/ENTREGA_0_12.md).

Comparación de posibles contradicciones entre fuentes autorizadas: [entrega 0.13](docs/ENTREGA_0_13.md).

Informes semanales locales, borradores IA y antecedente autorizado por finalidad: [entrega 0.14](docs/ENTREGA_0_14.md).

Registro de decisiones, resolución independiente e historial: [entrega 0.15](docs/ENTREGA_0_15.md).

Capacidad diaria, ausencias y distribución institucional con aprobación independiente: [entrega 0.16](docs/ENTREGA_0_16.md).

Informes conservados, revisión independiente y exportación: [entrega 0.17](docs/ENTREGA_0_17.md).

Retiro y sustitución formal de informes: [entrega 0.18](docs/ENTREGA_0_18.md).

Avisos personales de decisiones y acuse: [entrega 0.19](docs/ENTREGA_0_19.md).

Suplencias temporales de nombramientos: [entrega 0.20](docs/ENTREGA_0_20.md).

Integración de suplencias con tareas y avisos: [entrega 0.21](docs/ENTREGA_0_21.md).

Generación semanal programada de borradores: [entrega 0.22](docs/ENTREGA_0_22.md).

Recuperación explícita de semanas omitidas: [entrega 0.23](docs/ENTREGA_0_23.md).

Distribución interna y acuse: [entrega 0.24](docs/ENTREGA_0_24.md). Condiciones para [cerrar el piloto del gestor](docs/CIERRE_PILOTO_GESTOR.md).

Entrega 0.25: [paginación de destinatarios, entregas y bandeja](docs/ENTREGA_0_25.md), sin el bloqueo anterior de 500 registros.

Entrega 0.26: [correcciones de horas con historial](docs/ENTREGA_0_26.md), totales efectivos e informes originales conservados.

Entrega 0.27: [capacidad y ausencias vinculadas a la planificación de tareas](docs/ENTREGA_0_27.md), comparación diaria de carga y sobrecarga por servicio.

Entrega 0.28: [controles de cierre del gestor](docs/ENTREGA_0_28.md) y [guía para reunión con Dirección del 29 de septiembre](docs/REUNION_CIERRE_2026_09_29.md).

Entrega 0.29: [correcciones administrativas de horas con revisión independiente](docs/ENTREGA_0_29.md).

Pruebas del servidor con PostgreSQL temporal por socket Unix (sin reutilizar bases): `python3 tests/run_backend.py`. Requiere los binarios locales de PostgreSQL 16; puede indicarse otra ruta mediante `TEST_PG_BIN`.

Entrega 0.30: [recuperación excepcional de autenticador con doble autorización y reinscripción obligatoria](docs/ENTREGA_0_30.md). Deshabilitada por defecto, pendiente de acuerdo institucional antes del uso real.

Entrega 0.31: [historial completo de informes y búsqueda paginada de sustitutos aprobados](docs/ENTREGA_0_31.md). API e interfaz deben publicarse juntas.

### Entrada pública corregida — 0.35.1

El dominio principal abre la portada de los seis servicios. El personal ingresa por `/personal`; `/portal` conserva la misma portada por compatibilidad. Backend 0.35 y esquema 0042 sin cambios. Operación y reversión exclusiva de interfaz: [REDEPLOY_0_35_1.md](deploy/demo/REDEPLOY_0_35_1.md). Solicitudes reales todavía deshabilitadas.

Interfaz del personal actualizada a 0.35.2: identidad compartida con el portal, escuelas pares y pasos de acceso. [Operación y reversión](deploy/demo/REDEPLOY_0_35_2.md). Backend/esquema sin cambios.

Demo 0.35.3: acceso temporal sólo con usuario y contraseña por instrucción del usuario. Autenticadores conservados; reactivar y comprobar antes de información real. [Configuración y reactivación](deploy/demo/REDEPLOY_0_35_3.md).

Inicio autenticado 0.35.4: panel académico en `/personal`, con escuelas autorizadas, métricas y accesos a prácticas/evaluaciones/informes. Gestor anterior conservado en `/personal/plan`. [Operación del parche](deploy/demo/REDEPLOY_0_35_4.md). Backend 0.35.3 y modo temporal de contraseña conservados.

Directorio institucional 0.36: seis servicios publicados por Universidad Modelo incorporados a base y portal/paneles. [Datos, fuentes y límites](docs/SERVICIOS_INSTITUCIONALES_0_36.md) · [Despliegue](deploy/demo/REDEPLOY_0_36.md). Nueva migración 0043 aplicada; atención real todavía no habilitada.

0.36.1: fichas institucionales plegadas por defecto en Escuelas para priorizar captura. [Operación del parche](deploy/demo/REDEPLOY_0_36_1.md).
# saludmodelo
