# Entrega 0.15 — registro de decisiones por servicio

La pantalla «Decisiones» permite registrar solicitudes para Dirección, alternativas conocidas, plazo interno y una tarea relacionada opcional. La resolución se registra con fundamento y conserva historia; no ejecuta cambios de tareas, presupuestos, fechas, línea base, respuestas ni aprobaciones clínicas.

## Recorrido y permisos

Personas con permiso vigente de trabajo en el servicio y Dirección pueden solicitar una decisión. Toda lectura requiere asignación vigente al servicio; un privilegio técnico o mandato institucional sin ese alcance no basta. Dirección dentro de su alcance puede resolver o descartar solicitudes de otra persona. Se impide resolver la propia solicitud. La persona solicitante puede retirarla; Dirección también puede retirarla o reabrir una solicitud cerrada.

La tarea relacionada debe pertenecer al mismo servicio. Se conserva su título, estado y versión al solicitar, y se muestra el contexto actual. Al cerrar una solicitud vinculada, el servidor verifica la versión actual que vio la persona: si la tarea cambió, devuelve conflicto para recargar y comparar. Una decisión resuelta no compromete automáticamente la tarea.

Cada operación requiere fundamento y conserva un evento con versión y fotografía del estado. Reabrir restablece el estado pendiente sin borrar la resolución previa del historial. No hay endpoint de eliminación. Título, pregunta, alternativas, plazo y vínculo inicial se conservan; las correcciones sustantivas pueden documentarse retirando la solicitud y creando otra. Edición versionada de esos campos y reasignación individual permanecen pendientes.

Plazo mínimo: 1 de octubre de 2026, conforme al inicio del plan; no representa un plazo legal. El registro es por servicio y no asigna automáticamente un decisor individual ni envía notificaciones.

## API y concurrencia

- `/api/v1/decisions/services/{service}/`: consultar registro o crear solicitud.
- `/api/v1/decisions/{id}/`: consultar historia y contexto; registrar `resolve`, `dismiss`, `withdraw` o `reopen`.

Claves de reintento por servicio/persona y huella del contenido impiden duplicar operaciones. Repetir la misma clave con otro contenido se rechaza; un reintento válido devuelve el estado actual sin repetir la operación histórica. Versiones optimistas y bloqueo por servicio serializan cambios; las comprobaciones de permiso se repiten dentro de la transacción. La interfaz conserva la clave al fallar una recarga posterior al guardado.

Migración 0022 aditiva: `Decision` y `DecisionEvent`, relaciones protegidas, unicidad de operación y de versión, fecha mínima del plan. La consulta del registro limita a 500 decisiones con rechazo explícito al excederlas; no descarta silenciosamente registros. La paginación ampliada sigue pendiente. No se concede acceso adicional a IA.

## Integración con informes

El informe semanal local incorpora solicitudes de decisión actualmente pendientes y movimientos del período: solicitud, resolución, descarte, retiro y reapertura. Conserva por separado cambios de línea base y decisiones de este registro. Los movimientos se exportan con identificadores, fechas y versiones; no se exportan fundamentos libres en el informe semanal. La pantalla de decisiones permite consultar el historial completo con permisos.

La sección pendiente muestra estado actual, aunque el período consultado sea pasado. No se reconstruye un cierre histórico ni se asegura que todas las decisiones institucionales estén registradas.

## Validación y límites

Pruebas cubren resolución independiente, reapertura e historial, reintentos, rechazo de claves reutilizadas, concurrencia, roles revocados, servicio ajeno, cuenta técnica, fechas y campos obligatorios, tarea ajena o modificada, retirada sin borrado y ausencia de cambios automáticos. Se prueba también su inclusión en el informe semanal. El navegador recorre solicitud por responsable, resolución por Dirección, reapertura e informe usando API real en recursos temporales propios.

Continúan capacidad y ausencias institucionales, suplencias ampliadas, avisos de decisiones, aprobación/envío de informes, validación de fichas, evaluación humana de IA, módulos clínicos/administrativos y operación de producción. No se activaron servicios ni se modificaron aplicaciones ajenas del VPS.

Resultado técnico: 166 pruebas de backend aprobadas, un nuevo recorrido de navegador aprobado, compilación 0.15/TypeScript correcta y OpenAPI validado sin advertencias. Migración aplicada sólo en la base privada de desarrollo; clúster propio detenido al cierre.
