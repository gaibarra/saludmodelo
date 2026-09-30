# Operación y recuperación

## Uso por función

- Colaborador: ingresar, seleccionar servicio, contestar o indicar desconocimiento, guardar, adjuntar declaración TXT y enviar a revisión. El mensaje Guardado confirmado acredita respuesta del servidor. No hay guardado automático todavía.
- Revisor de servicio: revisar respuesta e historial, registrar fundamento y validar o devolver. El servidor rechaza aprobación propia o falta de permiso vigente. La validación de respuesta no representa cumplimiento normativo.
- Dirección institucional: entrar a Administración y cuestionarios. Crear campus/sedes/servicios, confirmar alcance, registrar cuentas y aprobar nombramientos con fechas y fundamento. Revocar con motivo conserva el historial. Consultar indicadores agregados de su alcance; el mandato no da acceso automático a respuestas detalladas. La captura y revisión requieren nombramientos de servicio, sin autoasignación.
- Autor de ayuda: seleccionar Cuestionarios y ayudas y su servicio; completar los diez apartados y guardar un borrador. Puede retomar una ficha incompleta. Las versiones y observaciones se conservan.
- Revisor de ayuda: comprobar significado, fuentes, ejemplo ficticio, evidencia, suficiencia y vía de consulta. Aprobar o devolver con fundamento. Una persona distinta del autor debe revisar. La publicación requiere cobertura de ayuda completa en el alcance del servicio. Publicar una corrección exige volver a revisar las respuestas afectadas.
- Auditor: consulta dentro de su alcance; la descarga vuelve a comprobar autorización.
- TI/desarrollador: ningún acceso de producto a respuestas por ese rol. La importación se realiza por operador bootstrap autorizado. El acceso excepcional de infraestructura se gestiona fuera de la aplicación y requiere controles institucionales.

Las preguntas se habilitan sólo mediante publicación explícita con ayuda revisada. No introducir datos reales sensibles en esta entrega en desarrollo.

## Despliegue pendiente

Las plantillas de `deploy/` requieren usuario de sistema dedicado, instalación en `/opt/salud-modelo`, PostgreSQL con credenciales propias en loopback, directorio privado `/var/lib/salud-modelo/private`, archivo de entorno modo 600 y revisión institucional. No se instalaron en el sistema. Verificar dependencias, configurar TLS y probar `certbot renew --dry-run` después de disponer de dominio y DNS. MFA está implementado en 0.9; su configuración de clave y alta institucional, monitoreo y endurecimiento restante siguen siendo requisitos previos de producción.

## Recuperación: ensayo local implementado, producción pendiente

Herramientas y ensayo disponibles en [RECUPERACION.md](RECUPERACION.md). El ensayo sintético conserva base, documentos, versiones y permisos; no configura copia externa ni demuestra RPO/RTO reales.

1. Configurar respaldos cifrados de base y documentos fuera del VPS. Seleccionar herramienta y custodia de claves aprobadas; no hay plazo universal de retención.
2. Definir estrategia PITR/WAL y periodicidad coherente con RPO de una hora.
3. Restaurar en entorno aislado; verificar revisiones, fuentes, archivos por hash, roles, alcance, outbox y pendientes.
4. Medir pérdida de datos y duración; contrastar con RPO 1 h / RTO 4 h. No están demostrados.
5. Antes de migraciones reales, revisar SQL y respaldo. Una reversión conserva y concilia registros creados después del corte; nunca sustituir la base activa por una copia antigua sin conciliación.

Las pruebas locales utilizan un clúster temporal propio y no constituyen ensayo de recuperación de producción.

## Borradores y consultas (0.3)

En la ficha, «Comparar borrador de la fuente» muestra los diez apartados propuestos frente al texto del editor y sus referencias. «Usar propuesta en el editor» reemplaza explícitamente el texto local; revise y adapte antes de guardar. El estado continúa en borrador hasta revisión independiente y publicación. Un inventario incompatible permite seguir redactando manualmente.

Desde una ficha o respuesta, abra «Consultas privadas». Seleccione a otra persona con permiso de revisión, describa la duda y elija fecha esperada. La persona asignada puede responder desde `/consultas`; quien inició puede pedir más aclaraciones o marcar la duda resuelta con un fundamento. La consulta conserva las versiones de contexto sin aprobar el contenido del cuestionario. Si aparece un conflicto, el texto escrito permanece: actualice las consultas, compare y vuelva a enviar. Al perder acceso vigente al servicio se pierde el acceso a la consulta.

