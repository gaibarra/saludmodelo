# Entrega 0.18 — retiro y sustitución de informes

En «Informes semanales» una versión conservada puede retirarse sin sustituto o sustituirse por otra versión ya aprobada del mismo servicio y período. Ambas operaciones conservan el contenido, su huella y la resolución histórica. El listado, la consulta y la exportación muestran por separado resolución y disponibilidad: conservado, retirado o sustituido.

## Permisos y recorrido

La persona autora puede retirar su propio borrador mientras continúa pendiente y conserva acceso al servicio. Los demás retiros y todas las sustituciones requieren Dirección dentro del alcance y lectura vigente. No se conceden permisos nuevos a cuentas técnicas. El retiro no necesita una segunda aprobación: Dirección lo registra directamente con fundamento; la aprobación del sustituto sí procede del recorrido independiente existente.

Para sustituir, seleccione otro informe aprobado del mismo período y servicio, todavía conservado. El servidor rechaza destinos ajenos, pendientes, rechazados, retirados o sustituidos y la referencia al propio informe. La interfaz permite consultar después la versión sustituta con sus permisos actuales.

El fundamento, autoría, fecha y referencia al sustituto se conservan en `ReportDisposition`. Cada informe admite una sola disposición definitiva; no hay borrado, reactivación ni edición de su motivo. Un informe sustituto puede retirarse o sustituirse posteriormente; el enlace histórico original se conserva y no se redirige automáticamente. Puede haber varias versiones conservadas del mismo período: no se presume una única versión institucional vigente.

## Consistencia y exportación

La solicitud incluye huella y estado observado del informe original; una sustitución incluye también la huella del destino. Cambios de estado concurrentes generan conflicto y requieren volver a consultar. Las operaciones de revisión y disposición se serializan por servicio. Esto evita aprobar después de un retiro y evita ciclos incluso con sustituciones cruzadas simultáneas.

Repetir exactamente actor, motivo, estado y destino devuelve el resultado histórico sin duplicarlo. Una operación diferente sobre un informe ya retirado o sustituido se rechaza. El retiro no modifica los datos fuente, la aprobación original ni el contenido fijo. La huella del contenido no cubre la disposición; ésta se entrega como metadato de historial y cuenta con evento de auditoría.

Endpoint nuevo: `POST /api/v1/reports/saved/{id}/disposition/`. La consulta/exportación existente incorpora `availability` y `disposition`. Migración aditiva 0025: relación única al informe, relaciones protegidas y restricción contra autorreferencia.

Una copia ya descargada no puede retirarse a distancia. Quien la utilice debe consultar el registro para comprobar disposiciones posteriores. No se envían avisos, no se activa distribución programada y no se atribuye aceptación clínica a una resolución administrativa.

## Pendientes conservados

Programación y envío por canal autorizado, suplencias, avisos, validación institucional y los módulos clínicos/administrativos permanecen abiertos. Esta entrega atiende el retiro/sustitución formal pendiente de 0.17, sin completar el plan maestro ni activar producción.

## Verificación realizada

188 pruebas de backend aprobadas. Siete casos nuevos cubren retiro por autor, permisos/revocación, servicio ajeno, integridad, estado desactualizado, sustitución válida, reintentos, destino retirado, conservación de aprobación y dos carreras concurrentes. Recorrido de navegador aprobado con API real aislada: dos versiones aprobadas, sustitución, consulta del sustituto y retiro posterior con historia visible. Compilación 0.18/TypeScript y OpenAPI sin advertencias. Migración aplicada únicamente en la base privada de desarrollo por socket Unix; clúster propio detenido al cierre. Fuentes originales verificadas por SHA-256.
