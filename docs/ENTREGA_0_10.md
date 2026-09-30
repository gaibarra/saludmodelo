# Entrega 0.10 — entrevista persistente y aclaraciones IA

Se incorpora entrevista guiada por persona y pregunta de servicio, con memoria, edición por apartado, historial y traslado explícito a borrador. **No hubo llamadas reales a proveedores, aprobaciones institucionales ni despliegue.** La evaluación humana de IA y las demás ampliaciones de P06 siguen pendientes.

## Recorrido disponible

Desde una pregunta publicada, abra **Entrevista guiada** e inicie con la ayuda revisada. Los pasos numerados de esa ayuda forman los apartados; se muestran como máximo dos pendientes a la vez. Si la guía no tiene pasos numerados o supera doce, se utiliza la pregunta original completa como un apartado y se conserva la guía íntegra para consulta. No se inventan subpreguntas ni se da por aceptado un formulario institucional a partir de su contenido editorial.

Cada apartado permite declarar información conocida, desconocida, inexistente, por confirmar o considerada no aplicable. Lo conocido requiere texto; no aplicabilidad requiere fundamento. Guardar conserva el avance en el servidor y crea un turno histórico. Los apartados registrados no se preguntan nuevamente en esa entrevista, incluidos los desconocidos: permanecen visibles para corrección, con su estado honesto. «Registrado» y «declarado conocido» se contabilizan por separado; ninguno equivale a validación institucional.

Salir, recargar y abrir de nuevo recupera el avance de esa persona y pregunta. Las respuestas que todavía no se guardaron permanecen sólo en el formulario: no hay guardado automático. Guardar un apartado no borra lo que se está escribiendo en el otro apartado visible. La sección de declaraciones guardadas permite corregir cualquier apartado, añadiendo historia en lugar de sobrescribir los turnos anteriores.

La entrevista es privada para su autor dentro de un servicio con nombramiento de escritura vigente. Otro responsable del servicio inicia su propia entrevista; no recibe la memoria privada del primero. Sólo al trasladarla explícitamente se incorpora el contenido a la respuesta compartida del servicio, bajo los permisos existentes.

## Aclaraciones procedentes de IA

Se pueden incorporar hasta dos aclaraciones de una solicitud IA propia, disponible y de la misma pregunta. Antes de copiarlas, el servidor vuelve a comprobar el contrato, la versión de respuesta, permisos, documentos, vigencia, autorizaciones de salida y citas del resultado. No se acepta un resultado manipulado con citas inventadas.

Las aclaraciones se deduplican por texto normalizado —espacios y mayúsculas—, incluso al incorporar nuevamente una solicitud. No hay deduplicación semántica de paráfrasis ni inferencia automática de datos confirmados a partir de una respuesta libre previa. El límite total es veinte apartados; superarlo se rechaza, sin truncar preguntas silenciosamente. Cada aclaración conserva origen y solicitud de procedencia.

Los datos escritos en la entrevista **no se añaden a las peticiones de proveedores**. El flujo IA existente continúa enviando únicamente pregunta y fragmentos autorizados. Por eso este incremento no equivale a una conversación continua del proveedor con toda la memoria institucional. Si se quiere usar memoria como contexto externo en el futuro, requerirá clasificación, autorización y cambios explícitos del contrato; no se habilitó esa transmisión por conveniencia.

Si se revoca una fuente, cambia una respuesta o deja de estar disponible la solicitud que originó una aclaración, se bloquea el uso de esa memoria IA y no se expone su contenido en la entrevista activa. Puede actualizar contexto para continuar con la ayuda vigente. Las instantáneas históricas siguen conservadas en la base; la API sólo presenta metadatos de esos turnos, no una vía alternativa para leer contenido bloqueado.

## Comparación y traslado a respuesta

Antes de trasladar, compare el editor actual, la respuesta guardada en el servidor y el texto de entrevista. El botón queda deshabilitado mientras hay cambios sin guardar en el editor principal. El servidor exige haber registrado todos los apartados; puede indicar desconocimiento en lugar de inventar datos. La combinación no puede exceder 20000 caracteres.

