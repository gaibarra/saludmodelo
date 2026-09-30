# Entrega 0.29 — correcciones administrativas de horas

Una persona de Dirección con lectura vigente del servicio puede solicitar un ajuste de minutos de otra persona. Otra persona de Dirección, distinta del solicitante y del autor de las horas, aprueba o rechaza con motivo. La solicitud por sí sola no cambia totales. Se conserva el registro original, el valor observado, la versión, la propuesta, las dos personas intervinientes y la decisión.

## Uso en la aplicación

En Seguimiento → Revisar tarea → Actividad y tiempo registrado, Dirección dispone de «Solicitar corrección administrativa» en entradas ajenas. El formulario pide minutos propuestos y justificación. También se puede solicitar desde el historial completo de horas, sin quedar limitado a las cien entradas del resumen.

En «Correcciones administrativas de horas», consultar solicitudes. El revisor independiente ve los valores anterior/propuesto y el motivo; puede aprobar o rechazar justificadamente. La consulta se pagina en grupos de 50, sin corte total. El autor y las demás personas con lectura vigente pueden consultar la trazabilidad, sin obtener autoridad administrativa por ello.

La revisión cambia únicamente minutos efectivos. Cero anula su cómputo sin borrar el original. No cambia fecha, tarea, categoría base/reserva, calendario, estado de tarea ni compromisos aprobados. Las tareas cerradas o canceladas también conservan la posibilidad de corrección histórica.

## Controles

- Solicitud y decisión requieren cuenta activa, autoridad de Dirección y lectura vigente del servicio. Un usuario técnico o administrador sin nombramiento no obtiene esta facultad. La propuesta de horas propias se rechaza: se conserva el recorrido de autocorrección existente.
- Al aprobar se vuelve a comprobar la autoridad del solicitante y del revisor. Si el solicitante perdió autorización, otro revisor habilitado puede rechazar la solicitud; no puede aprobarla.
- El autor de las horas puede estar inactivo: ése es uno de los casos que resuelve el procedimiento administrativo. El solicitante y el revisor deben ser personas activas y autorizadas.
- Una corrección del autor u otra aprobación posterior a la propuesta invalida la versión observada. Se responde con conflicto, sin sobrescribir. Se puede rechazar la solicitud antigua y crear una nueva.
- Se comparte el orden de bloqueo servicio → tarea → autor de las horas → entrada con las altas/autocorrecciones. El total diario efectivo del autor entre todos los servicios no puede superar 1440 minutos.
- Identificador de reintento por entrada y solicitante: repetir exactamente la solicitud devuelve la existente; reutilizar la clave con otro contenido produce conflicto. Repetir la misma decisión por el mismo revisor es idempotente. Una decisión incompatible no sobrescribe la anterior.
- La aprobación crea una versión de TimeCorrection vinculada a la solicitud. Los eventos de tarea conservan solicitud y decisión. La autocorrección ya no interpreta una corrección administrativa como reintento propio aunque coincidan minutos y motivo.
- Tablero, presupuesto real y nuevos informes usan los minutos efectivos existentes. Los informes ya conservados mantienen su contenido y huella; su sustitución sigue siendo explícita.

## API y migración

- `POST /api/v1/tracking/time/{id}/administrative/`: `version`, `minutes`, `rationale`, `client_key`.
- `GET /api/v1/tracking/tasks/{id}/time-requests/?before={id}`: historial paginado de solicitudes.
- `POST /api/v1/tracking/time-requests/{id}/decision/`: `approve`, `rationale`.

Migración aditiva `0037_administrative_time_correction`: crea las solicitudes con referencias protegidas y unicidad de reintento. No modifica horas originales. API e interfaz deben publicarse juntas.

## Alcance y operación

Este incremento implementa un procedimiento técnico para revisión institucional. No autoriza ajustes reales ni crea nombramientos; no se ha desplegado en producción. La institución debe confirmar qué personas ejercerán los roles y qué respaldo exigirá para las solicitudes. No incluye cierre contable, nómina, traslado de fecha/tarea ni recuperación excepcional de acceso.

Permanecen pendientes los avisos externos, ampliaciones de IA/informes, retención documental, recuperación excepcional, preparación operativa, piloto humano y alcance clínico/administrativo integral. Odontología sigue siendo un posible servicio piloto del gestor; su módulo clínico no se declara implementado.

## Verificación y reproducción

Ejecutar `python3 tests/run_backend.py` para comprobar Django, migraciones pendientes, la suite completa y el contrato OpenAPI. El ejecutor crea un clúster PostgreSQL exclusivo por socket Unix, sin TCP, deshabilita proveedores externos y elimina sus recursos al terminar. Se pueden pasar etiquetas de pruebas, por ejemplo `core.test_migrations core.tracking.test_administrative_time`.

La revisión detectó que la prueba histórica de migraciones restauraba una versión fija anterior; se cambió para restaurar la última migración disponible. La combinación de esa prueba y los doce casos administrativos pasó (13 pruebas). No se trataba de una pérdida de datos de operación: el fallo ocurrió en la base desechable de regresión.

Dos recorridos de navegador con API real y cuentas sintéticas aprobaron: autocorrección previa y solicitud/aprobación administrativa con consulta por el autor. Build final 0.29 y TypeScript aprobados. El archivo de dependencias conserva scheduler 0.27.0, coincidente con la versión e integridad instaladas; no se instalaron ni actualizaron dependencias. Las fuentes DOCX/prompt conservan sus hashes originales. La migración sólo se ejercitó en bases temporales; deberá aplicarse al entorno autorizado cuando se publique el incremento.

Regresión final completa: **266 pruebas aprobadas**, incluidas doce nuevas de correcciones administrativas; Django y OpenAPI validados, sin cambios de migración pendientes de generar. El primer ensayo completo detectó el problema de restauración de esquema descrito arriba; la repetición completa aprobó después de corregirlo. Todos los clústeres y servidores temporales de esta entrega quedaron detenidos y eliminados. No se activó producción ni se modificaron aplicaciones ajenas del VPS.
