# Evaluación por competencias e informes de cierre — 0.34

Dirección puede definir competencias para cada ciclo y servicio, los supervisores evaluar a sus alumnos con prácticas validadas y la institución conservar un informe de cierre individual y consolidado. Funciona con todos los servicios configurados; no depende del catálogo inicial de seis áreas del portal público.

## Uso en lenguaje sencillo

1. En **Prácticas académicas → Competencias e informes de cierre**, Dirección selecciona el ciclo y abre **Rúbricas y competencias**. Registra código, nombre y criterio observable de cada competencia, describe entre dos y seis niveles de desempeño y establece el mínimo requerido. Puede limitarla a un programa académico o aplicarla a todos los alumnos de ese servicio. Marca si es obligatoria y registra el motivo o referencia institucional.
2. El supervisor abre **Evaluaciones por alumno**, selecciona la rotación y elige el nivel observado. Debe señalar qué prácticas validadas de ese mismo alumno y rotación sustentan su evaluación, y justificarla. El alumno puede consultar el resultado y el historial; no evaluarse a sí mismo.
3. Dirección abre **Informes de cierre** y genera una versión del informe. Este conserva todos los alumnos con rotaciones en el ciclo, incluyendo quienes aún no tienen prácticas. Incluye todos los servicios, horas por estado, referencias de evidencias, competencias, evaluaciones, versiones e historial y pendientes.
4. Al abrir el informe, Dirección puede consultar el consolidado o seleccionar un alumno. **Imprimir o guardar PDF** utiliza la impresión del navegador para guardar la vista elegida. Los alumnos sólo ven sus informes individuales de versiones cerradas.
5. Al llegar la fecha de término del ciclo, Dirección puede cerrarlo con una versión vigente y un motivo. Si hay pendientes, debe reconocer expresamente que cierra con ellos. El cierre protege sus registros contra modificaciones. El informe documenta resultados: no concede automáticamente acreditación académica.
6. Para corregir después, Dirección utiliza **Reabrir ciclo**, indicando el motivo. El cierre anterior se conserva como histórico. Tras las correcciones se genera otro informe y se realiza un nuevo cierre.

## Qué se conserva y cómo se interpreta

- **Rúbrica:** criterio, descriptores de niveles, mínimo requerido, obligatoriedad, autor, motivo, fecha y versión. Cambiar una rúbrica crea otra versión; no sustituye la utilizada en evaluaciones anteriores.
- **Evaluación:** supervisor, nivel observado, justificación y prácticas/versiones que la sustentan. Una corrección crea otra valoración conservando las previas.
- **Estado de competencia:** sin evaluar, nivel requerido alcanzado, no alcanzado o requiere nueva revisión. Este último aparece cuando cambia la rúbrica o se anula/modifica la evidencia que sustentaba la valoración. La comparación con el nivel mínimo no es una acreditación del alumno o del ciclo.
- **Informe:** corte y versión, datos identificativos académicos del alumno, grupo, rotaciones, supervisores, servicios/sedes, prácticas y su historia, evaluación/competencia y su historia, metas de minutos y pendientes. Resumen por servicio y detalle completo por alumno. No se aplica el límite de la primera página de la pantalla de prácticas.
- **Cierre:** versión utilizada, responsable, fecha y motivo. No cambia el contenido del corte. Los informes posteriores se crean por separado.

El total es de participaciones de alumnos. Una jornada compartida no se convierte automáticamente en varias actividades institucionales o pacientes distintos. Las evidencias son referencias textuales; este incremento no adjunta documentos ni incluye expedientes clínicos.

## Permisos y consistencia

Dirección necesita un mandato institucional vigente para definir rúbricas, generar el consolidado, cerrar y reabrir. El supervisor debe ser el asignado a la rotación, distinto del alumno y con nombramiento vigente; sólo puede usar prácticas actualmente validadas de esa rotación en sus versiones actuales. Los estudiantes consultan sus evaluaciones y los informes cerrados que efectivamente los incluyen, nunca los registros de sus compañeros. El motivo institucional libre del cierre se reserva a Dirección; el informe del alumno muestra una indicación general de autorización.

Cada mutación académica bloquea primero el ciclo y actualiza su revisión. Generar un informe toma el mismo bloqueo para obtener un corte consistente. Un borrador queda desactualizado si después se registran o corrigen prácticas, asignaciones, rúbricas o evaluaciones. El servidor rechaza el cierre de ese borrador y requiere generar otro. Un cierre concurrente y una modificación posterior no pueden aprobarse ambos contra el mismo corte. El límite diario por alumno continúa protegido entre servicios y ciclos.

La huella de integridad del contenido se verifica al consultar y cerrar. La impresión usa la versión conservada, no reconstruye los datos actuales. Una reapertura no borra informes ni evaluaciones. Los informes individuales excluyen los resúmenes y registros de otros alumnos. Los borradores no se publican a alumnos ni se envían por correo.

## Alcance pendiente

La institución debe definir y validar sus competencias, niveles, mínimos y reglas formales de acreditación. Quedan sustitución de supervisores, correcciones administrativas versionadas de datos académicos base, evidencias adjuntas privadas, consolidación de actividades colectivas e integración con atenciones/expedientes. La firma electrónica de actas, constancias oficiales, calificaciones escolares y su integración con un sistema escolar no se presentan como implementadas. El cierre aquí es documental, con pendientes expresamente visibles cuando existan.

## Verificación y despliegue

Migración aditiva `0041_academic_assessment_reports`; las fuentes originales permanecen intactas. Se trabaja exclusivamente con bases PostgreSQL temporales por socket privado y servidores de ensayo propios. La demostración pública y las demás aplicaciones del VPS no se actualizan durante este incremento.

Pruebas reproducibles:

- `python3 tests/run_backend.py core.test_academic_assessment core.test_academic core.test_migrations`
- `E2E_TEST_PATTERN='cierre académico|núcleo académico' python3 tests/run_browser.py`
- `cd frontend && npm run typecheck && npm run build`

Evidencias de la prueba sintética: `frontend/test-results/academic-individual-report.pdf` y `frontend/test-results/academic-closure-report.png`. El resultado final comprobado se registra en `docs/DECISIONES.md`.

Resultado comprobado el 30/09/2026: 31 pruebas backend, dos recorridos de navegador, TypeScript, compilación y validación OpenAPI aprobados. El PDF individual se verificó con extracción de texto: contiene a la alumna seleccionada y su evidencia, conserva la marca de borrador y excluye a la otra alumna del ensayo. La revisión móvil comprobó ausencia de desbordamiento horizontal.
