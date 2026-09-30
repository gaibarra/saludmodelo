# Entrega 0.17 — informes conservados y aprobación

La pantalla «Informes semanales» permite generar y conservar una versión fija desde los registros del servicio, consultar su contenido, aprobarla o rechazarla por otra persona de Dirección y exportar la versión junto con su resolución. Guardar vuelve a consultar los datos; no conserva automáticamente un borrador previamente mostrado. La revisión se realiza sobre la versión conservada.

## Permisos y trazabilidad

Personal con permiso vigente de trabajo o Dirección puede generar versiones. Lectura y exportación requieren acceso vigente al servicio. Para aprobar o rechazar se necesitan acceso de lectura y autoridad de Dirección dentro del alcance; quien generó la versión no puede resolverla. No se concede acceso automático a cuentas técnicas.

La instantánea se calcula mediante la transacción de lectura consistente del informe semanal existente. Después se guarda en una transacción independiente que revalida permisos. Fechas de observación y generación identifican el momento del contenido; los cambios posteriores no actualizan esa versión. La resolución aprueba ese contenido histórico, sin afirmar que coincide con el estado actual.

La huella SHA-256 del contenido se comprueba al consultar, exportar y resolver. La solicitud de revisión incluye la huella consultada. Es un control de integridad de aplicación, no una firma digital ni protección frente a un administrador capaz de alterar simultáneamente contenido y huella.

Las claves de reintento se vinculan a servicio, persona y período. Repetirlas recupera la misma versión aunque los datos actuales hayan cambiado. Revisiones concurrentes se serializan; sólo una resolución distinta puede ganar. Repetir exactamente la resolución de la misma persona no duplica el evento. Auditoría registra creación, consulta/exportación y resolución.

## API y operación

- `GET/POST /api/v1/reports/services/{service}/saved/`: lista y generación de versiones.
- `GET /api/v1/reports/saved/{id}/`: contenido fijo y resolución, descargables como JSON.
- `POST /api/v1/reports/saved/{id}/`: aprobación o rechazo independiente.

Migración aditiva 0024, modelo `SavedReport`. Respuestas privadas sin caché. La lista admite hasta 500 versiones y rechaza explícitamente excedentes; paginación ampliada pendiente. No se modifica el informe conservado mediante API. La resolución se registra una sola vez; una corrección requiere generar y revisar otra versión. No hay sustitución, retiro ni revocación formal de una resolución en este incremento; versiones anteriores siguen visibles y ninguna se declara automáticamente vigente frente a otras.

El objeto de contenido conserva el estado `draft` del generador original; el estado de revisión se encuentra en el registro que lo envuelve. La exportación incluye ambos para preservar la huella original. El listado de destinatarios representa elegibilidad al generar, nunca permiso actual de envío.

## Límites

No se envían mensajes ni se programa distribución. Permanecen canales autorizados, comprobación de destinatarios al enviar, programación, suplencias y avisos. La aprobación del informe no cambia tareas, línea base, respuestas, evidencia, aceptación clínica ni cumplimiento normativo. No existe aprobación humana real por usar cuentas sintéticas de prueba.

Se conservan los pendientes institucionales, clínicos y operativos del backlog. Ninguna aplicación ajena del VPS se modifica ni se activa producción.

## Verificación realizada

181 pruebas de regresión aprobadas. Seis casos específicos aprobados de nuevo tras añadir comprobación explícita de que cambiar tareas no modifica el contenido conservado; cubren también revisión independiente, reintentos, permisos/revocación, cuentas técnicas, integridad, rechazo y resolución concurrente. Recorrido de navegador con API real aislada aprobado. Compilación 0.17/TypeScript y OpenAPI sin advertencias. Migración aplicada sólo en base privada por socket Unix, clúster propio detenido al cierre y fuentes originales verificadas por SHA-256.