## Documentos TXT/CSV (0.4)

Adjunte el documento después de guardar la respuesta como borrador. El CSV debe estar en UTF-8 con coma como separador; puede contener campos entre comillas y saltos de línea. Las fórmulas se muestran literalmente. El original conserva su huella y versión de respuesta. Para un documento corregido, adjunte otro archivo; no se reemplaza el historial.

El operador ejecuta `backend/.venv/bin/python backend/manage.py extract_evidence` con las variables de la base propia. Cada ejecución procesa como máximo cien trabajos. Un fallo deja el original disponible y un estado explícito. La interfaz permite reintentar hasta el máximo de tres intentos; no hay bucles indefinidos ni extracción parcial aceptada. La recuperación de un proceso interrumpido ocurre al expirar el arrendamiento de sesenta segundos y ejecutar nuevamente el trabajador.

«Ver texto y revisión» presenta líneas o filas y celdas, con cincuenta fragmentos por página. Compare el texto con el original. Un revisor distinto de cargador y autor puede aceptar con fundamento y fecha de vigencia o devolver. «Actualizar documento» permite comparar tras un conflicto sin borrar el fundamento escrito. La ficha identifica si venció la vigencia o si el archivo pertenece a una versión anterior de respuesta. Estas decisiones no validan respuestas ni obligaciones normativas automáticamente.

Los límites de proceso son una defensa de recursos para texto inerte; no sustituyen confinamiento ni antivirus. PDF, Office e imágenes siguen bloqueados. Las plantillas de servicios permanecen sin instalar.

## Matriz de cumplimiento (0.7)

Desde **Cumplimiento**, seleccione el servicio. Un responsable (`manager`) o una persona de cumplimiento prepara norma/numeral, control, proceso, pregunta, supuesto, fuente consultada, responsable y evidencia de la respuesta actual. Guardar crea un borrador versionado; no significa que la norma esté vigente o que la institución cumpla.

El responsable, cumplimiento o supervisión clínica registra procedimiento de prueba, resultado esperado y observado. Otra persona con rol `compliance` aprueba o devuelve con fundamento. No puede aprobar la versión que escribió ni la prueba que ejecutó. Revise los pendientes visibles: cambios de respuesta, evidencia vencida, nuevos resultados o fechas vencidas requieren nueva revisión. El historial conserva las decisiones previas.

La exportación JSON está limitada al servicio autorizado y registra la descarga en auditoría. Las fechas de consulta reflejan la consulta efectuada; la próxima revisión no puede programarse antes del 1 de octubre de 2026 ni quedar vencida. Consulte `ENTREGA_0_7.md` para límites y evidencias de prueba.

Para incorporar el catálogo N01–N60 a un lote ya importado, el operador autorizado repite la orden `import_plan` con el mismo DOCX, su huella aprobada y su usuario de importación; primero ejecute la vista previa sin `--approve-sha`. La conciliación agrega filas normativas faltantes y conserva fuentes originales. No cambie permisos de catálogo ni atribuya vigencia para resolver una pantalla vacía; compruebe el lote y su autorización institucional.

## Seguimiento y calendario (0.8)

En **Seguimiento**, elija un servicio de su nombramiento. Un responsable o coordinador prepara una tarea con fechas, criterios y predecesoras. Después solicita su incorporación a línea base. Otra persona de Dirección, con alcance del servicio, aprueba o rechaza. La tarea propuesta no permite registrar avance de estado hasta que exista compromiso aprobado y llegue su inicio.

El responsable, suplente o responsable autorizado informa avance o bloqueo y envía la entrega con su resultado. Otra persona responsable o de Dirección coteja los criterios y acepta o devuelve. Si necesita cambiar o cancelar un compromiso, proponga otro cambio con fundamento; no borre el registro. Una predecesora modificada provoca revisión de sus sucesoras afectadas.

Para tiempo real, indique fecha desde el 1 de octubre de 2026, minutos y una descripción. Un reintento con la misma clave no duplica horas. No use este registro para simular tiempo futuro. La corrección de registros históricos aún requiere el procedimiento pendiente.

