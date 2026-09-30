# Entrega 0.24 — distribución interna y constancia de lectura

El recorrido de informes permite ahora seleccionar destinatarios, distribuir una versión aprobada en sus bandejas internas y registrar un acuse personal. Dirección puede consultar entregas y lecturas. No se manda correo ni se activa otro canal externo.

## Distribución explícita

Dirección necesita lectura vigente del servicio y autoridad dentro de su alcance. Sólo puede distribuir un informe aprobado, conservado y cuya huella coincide con la versión consultada. Se comprueba su integridad y se bloquea distribución si fue retirado o sustituido.

Se seleccionan entre uno y cien destinatarios por operación, sin selección automática. Todos deben tener cuenta activa y lectura vigente en el mismo servicio; el listado se calcula al consultar y se vuelve a comprobar al distribuir. Si cualquiera resulta inválido, no se entrega a nadie de ese lote. El motivo es obligatorio. No se usa el listado histórico de elegibilidad del contenido como autorización actual.

La entrega interna es inmediata y transaccional: crea una referencia en la bandeja, sin copiar el contenido ni conceder permisos nuevos. Se conservan remitente, destinatario, motivo, fecha y auditoría. La unicidad por informe/persona evita duplicados concurrentes y de reintento. Repetir una entrega conserva el primer remitente y motivo, sin reemplazarlos.

## Bandeja y acuse

«Mis informes recibidos» muestra sólo entregas de la cuenta actual para servicios a los que aún tiene lectura. Abrir un informe no lo marca como leído. Después de consultar el contenido, la persona puede confirmar expresamente su lectura; la fecha se registra una sola vez y el acuse no puede hacerse por otro destinatario.

El acuse vuelve a verificar permisos, huella, integridad y estado aprobado/conservado. Un retiro o sustitución queda visible en la bandeja como historia y bloquea acuses nuevos. La pérdida de acceso oculta la entrega y deniega la consulta, sin borrar los registros históricos. Una lectura ya registrada no se elimina tras el retiro y no acredita aceptación clínica ni conformidad con el contenido.

La consulta/exportación del informe incluye contadores actuales de distribución y lectura fuera del contenido fijo. El campo histórico `delivery: not_sent` del contenido describe el momento de generación; no se reescribe ni altera su huella. La interfaz aclara que la lista de elegibles del informe tampoco acredita distribución actual.

## API y límites

- `GET/POST /api/v1/reports/saved/{id}/distribution/`: Dirección consulta destinatarios y lecturas o distribuye explícitamente.
- `GET /api/v1/reports/inbox/`: bandeja personal con permisos actuales.
- `POST /api/v1/reports/deliveries/{id}/acknowledge/`: acuse personal ligado a huella.

Migración aditiva 0032, modelo `ReportDelivery` con relaciones protegidas y unicidad informe/destinatario. Operaciones de distribución, retiro y acuse comparten bloqueo de servicio. Cuentas seleccionadas se bloquean en orden estable para verificar su estado. Las consultas rechazan más de 500 registros; ampliación de paginación pendiente. Respuestas privadas sin caché.

No hay distribución automática al aprobar, programar o recuperar un informe. Tampoco se redirige la entrega a suplentes automáticamente: Dirección selecciona las cuentas concretas y se verifican sus nombramientos. La entrega interna no demuestra recepción fuera de la aplicación ni lectura efectiva más allá del acuse declarado.

## Cierre operativo y pendientes

Se preparó `CIERRE_PILOTO_GESTOR.md` con recorrido, condiciones de aceptación y dependencias institucionales/operativas. Servicio y responsable de validación se solicitaron al usuario; no se inventaron. El piloto sigue pendiente de selección, contenido revisado, usuarios y ejecución humana.

Permanecen distribución por canales externos autorizados, despliegue/temporizadores, recuperación de producción, ampliaciones del gestor y todos los módulos clínicos/administrativos no implementados. La distribución se ensaya sólo con cuentas sintéticas en recursos aislados. No se modifican otras aplicaciones del VPS.

## Verificación técnica

- Regresión completa del servidor: 227 pruebas aprobadas. Tras reforzar el control de cuenta activa, se repitieron las seis pruebas de distribución, incluyendo desactivación y revocación de permisos; todas aprobadas.
- Navegador: la corrida general aprobó 19 de 21 recorridos; dos expectativas antiguas (texto histórico de destinatarios y versión fija de programación) se actualizaron. La repetición descubrió una respuesta tardía de carga que podía restablecer el checkbox de programación; se corrigió ignorando efectos cancelados. Los cuatro recorridos relacionados pasaron posteriormente: informe local, habilitar/pausar programación, recuperación y distribución/lectura. La recuperación usa respuesta simulada en navegador; los otros tres usan API real aislada.
- Compilación final 0.24 y TypeScript aprobados tras corregir la carga de programación. OpenAPI validado sin advertencias y sin migraciones pendientes de generar. Migración 0032 aplicada sólo en la base privada del proyecto por socket Unix; clúster detenido al finalizar.
- SHA-256 de DOCX y prompt coincide con los originales conservados. Sin llamadas a proveedores, mensajes externos, instalación de temporizadores ni modificación de otras aplicaciones del VPS.
