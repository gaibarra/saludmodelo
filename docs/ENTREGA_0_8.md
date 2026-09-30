# Entrega 0.8 — seguimiento, calendario y línea base

Continuación del punto 4. Se incorpora seguimiento operativo de tareas por servicio, con historial y aprobación explícita de compromisos. No se aprobaron calendarios, tareas, responsables ni entregas institucionales reales.

## Tareas y línea base

La pantalla **Seguimiento** permite crear propuestas con responsable, suplente, coordinador, fechas, prioridad, esfuerzo en minutos, criterios de aceptación y predecesoras. El tablero se filtra por servicio/sede, responsable, prioridad, estado y periodo de vencimiento. Las tarjetas de tareas abren sus listas; se muestra la hora de actualización en la zona de la sede.

Una propuesta permanece fuera de línea base hasta que Dirección, dentro del servicio autorizado, aprueba la solicitud de otra persona. Las altas comprometidas, modificaciones, reaperturas y cancelaciones guardan propuesta, valores previos, fundamento, solicitante, revisor y fechas. Un cambio pendiente no modifica el trabajo vigente; si éste cambió, la aprobación recibe 409. No se eliminan tareas canceladas ni sus horas para mejorar porcentajes.

Los estados son pendiente, en curso, bloqueada, entrega en revisión, cierre aceptado, devuelta y cancelada. La entrega lleva una declaración de resultado; el cierre requiere otra persona distinta del responsable y de quien envió la entrega. Se registra el fundamento del cotejo con los criterios de aceptación. Esto acepta una tarea de gestión: no acredita por sí mismo una prueba clínica, proceso completo o salida de un servicio.

Las dependencias usan claves foráneas, son del mismo servicio y rechazan ciclos, referencias ajenas, predecesoras canceladas y fechas incompatibles. No se puede iniciar, entregar o aceptar una tarea con predecesoras sin cierre aceptado. Cambiar una predecesora reabre para revisión sus sucesoras aceptadas/en revisión y bloquea las que estén en curso, conservando las aceptaciones anteriores y generando avisos internos.

El calendario muestra fechas guardadas, dependencias y fechas propuestas con relaciones fin-a-inicio. Una cadena bloqueada sin resolución permanece sin fecha estimable. El cálculo no altera automáticamente la línea base. No es una optimización por disponibilidad de recursos compartidos ni un compromiso de fechas de IA.

## Calendario y avisos

Dirección necesita mandato institucional para confirmar días de semana laborables y fechas no laborables. Cada confirmación queda versionada y afecta al calendario de la institución. Antes de confirmarlo, sólo se calcula una propuesta orientativa de lunes a viernes y **no se generan avisos programados**. No se precargaron festivos ni ausencias como hechos aprobados.

Con calendario confirmado, `tracking_reminders` genera avisos internos al responsable al vencer y al suplente/coordinador asignados al cumplirse dos/tres días hábiles sin respuesta. Se cuentan días posteriores al vencimiento o a la última respuesta de estado, lo que sea posterior; se excluyen días no laborables. Son acuerdos internos, no plazos legales. Sólo se procesan tareas comprometidas que no estén aceptadas, canceladas o esperando revisión de entrega.

Los eventos tienen claves de deduplicación y versión de tarea. El trabajador existente entrega las notificaciones una sola vez y comprueba de nuevo permisos, estado y versión; descarta avisos obsoletos o destinados a usuarios sin permiso vigente. Sin suplente/coordinador vigente no se inventa un destinatario. No se envían correos ni mensajes externos. La plantilla systemd incorpora el generador antes del drenado del outbox, **sin instalarla ni activarla**.

## Horas y métricas

El tiempo real se registra por persona, fecha, minutos y fundamento, con clave de idempotencia; se rechazan duplicados incompatibles, más de 24 horas diarias, fechas anteriores al 1 de octubre de 2026 o posteriores al día de la sede. Los registros son históricos y no se sobrescriben desde esta pantalla; una corrección requiere el procedimiento pendiente, no editar el pasado silenciosamente.

- Captura suficiente: respuesta vigente conocida, no vacía, enviada o validada / preguntas del alcance confirmado del servicio.
- Respuestas validadas: estado vigente validado / preguntas del mismo alcance.
- Cierres aceptados: tareas comprometidas aceptadas / todas las tareas comprometidas; las canceladas permanecen en el denominador y se muestran aparte.
- Tareas vencidas, próximas a vencer, bloqueadas y críticas; carga por responsable y horas estimadas/reales del servicio visible. Estas listas incluyen propuestas, que se distinguen de las tareas comprometidas.

Un denominador cero muestra «Sin alcance definido». Los indicadores del servicio no cambian de universo al filtrar la lista. Aceptación integral de procesos/servicios y consumo de reserva se muestran como pendientes, porque faltan sus criterios o asignaciones institucionales; no se fabrican porcentajes.

`imports/work-calendar-reference.json` conserva C22, sus ventanas de módulos/pilotos y el calendario del prompt. Sólo se muestra a instituciones con permiso del lote fuente. **295 horas base + 59 de reserva = 354 horas** es una referencia institucional provisional, no una bolsa por servicio; no se multiplica por unidades ni se presenta como capacidad ya aprobada. El tablero no calcula consumo de reserva sin asignación institucional.

## Seguridad, API y límites

Todas las consultas y mutaciones vuelven a comprobar alcance vigente. Los mandatos institucionales permiten configurar calendarios; no conceden por sí solos acceso a datos de tareas sin nombramiento de servicio. Control de concurrencia por versión y bloqueo del servicio para cambios del grafo. Respuestas privadas, sin caché compartida. Migración 0014 aditiva, conservando tareas y eventos previos.

API: `/api/v1/tracking/services/{id}/`, `/calendar/`, `/source/`; `/api/v1/tracking/tasks/{id}/`, `/change/`, `/state/`, `/time/`; y `/api/v1/tracking/changes/{id}/decision/`. Contratos incluidos en OpenAPI.

Límites actuales: tablero hasta mil tareas por servicio; historial visible de últimos cien eventos, solicitudes y registros de tiempo (los anteriores se conservan); hasta cincuenta predecesoras por tarea y mil fechas no laborables. Las dependencias entre servicios, redistribución institucional de capacidad, corrección de horas, renovación automática de evidencia, resumen semanal, alertas de procesos/decisiones y métricas integrales de aceptación siguen pendientes. Los indicadores normativos detallados se revisan en la matriz de cumplimiento; no se mezclan con avance de proyecto.

## Verificación

Pruebas específicas: compromiso independiente, autoaceptación rechazada, cancelaciones conservadas, dependencias/ciclos, cambios obsoletos, horas idempotentes, aislamiento por servicio, calendario confirmado, festivos, avisos a suplente/coordinador, destinatarios revocados y reapertura de sucesoras. Ensayo de navegador con una tercera institución sintética aislada y reloj de dominio simulado sólo en el servidor de pruebas. No se registraron actividades reales anteriores al inicio del plan ni se alteraron aplicaciones ajenas.

Cierre de verificación: **87 pruebas en la regresión completa aprobadas**; tras el ajuste final de bloqueos se aprobaron **11 pruebas específicas de seguimiento**, incluida una prueba con dos conexiones concurrentes y la misma clave de registro de horas. **Cuatro recorridos Playwright aprobados** (gestor, acceso móvil, cumplimiento y seguimiento), compilación Next.js/TypeScript correcta y OpenAPI sin advertencias. Migración 0014 comprobada en el PostgreSQL privado; no hay cambios de modelo sin migración. Las fuentes DOCX y prompt conservan sus huellas.