Dirección con mandato institucional confirma días y fechas no laborables para habilitar avisos. Los avisos se consultan dentro del servicio y vuelven a comprobar los permisos; no se envía correo. El despliegue autorizado puede invocar `python backend/manage.py tracking_reminders` y después `python backend/manage.py worker`; aquí sólo se ejecutaron contra bases sintéticas privadas. Conservar el resto de comandos del trabajador. No instalar la plantilla sin revisión y autorización de despliegue.

La capacidad 354 horas es una referencia para toda la institución, no para cada servicio. Los pendientes de aceptación de procesos, reserva y ampliaciones se detallan en `ENTREGA_0_8.md`.


## MFA y seguridad de la cuenta (0.9)

Los perfiles privilegiados deben completar autenticación en dos pasos antes de consultar datos. Use Seguridad de la cuenta para activar o reemplazar el autenticador y guardar códigos de recuperación. Consulte [ENTREGA_0_9.md](ENTREGA_0_9.md) para operación, vigencias, bloqueo de intentos, custodia de clave y recuperación. No se activó MFA para personas reales ni se habilitó despliegue.


## Monitoreo y señal del trabajador

Consulte [MONITOREO.md](MONITOREO.md) para `monitor_health`, códigos de salida, umbrales y alertas privadas. Los componentes no configurados aparecen como desconocidos. `worker_cycle` ejecuta los cuatro comandos existentes y registra inicio/resultado; debe usarse sólo para procesar el trabajo del proyecto autorizado. Las plantillas actualizadas y el nuevo temporizador no están instalados. Faltan supervisión externa, agregación de errores web y canal de aviso autorizado.


## Entrevista guiada (0.10)

Abra Entrevista guiada desde la pregunta, inicie con la ayuda revisada y guarde cada apartado; se presentan hasta dos pendientes a la vez. Puede salir y retomar lo guardado, corregir declaraciones e incorporar aclaraciones IA disponibles. La entrevista es privada del autor y no envía sus textos a proveedores. Antes de trasladarla compare editor, respuesta vigente y entrevista; el traslado crea borrador por confirmar. Si cambia el contexto, actualícelo y reconfirme. Ver [ENTREGA_0_10.md](ENTREGA_0_10.md).


Acciones IA (0.11): aplicar la migración 0017 únicamente en un entorno propio autorizado. Las políticas anteriores conservan sólo `suggest`. Habilitar otras acciones requiere editar la política del servicio; para modelo por acción consultar [ENTREGA_0_11.md](ENTREGA_0_11.md). No hay envío de texto de respuesta ni memoria de entrevista.


Revisión de respuestas (0.12): migración aditiva 0018 y acción `review`, deshabilitada en políticas anteriores. Requiere autorización independiente del texto guardado por proveedor y vencimiento, y confirmación del envío. Cambios del etag exigen nueva autorización. Sólo esta acción incluye texto de respuesta; ver [ENTREGA_0_12.md](ENTREGA_0_12.md).


Comparación de fuentes (0.13): migración 0019; habilitar `contradictions` expresamente en la política sólo cuando corresponda. Requiere dos fragmentos distintos autorizados, no envía respuesta ni memoria y no resuelve conflictos automáticamente. Ver [ENTREGA_0_13.md](ENTREGA_0_13.md).


Informes y guía (0.14): migraciones 0020/0021. La nueva acción `report` requiere política explícita; las autorizaciones de respuestas anteriores conservan finalidad `review`. Para guía con antecedente se necesita nueva autorización `interview` y confirmación de envío. El informe semanal es local, de sólo lectura y sin mensajería; la exportación se recalcula y audita. Ver [ENTREGA_0_14.md](ENTREGA_0_14.md).


Decisiones (0.15): migración aditiva 0022, pantalla `/decisiones` y registro por servicio. Requiere permisos de servicio vigentes; resolución por otra persona de Dirección. Resolver no ejecuta cambios de línea base ni tareas. Ver [ENTREGA_0_15.md](ENTREGA_0_15.md).

Capacidad (0.16): migración aditiva 0023 y pantalla `/capacidad`, sólo para mandatos institucionales vigentes. Requiere dos personas distintas para proponer/aprobar. Capturar minutos explícitos; una propuesta pendiente no acredita disponibilidad. La pérdida de nombramiento exige revisión y, si procede, nueva propuesta cero. No registrar motivos médicos. Ver [ENTREGA_0_16.md](ENTREGA_0_16.md).

