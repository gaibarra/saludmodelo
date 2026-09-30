# Entrega 0.14 — informes y antecedente autorizado para la guía

Se atienden dos pendientes de IA y parte del resumen semanal de seguimiento. No se declara completado el alcance clínico ni la validación institucional.

## Informe semanal local

La pantalla «Informes semanales» calcula un borrador por servicio y período de siete días desde registros reales. Por defecto comienza el lunes de la semana actual, en America/Merida. Separa:

- Estado actual: tareas aceptadas/comprometidas, cancelaciones, propuestas sin compromiso y tareas comprometidas vencidas, bloqueadas y críticas; respuestas validadas frente a preguntas asignadas.
- Actividad del período: eventos de tareas, decisiones de cambios de línea base y minutos registrados por fecha de trabajo. La semana actual se identifica como incompleta.
- Decisiones de línea base pendientes, referencias de tareas/preguntas/respuestas y destinatarios con cuenta activa y acceso vigente al servicio.

No reconstruye el estado al cierre de una semana pasada. No equipara validación de respuesta con cumplimiento ni calcula aceptación clínica. Tareas canceladas permanecen en el denominador de la línea base. Cero alcance se muestra como «Sin alcance definido».

El informe se consulta mediante GET `/api/v1/reports/services/{service}/weekly/?start=YYYY-MM-DD`; `weekly/export/` genera JSON descargable con una nueva consulta de permisos y datos. La exportación puede diferir de una vista previa anterior. La aplicación registra auditoría de consulta/exportación, pero no guarda una instantánea histórica del contenido del informe. El archivo descargado conserva sus referencias y fecha de generación.

Cada generación usa una transacción PostgreSQL REPEATABLE READ de sólo lectura con límite de cinco segundos por consulta, seguida de auditoría fuera de esa transacción. Límite de 1000 registros por sección: se rechaza el informe completo al excederlo, sin truncamiento silencioso. No se incluyen notas libres de eventos ni contenido de respuestas. Acceso por asignación de servicio vigente; el privilegio técnico o un mandato institucional por sí solos no conceden acceso a los datos. Respuesta privada sin caché.

No se envía correo, notificación ni contenido a proveedores. El listado de destinatarios sólo prepara la revisión; cualquier envío futuro requiere nueva comprobación de alcance y canal institucional aprobado. La selección/persistencia de destinatarios, aprobación formal del informe y programación semanal siguen pendientes.

## Borrador de informe IA

La acción `report` prepara un borrador sobre una pregunta desde uno a ocho fragmentos autorizados. Requiere habilitación explícita en política del servicio, explicación no vacía y citas verificadas; no admite campos propuestos ni aplicación a respuesta. Hereda cola, cuotas, revocación, vigencia y configuración de modelo por acción.

Este borrador no recibe el resumen semanal, métricas del proyecto, respuestas, destinatarios ni memoria. No es un informe institucional integral. Las instrucciones distinguen hechos documentados, faltantes y posibles contradicciones. La calidad semántica permanece pendiente de revisión humana. Migración 0020 amplía opciones sin autorizar automáticamente políticas existentes.

## Antecedente autorizado en la guía

La acción `interview` puede incorporar opcionalmente la versión guardada de una respuesta. La autorización independiente ahora declara finalidad: `review` o `interview`. La migración 0021 conserva todas las autorizaciones anteriores como `review`; no las amplía a la guía.

El capturista selecciona una autorización para proveedor y finalidad correctos, ve el texto y confirma el envío. Sin selección, la guía continúa sin antecedentes. El backend obtiene el texto desde la revisión referenciada e incluye versión y estado declarado de conocimiento; no acepta texto arbitrario en la solicitud. Una autorización para revisión no sirve para memoria, ni al revés.

Se conservan revisión por otra persona, etag, huella, vigencia, cuenta y permiso vigente de quien autoriza. Revocación o cambio bloquean el envío/resultado; la revocación no retira lo ya enviado. La guía no reemplaza respuestas ni confirma hechos. Un antecedente conocido por declaración no equivale a aprobación institucional.

La entrevista privada y su historial no salen. Para usar parte de ella como antecedente, la persona primero debe trasladar explícitamente lo pertinente a una respuesta compartida y guardarla; después se requiere autorización independiente para esa nueva versión. No se implementa memoria persistente en el proveedor, embeddings ni recuperación entre preguntas/servicios. La no repetición semántica de preguntas se instruye, pero requiere evaluación humana; la deduplicación local existente es textual.

Nuevas solicitudes usan `salud-actions-6`. Se mantienen los adaptadores externos sin nuevas capacidades de red. No se realizaron llamadas reales ni se configuraron claves/modelos institucionales.

## Pruebas y siguientes pendientes

Las pruebas verifican límites de fecha local, registros del instante de generación, cero denominador, cancelaciones, exclusión de notas, permisos de consulta/exportación, revocación, destinatarios, límites y consistencia ante escritura concurrente. En IA verifican borrador con citas y ausencia de escritura, finalidades incompatibles, antecedente opcional con confirmación y revocación. Los recorridos de navegador usan API real aislada para el informe local y respuestas simuladas para IA.

Siguen pendientes evaluación humana y 177 fichas institucionales, corpus autorizado, ampliaciones de seguimiento, retención, recuperación excepcional y operación externa, módulos clínicos/administrativos, portal y aceptación/despliegue. El backlog conserva cada paquete. No se modificaron aplicaciones ajenas del VPS ni se instalaron plantillas de producción.

Resultado técnico final: 158 pruebas de backend y once recorridos de navegador aprobados. Compilación 0.14/TypeScript correcta y OpenAPI validado sin advertencias. Migraciones 0020/0021 aplicadas únicamente en la base privada de desarrollo; clúster propio detenido al terminar.
