# Entrega 0.21 — suplencias integradas con tareas y avisos

Los nombramientos de suplencia vigentes se integran con las tareas del titular y sus avisos internos. El tablero muestra quiénes cubren al responsable y sus fechas. La tarea conserva dueño, línea base y estimación; la suplencia permite actuar con la identidad propia de quien realiza el trabajo.

## Trabajo y revisión independiente

Una persona con suplencia vigente de un rol de trabajo del titular, en el mismo servicio, puede avanzar, bloquear y enviar la tarea a revisión sin ser asignada manualmente como suplente de esa tarea. Se mantienen inicio del plan, fechas, dependencias y control de versión. El evento conserva actor real y los identificadores de nombramientos de cobertura utilizados. La entrega conserva a su autor real en `submitted_by`.

Un suplente vigente del responsable o el suplente explícito de la tarea no puede aceptar ni devolver su cierre, incluso si dispone además de un rol de gestión. Se mantienen también las restricciones del titular y de quien envió la entrega. La revisión debe hacerla otra persona habilitada. Registrar horas sigue atribuyendo el tiempo a quien lo realizó, con los límites existentes; el evento incorpora la cobertura vigente, sin convertir esas horas en trabajo del titular.

Al expirar o revocarse la cobertura se deja de reconocer esa relación para actuar y generar avisos. Los permisos de otros nombramientos independientes mantienen su comportamiento: por ejemplo, una persona con rol gestor independiente puede seguir gestionando el servicio. No se retiran permisos ajenos a la suplencia ni se oculta el historial de actuaciones.

## Avisos internos de tareas

Los recordatorios existentes conservan calendario confirmado, días hábiles, festivos y versión de tarea. Desde el segundo día hábil de atraso se añaden los suplentes vigentes del responsable. Cada persona recibe como máximo una ruta de cobertura por generación; si ya es suplente explícito de la tarea, se conserva esa ruta sin duplicarla. Los destinatarios originales siguen recibiendo sus avisos.

Los cambios aprobados de una predecesora que bloquean o devuelven una tarea también generan avisos para quienes cubren al titular. Estos avisos siguen el comportamiento inmediato de la dependencia, sin esperar el segundo día de atraso.

La cola conserva el nombramiento que motivó el aviso. Antes de entregar se revalidan destinatario, tarea, versión, estado y cobertura concreta, además del acceso actual al servicio. Una persona con otro permiso de lectura no recibe por ello un aviso pendiente de una suplencia revocada. La entrega comparte bloqueo por servicio con las revocaciones administrativas y actuaciones de tarea.

El tablero deja de mostrar los avisos de cobertura cuando esa cobertura deja de ser válida, conservando las filas históricas en base de datos. No puede deshacer la lectura de un aviso ya visto. Las rutas independientes del titular, coordinador y suplente explícito mantienen sus reglas; no se transfieren automáticamente tareas o responsabilidades de coordinación.

## Avisos de decisiones

Quien cubre a la persona solicitante puede ver y acusar los avisos de sus decisiones pendientes dentro del mismo servicio. Se conserva calendario y niveles de aviso. El acuse es personal y registra los nombramientos de cobertura que lo justificaron; no marca lectura al titular ni resuelve la solicitud. Al perder cobertura desaparece esa vía de aviso, salvo que exista otra relación habilitante, como Dirección con acceso vigente.

No se hereda la identidad del solicitante ni el derecho a retirar una decisión en su nombre. Resolver decisiones sigue sujeto a las reglas vigentes de Dirección y revisión independiente. Reaperturas, cambios de calendario y escalamiento conservan las reglas de nuevos acuses; cambiar sólo el nombramiento no borra una lectura previa de la misma persona sobre la misma versión/nivel.

## Datos y operación

Migraciones aditivas 0028 y 0029: referencia opcional de cobertura en `OutboxEvent` e identificadores de cobertura en `DecisionNoticeReceipt`. Eventos antiguos y acuses anteriores conservan valores vacíos. No se modifican titulares ni se duplican estimaciones de carga.

Se utiliza el trabajador interno existente; no se instala ni activa ningún temporizador. No hay envío de correo ni otros canales externos. Los ensayos sólo entregan notificaciones a cuentas sintéticas en recursos propios. La elegibilidad de nombramientos sigue la fecha de permisos del sistema; los vencimientos de tareas y avisos utilizan la fecha local de la sede, como los módulos existentes.

La suplencia autorizada no depende de detectar automáticamente una ausencia: titular y suplente pueden trabajar durante la cobertura. No se reserva capacidad ni se calculan ausencias. Permanecen informes programados, canales externos autorizados, validación institucional y el alcance clínico/administrativo restante.

## Verificación realizada

208 pruebas de backend aprobadas. Ocho casos nuevos cubren trabajo y actor real, expiración/revocación pese a otro permiso, independencia de cierre, duplicados, entrega/ocultación de avisos, dependencias y acuse por cobertura de solicitante. Después del refuerzo final de revalidación de permisos tras bloqueo, se repitieron y aprobaron 19 pruebas de seguimiento/integración. Recorrido de navegador con API real aislada aprobado: ver cobertura, recibir aviso interno y enviar entrega como suplente. Compilación 0.21/TypeScript y OpenAPI sin advertencias; sin migraciones pendientes de generar. Migraciones sólo en base privada por socket Unix, clúster propio detenido al cierre y fuentes originales intactas por SHA-256. Ninguna aplicación ajena del VPS modificada.
