# Entrega 0.23 — recuperación explícita de semanas omitidas

Dirección con lectura vigente del servicio puede recuperar una semana completa mediante el formulario de programación de informes. Se requiere una configuración existente, su versión actual, el lunes del período y un motivo. La operación genera un borrador conservado pendiente de revisión, sin aprobarlo ni enviarlo.

## Alcance de la recuperación

Se admiten lunes desde el 5 de octubre de 2026 y únicamente semanas ya concluidas, con fechas America/Merida. Se recupera una semana por solicitud; no se lanza un lote ni se rellenan períodos automáticamente. Puede solicitarse con la programación pausada y para semanas anteriores a su primera semana elegible: es una autorización explícita de quien hace la solicitud, no una ampliación implícita de la autorización periódica.

El contenido usa el generador consistente existente: actividad del intervalo y estado observado al generar. No reconstruye el estado del sistema al cierre de una semana pasada. Consulta y exportación identifican `backfill`, programación, versión y motivo, y muestran la fecha real de generación. La persona que solicita figura como responsable y no puede aprobar su propio borrador.

## Duplicados y conservación

La generación automática y la recuperación comparten la restricción única por programación/período. Si ya existe una ejecución para esa semana, se devuelve el informe vinculado sin crear otro ni cambiar su contenido, resolución o motivo original. Esto se aplica también si el informe fue rechazado, retirado o sustituido; una corrección usa el recorrido manual existente y su revisión independiente.

Los informes manuales independientes del registro programado no se reemplazan ni se consideran una ejecución automática de esa semana. Pueden existir varias versiones manuales del mismo período según las reglas existentes.

El cálculo ocurre fuera de la transacción de escritura. Al guardar se bloquean servicio y configuración y se comprueban otra vez versión, cuenta activa, lectura y autoridad de Dirección. Cambios de configuración o pérdida de autoridad durante el cálculo impiden guardar. Informe y vínculo se crean juntos; los fallos no dejan registros parciales. Los reintentos y ciclos automáticos simultáneos convergen en el mismo informe del período.

La comprobación de cuenta activa consulta la base de datos, tanto en recuperación como en programación, para no depender de una instancia de usuario cargada antes de una desactivación. Las revocaciones de rol se vuelven a consultar. Se conservan los controles de acceso actuales al descargar el resultado.

## Interfaz, API y operación

El formulario «Recuperar una semana omitida» está en `/reportes`, dentro de la programación. Tras guardar se informa si se creó el borrador o si ya existía, y se ofrece su consulta/exportación. Para revisión en pantalla, actualizar las versiones conservadas.

Endpoint: `POST /api/v1/reports/services/{service}/backfill/` con `version`, `period` y `rationale`. Respuestas privadas sin caché. La operación usa el límite existente del generador de 1000 registros por sección y tiempo máximo de consulta; no devuelve informes parciales.

Migración aditiva 0031: modalidad de generación y fundamento en `ScheduledReportRun`. Los registros anteriores conservan modalidad `scheduled`; no se reescribe contenido ni huellas. Una recuperación explícita no modifica el estado de la última comprobación automática; aparece como generación en el historial compartido.

No se activa ningún trabajador, temporizador, envío externo ni servicio del VPS. Continúan pendientes distribución por canales autorizados, otras frecuencias/horarios, integraciones de capacidad/ausencias, piloto institucional y los módulos clínicos/administrativos del plan.

## Verificación realizada

221 pruebas de backend aprobadas con PostgreSQL real aislado; trece específicas de recuperación/programación aprobadas antes de la regresión. Seis casos nuevos cubren origen del borrador, programación pausada, conservación de ejecuciones existentes incluso retiradas, fechas y autoridad, cambios de configuración/rol/cuenta durante cálculo, fallos recuperables y concurrencia automática/manual. Recorrido de navegador aprobado con respuesta de recuperación simulada para verificar formulario y enlace; no se presenta como generación real de una semana futura en el reloj del ensayo. Compilación 0.23/TypeScript y OpenAPI sin advertencias; sin migraciones pendientes de generar. Migración aplicada sólo en base privada por socket Unix y clúster propio detenido al cierre. Fuentes originales intactas por SHA-256; ninguna aplicación ajena del VPS modificada.