**Usar entrevista y guardar borrador** reemplaza la respuesta mediante una nueva revisión, conserva las anteriores y mantiene conocimiento `unconfirmed`, aun si todos los apartados fueron declarados conocidos. No envía a revisión ni aprueba respuestas, documentos, normas o actuaciones clínicas. El flujo existente genera el pendiente de confirmación cuando se traslada el borrador; antes de trasladarlo, los pendientes forman parte de la entrevista privada, no de tareas institucionales ya comprometidas.

El turno conserva la referencia a la revisión de respuesta creada. Reintentar la misma operación con su clave no duplica respuesta, turno ni tarea; una nueva acción de traslado de la misma versión de entrevista ya aplicada se rechaza. Un uso posterior requiere editar la entrevista y volver a comparar.

## Versiones y contexto

Cada escritura exige versión de entrevista, versión de respuesta y clave de idempotencia. El bloqueo de la instancia serializa inicio y traslado; se vuelve a comprobar permiso tras obtenerlo. Un conflicto responde 409 y no borra lo guardado ni sustituye una respuesta más nueva.

Cambiar la respuesta —incluida una carga documental que cambia su versión de concurrencia— o publicar otra ayuda deja la entrevista pendiente de actualización de contexto. Al actualizar se conserva el texto de pasos de ayuda que coincidan, pero vuelve a pedirse confirmación; las aclaraciones IA previas no se trasladan automáticamente al contexto nuevo. El historial anterior se conserva con su ayuda, versión de respuesta y datos de ese turno. Si se trasladó una entrevista con aclaraciones IA, la nueva versión de respuesta puede hacer que la solicitud origen deje de ser compatible; se requiere actualizar contexto para seguir utilizándola.

No se usa la antigüedad de la pantalla para decidir qué versión prevalece. La respuesta actual del servidor aparece en la comparación. La entrevista no resuelve automáticamente discrepancias entre colaboradores ni sustituye la gestión pendiente de cambios de alcance/fuente institucional.

## Implementación y límites

Migración aditiva `0016_interview_interviewturn_and_more`: una entrevista por propietario e instancia, turnos históricos con versión/clave únicas, vínculo a ayuda y revisión aplicada. Endpoint privado `/api/v1/interviews/{instance}/`, protegido por MFA y alcance de escritura, sin caché compartida. Acciones: `open`, `reply`, `add_ai`, `rebase`, `apply`; campos cerrados por acción.

Hasta doce pasos iniciales, veinte apartados incluyendo aclaraciones IA, dos pendientes visibles, 2000 caracteres por declaración y 20000 en el traslado. La interfaz muestra los últimos cien turnos; los anteriores permanecen en la base. Confirmar un apartado sólo declara conocimiento del autor, no acredita revisión competente.

Pendientes de P06: evaluación humana sobre corpus institucional autorizado, claridad/fidelidad/utilidad por servicio, acciones IA adicionales, memoria autorizada para nuevas preguntas del proveedor, edición de propuestas IA por campos tipados más allá del texto de respuesta, manejo progresivo de reintentos y soporte de paráfrasis. La funcionalidad actual no demuestra exactitud clínica ni «sin dudas» con personas reales.

## Pruebas ejecutadas

- Once pruebas iniciales de entrevista aprobadas; regresión de **126 pruebas Django** aprobada. Después, **doce pruebas finales de entrevista**, incluida concurrencia real de inicio y traslado idempotentes, aprobadas. Total actual descubierto: 127; no se afirma una ejecución conjunta posterior de esas 127.
- **Seis recorridos Playwright aprobados** en una ejecución: administración, móvil, cumplimiento, seguimiento, MFA y entrevista. El nuevo recorrido prueba persistencia al recargar, conservación de otro apartado en edición, dos pendientes visibles y traslado sólo a borrador.
- **Ocho pruebas de recuperación aprobadas**, ahora incluyendo memoria e historial de entrevista junto con permisos y MFA. Ensayo sintético: 60 tablas, 345 filas, un adjunto, 2.562 segundos. No demuestra RPO/RTO de producción; informe actual en `recovery-test-report.json`.
- OpenAPI validado sin advertencias, migración aplicada sólo al PostgreSQL privado y sin cambios de modelo pendientes. Compilación final Next.js/TypeScript 0.10 comprobada.

Las pruebas IA usaron dobles y fragmentos sintéticos. Las cuentas, claves, permisos y decisiones de navegador/restauración son de ensayo. Las fuentes originales se conservan y ninguna aplicación existente del VPS fue modificada.
