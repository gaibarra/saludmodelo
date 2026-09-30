# Entrega 0.19 — avisos internos de decisiones y acuse personal

La pantalla «Decisiones» incorpora avisos personales de solicitudes pendientes para su autor y para Dirección con acceso vigente al servicio. Se calculan al consultar o actualizar el registro. Marcar como leído sólo registra la lectura de esa persona; no resuelve la decisión, no cambia su versión ni detiene el seguimiento.

## Calendario y escalamiento

Se utiliza el calendario institucional confirmado y la fecha local de la sede. Sin calendario confirmado se explica el requisito y no se calculan avisos. Se excluyen fechas anteriores al inicio del plan, plazos futuros, fines de semana u otros días no laborables y festivos configurados. Una solicitud cerrada no produce aviso activo.

El aviso inicial aparece desde el plazo en día hábil; cambia a recordatorio desde el segundo día hábil posterior al plazo y a escalamiento desde el tercero. Los niveles siguen siendo avisos dentro de la pantalla: no se asignan nuevos responsables ni se envían mensajes. Un día hábil posterior al plazo conserva el nivel inicial hasta alcanzar el segundo. El contador excluye el día del plazo y usa las reglas del calendario de seguimiento existente, incluido su límite de intervalo de 3660 días.

La marca de lectura se vincula a persona, decisión, versión de la decisión, versión del calendario y nivel. Reaperturas, cambios de calendario y nuevos niveles requieren otro acuse. Las marcas previas se conservan en base de datos y auditoría; en pantalla se muestra la correspondiente al aviso actual. El acuse de una persona no oculta ni marca como leído el aviso de otra.

## Permisos y consistencia

Lectura y acuse requieren acceso vigente al servicio; además, debe tratarse de la persona solicitante o Dirección competente. Una cuenta técnica sin ese alcance no obtiene avisos. Un usuario con lectura pero sin esa relación puede consultar el registro de decisiones según sus permisos existentes, sin recibir avisos personales.

El acuse bloquea el servicio y la versión del calendario, vuelve a comprobar el estado y los permisos y rechaza versiones o niveles desactualizados. La restricción de unicidad evita duplicar acuses, también con solicitudes simultáneas. La auditoría se registra una vez. El acuse y las resoluciones utilizan el mismo bloqueo por servicio.

Migración aditiva 0026: `DecisionNoticeReceipt`, relaciones protegidas y unicidad por persona/decisión/versiones/nivel. `GET /api/v1/decisions/services/{service}/` añade `notices`; `POST /api/v1/decisions/{id}/acknowledge/` registra lectura. Respuestas privadas sin caché. Se conserva el límite explícito de 500 decisiones por registro.

## Límites y pendientes

No es una cola de notificaciones ni un envío programado: si nadie abre la pantalla, no se entrega ningún aviso. No se instala trabajador, cron ni servicio nuevo. Correo, otros canales externos, resúmenes programados y configuración institucional de umbrales siguen pendientes. Los avisos de tareas existentes no cambian. Tampoco se asignan suplentes ni se sincronizan ausencias con destinatarios.

Se mantienen validación humana, suplencias, informes programados y los módulos clínicos/administrativos pendientes. Este incremento no completa el alcance clínico ni activa producción.

## Verificación realizada

194 pruebas de backend aprobadas con PostgreSQL real aislado. Seis nuevas cubren acuse personal, no resolución automática, reintentos, concurrencia, calendarios/festivos, escalamiento, reapertura, revocación y roles ajenos. Recorrido de navegador aprobado con avisos, fecha y respuesta de acuse simulados para verificar la interacción de lectura; no acredita una entrega real. Compilación 0.19/TypeScript y OpenAPI sin advertencias; sin migraciones pendientes de generar. 0026 aplicada sólo en base privada por socket Unix y clúster propio detenido al cierre. Fuentes originales intactas por SHA-256.
