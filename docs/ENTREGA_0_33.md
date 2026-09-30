# Núcleo académico de prácticas — 0.33

Este incremento permite organizar alumnos, ciclos, rotaciones y supervisores, registrar participaciones reales y consultar su revisión en todos los servicios configurados de la institución. La pantalla se abre en `/academico`, desde «Prácticas académicas» en el acceso del personal. No depende del catálogo público de seis áreas ni requiere habilitar el registro de pacientes.

## Recorrido de uso

1. Dirección crea las cuentas del alumno y del supervisor desde Administración. El supervisor debe tener un nombramiento clínico o de responsable del servicio que cubra las fechas de la rotación.
2. En «Configurar núcleo académico», Dirección registra el ciclo, matrícula y programa del alumno. Luego asigna servicio, grupo, fechas, supervisor y, si existe, una meta de minutos.
3. El alumno ingresa con su cuenta y selecciona «Registrar práctica». Indica actividad efectivamente realizada, fecha, minutos de su participación, competencia trabajada y referencia de evidencia.
4. El supervisor consulta las prácticas que tiene asignadas. Valida la participación o la devuelve con observaciones. El alumno puede corregir una práctica devuelta y enviarla otra vez; ambas versiones se conservan.
5. Dirección consulta alumnos y servicios con filtros de institución, ciclo, alumno, servicio, supervisor, programa y grupo. El resumen separa participaciones y minutos por revisar, devueltos, validados y anulados.

La referencia de evidencia es un folio o localizador textual para revisión del supervisor. No se adjuntan archivos ni se capturan datos de pacientes en esta pantalla. Cada registro corresponde a la participación de un alumno: dos alumnos en una jornada representan dos participaciones, no dos pacientes ni necesariamente dos actividades diferentes. Puede conservarse una referencia compartida, pero aún no existe una entidad de actividad colectiva que consolide participantes.

## Controles incluidos

- Sólo Dirección con mandato institucional vigente puede crear ciclos, registrar alumnos y asignar o revocar rotaciones. La cuenta del alumno debe pertenecer a la institución y estar activa.
- El alumno consulta y registra sus propias participaciones. El supervisor consulta las asignadas a su cuenta mientras conserva nombramiento vigente en el servicio. Dirección consulta transversalmente su institución. No se concede acceso clínico por estos permisos.
- Las fechas de rotación deben estar dentro del ciclo; la fecha de práctica debe estar dentro de la rotación y no ser futura. Se impiden rotaciones activas superpuestas de un alumno en el mismo servicio.
- El alumno no puede ser su propio supervisor ni validar su práctica. La validación corresponde al supervisor asignado; el mandato de Dirección por sí solo no permite validar en su lugar.
- Correcciones sólo sobre prácticas devueltas; validación y anulación conservan los datos y eventos anteriores. Se exige versión actual y motivo de revisión. La anulación la realiza el supervisor autorizado o Dirección y elimina la participación del subtotal validado, conservándola en el subtotal de anuladas.
- El límite de 1440 minutos por alumno y día considera todos sus servicios y registros no anulados. Los envíos y cambios bloquean al alumno en la transacción para proteger el límite ante concurrencia. No comprueba solapamientos horarios porque este incremento registra duración diaria, no intervalos de inicio/fin.
- Reintentos de un mismo envío conservan su identificador y no crean otra práctica. Listas e historial paginados; los totales se calculan sobre todos los registros autorizados que cumplen los filtros, no sólo la primera página.
- Revocar una rotación impide nuevas entregas, correcciones y validaciones en ella; preserva el historial. Dirección puede anular un registro con motivo si procede. El reemplazo de supervisor de prácticas pendientes se conserva como ampliación pendiente.

## Alcance pendiente

El núcleo no acredita automáticamente un ciclo ni genera todavía un acta de cierre. Quedan rúbricas y catálogo de competencias, evaluación académica con reglas institucionales, sustitución de supervisores, edición administrativa versionada de matrículas/ciclos/asignaciones, evidencias documentales académicas, informes finales individuales y consolidados con corte conservado, actividad colectiva, integración con atenciones/expedientes y adopción institucional.

La meta de minutos es una referencia configurada; no equivale a un requisito académico confirmado ni determina por sí sola la acreditación. Las horas del gestor de tareas y las citas de pacientes no se convierten en prácticas. La IA no valida participaciones ni decide acreditaciones en este incremento.

## Instalación y verificación

Migración aditiva `0040_academic_core`, modelos, API, interfaz y pruebas incorporados en el proyecto. La migración se ejecuta solamente en clústeres temporales privados de las pruebas durante este desarrollo. No se actualiza la demostración pública ni se modifican aplicaciones del VPS.

Pruebas reproducibles:

- `python3 tests/run_backend.py core.test_academic core.test_migrations core.test_public_portal`
- `E2E_TEST_PATTERN='núcleo académico' python3 tests/run_browser.py`
- `cd frontend && npm run typecheck && npm run build`

El resultado final de la verificación se registra en `docs/DECISIONES.md`.

Resultado de verificación del 30/09/2026: 20 pruebas backend aprobadas; OpenAPI y migraciones sin diferencias pendientes; recorrido de navegador completo aprobado en escritorio y móvil; TypeScript y compilación 0.33 correctos. Evidencias visuales: `frontend/test-results/academic-desktop.png` y `frontend/test-results/academic-mobile.png`. Todos los recursos temporales del ensayo fueron retirados por sus ejecutores.