Informes conservados (0.17): migración aditiva 0024 y sección en `/reportes`. Guardar genera una nueva instantánea fija; revisar su contenido antes de aprobar. Otra persona de Dirección con acceso al servicio registra la resolución. No hay envío ni programación, y no se retiran resoluciones anteriores automáticamente. Ver [ENTREGA_0_17.md](ENTREGA_0_17.md).

Informes (0.18): migración 0025 añade retiro/sustitución definitivos, sin borrar contenido ni aprobación. La persona autora puede retirar su borrador pendiente; demás casos requieren Dirección con acceso vigente. Un sustituto debe estar aprobado y conservado dentro del mismo servicio/período. Ver [ENTREGA_0_18.md](ENTREGA_0_18.md). Consultar el estado actual antes de reutilizar exportaciones históricas.

Avisos de decisiones (0.19): migración aditiva 0026. Se calculan al consultar `/decisiones` usando calendario confirmado y fecha local de sede. El acuse no resuelve ni desactiva escalamiento. Sin procesos nuevos ni envíos; ver [ENTREGA_0_19.md](ENTREGA_0_19.md).

Suplencias (0.20): migración aditiva 0027. En administración seleccione titular, otra persona, mismo servicio/rol y vigencia incluida. Revocar el titular revoca sus suplencias; no elimina otros permisos independientes. No basta desactivar técnicamente la cuenta titular para retirar coberturas autorizadas. Ver [ENTREGA_0_20.md](ENTREGA_0_20.md).

Integración de suplencias (0.21): aplicar 0028–0029. El tablero muestra coberturas vigentes; los suplentes trabajan con identidad propia y no aceptan cierres de tareas cubiertas. Avisos de atraso desde segundo día hábil y por dependencias usan la cola existente, con revalidación de cobertura al entregar. Avisos de decisiones se calculan al consultar. No se instala temporizador ni canal externo. Ver [ENTREGA_0_21.md](ENTREGA_0_21.md).

Programación de informes (0.22): migración 0030; configuración por Dirección en `/reportes`. `scheduled_reports` se incorpora al ciclo existente para generar la última semana completa elegible, sin aprobar ni enviar. Sólo operar sobre recursos propios y activar temporizadores tras configuración/autorización de producción. Último estado y últimas veinte generaciones visibles por servicio. Ver [ENTREGA_0_22.md](ENTREGA_0_22.md).

Recuperación semanal (0.23): migración 0031. Dirección puede solicitar una semana completa por operación desde `/reportes`, incluso con programación pausada, indicando motivo y versión vigente. No reemplaza ejecuciones existentes ni reconstruye cierre histórico. Ver [ENTREGA_0_23.md](ENTREGA_0_23.md).

Distribución interna (0.24): migración 0032. Dirección selecciona destinatarios actuales para un informe aprobado; entrega inmediata en bandeja y acuse expreso personal. No necesita un canal externo ni activa temporizadores. Retiro/sustitución y revocación se comprueban al operar. Ver [ENTREGA_0_24.md](ENTREGA_0_24.md) y [cierre del piloto](CIERRE_PILOTO_GESTOR.md).

Paginación de informes (0.25): desplegar frontend y API juntos porque la bandeja devuelve `results` y `next_before`. Sin nueva migración. Consultas de distribución con cursores independientes para personas y entregas. Ver [ENTREGA_0_25.md](ENTREGA_0_25.md).

Corrección de horas (0.26): migración aditiva 0033; publicar API e interfaz juntas. Los registros originales no se reescriben. Los informes conservados requieren generar otra versión para reflejar ajustes y revisión/sustitución explícita si procede. Ver [ENTREGA_0_26.md](ENTREGA_0_26.md).

Planificación con capacidad (0.27): nueva consulta de sólo lectura en Seguimiento. Confirmar calendario y aprobar capacidad/distribución; sin esos datos muestra información faltante. Actualizar comparación después de cambios aprobados. No requiere migración ni instala trabajadores. Ver [ENTREGA_0_27.md](ENTREGA_0_27.md).

Controles de cierre (0.28): migraciones 0034–0036. Regularizar reservas de tareas existentes antes de activar control obligatorio desde Capacidad; presupuestos introducidos explícitamente por mandato institucional. Ausencias aprobadas conservan compromisos y exponen conflictos para resolución. Los envíos externos y despliegue siguen sin activar. Ver ENTREGA_0_28.md y REUNION_CIERRE_2026_09_29.md.
