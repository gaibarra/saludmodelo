# Entrega 0.30 — recuperación excepcional de autenticador

Permite tramitar la pérdida del autenticador y de todos los códigos de recuperación de una cuenta institucional elegible. Dos responsables institucionales distintos verifican la identidad y dejan referencias de sus comprobaciones. La aprobación invalida los medios MFA anteriores y produce un código temporal que sólo permite iniciar la configuración de un nuevo autenticador. El titular conserva la obligación de conocer su contraseña y confirmar el nuevo segundo factor antes de acceder al trabajo.

## Recorrido en la aplicación

1. Un responsable con mandato institucional vigente entra en Seguridad → Recuperación excepcional de acceso. Consulta las solicitudes e indica institución, nombre de usuario, motivo y referencia de la verificación de identidad.
2. Otra persona con mandato de la misma institución revisa el caso. Debe ser distinta del solicitante y del titular. Registra su comprobación independiente y aprueba o rechaza. Ambos responsables necesitan MFA verificado en los últimos diez minutos al realizar su intervención, incluso si el entorno no exige MFA al resto de usuarios.
3. Al aprobar, la pantalla muestra una sola vez un código excepcional válido durante treinta minutos. No se envía automáticamente. Su entrega al titular corresponde al procedimiento seguro que apruebe la institución. No debe incluirse en motivos, capturas, documentos compartidos ni conversaciones de soporte.
4. El titular ingresa con su contraseña, canjea el código excepcional y configura un nuevo autenticador en esa misma sesión. Hasta confirmar el nuevo código TOTP, no obtiene acceso a servicios ni al gestor. La sesión parcial de autenticación conserva el límite de diez minutos del flujo MFA existente.
5. La solicitud registra el canje y después la finalización de la configuración. Se entregan nuevos códigos personales de recuperación por el flujo habitual. El historial muestra solicitante, revisor, motivos, referencias y fechas; nunca muestra el código temporal ni su hash.

La consulta pagina cincuenta solicitudes por vez sin corte total. Los motivos deben contener referencias a la verificación realizada, no copias de identificaciones ni contraseñas. La aplicación registra la declaración de los responsables; no verifica por sí sola la identidad física de una persona.

## Controles de seguridad

- Deshabilitado por defecto mediante `EXCEPTIONAL_MFA_RECOVERY_ENABLED=0`. Requiere configuración explícita y procedimiento institucional antes del uso real. Las pruebas lo habilitan únicamente en entornos efímeros sintéticos.
- Mandato institucional, cuenta activa y MFA vigente para quienes intervienen. Un rol de Dirección limitado al servicio, por sí solo, no permite recuperar una cuenta global.
- Sólo cuentas activas adscritas exclusivamente a una institución. Se consideran membresías y el historial de mandatos/nombramientos para evitar recuperar una cuenta compartida desde una sola institución. Cuentas de personal técnico/desarrollo, staff o superusuario quedan excluidas y requieren un procedimiento aparte.
- El titular no puede solicitar ni decidir su propia recuperación. El solicitante no puede aprobarla ni rechazarla. Una revocación puede realizarla un responsable institucional autorizado distinto del titular.
- La propuesta vence en veinticuatro horas. La aprobación requiere que la generación del MFA del titular siga siendo la observada y que la autoridad/MFA del solicitante siga vigente.
- El código temporal tiene entropía aleatoria y se almacena sólo como hash. Es de un uso, está vinculado al titular y vence a los treinta minutos. Se exige la contraseña del titular y se mantienen los límites de intentos y bloqueo MFA existentes.
- Canje y finalización vuelven a verificar la elegibilidad de la cuenta y la autoridad/generación MFA de ambos responsables. Una pérdida de autoridad o cambio de autenticador impide completar el procedimiento anterior.
- Al aprobar se invalidan autenticador, códigos de recuperación, configuración pendiente y verificaciones anteriores de sesiones. Una bandera de recuperación impide que una cuenta normalmente no privilegiada recupere acceso sin terminar el nuevo MFA.
- El permiso de reinscripción queda vinculado mediante un nonce a la sesión que canjeó el código; otra sesión no puede usarlo. La configuración conserva su vencimiento y protección contra repetición TOTP habituales.
- Se puede revocar una autorización aprobada o una reinscripción aún pendiente. La revocación no restaura los medios anteriores ni deja la cuenta sin protección. Una recuperación completada no se revoca por este flujo: requiere evaluar un nuevo incidente.
- Bloqueo por usuario del titular compatible con las operaciones MFA existentes. Aprobaciones concurrentes o canjes simultáneos no producen dos autorizaciones utilizables. La clave de solicitud evita duplicaciones; una aprobación repetida nunca devuelve nuevamente el secreto.

## Pérdida del código, de la sesión o de la respuesta de aprobación

El código no se puede consultar después de la respuesta original. Si no se pudo guardar o entregar, se revoca la autorización y se tramita otra solicitud con revisión independiente. Si se pierde o vence la sesión después del canje, también se requiere una nueva autorización. No hay un camino alternativo que omita la contraseña, el nuevo autenticador o la revisión institucional.

## Alcance y pendientes

Este incremento recupera el segundo factor de cuentas elegibles; no restablece contraseñas olvidadas, desbloquea cuentas desactivadas, concede roles, recupera cuentas técnicas o compartidas entre instituciones ni resuelve la pérdida de la clave de cifrado del servidor. Si no existen dos responsables institucionales habilitados, no ofrece un bypass. Estos casos excepcionales siguen requiriendo un procedimiento del operador y desarrollo/validación específico.

Antes de habilitarlo deben acordarse las comprobaciones de identidad, custodia de las referencias, responsables y medio seguro de entrega. No se ha habilitado en producción ni se han enviado códigos reales o mensajes externos.

Migración aditiva `0038_exceptional_mfa_recovery`: solicitudes de recuperación y estado de reinscripción en MFADevice. Las cuentas existentes mantienen sus valores por defecto; generar/aplicar la migración no inicia recuperaciones. API e interfaz deben publicarse juntas en el entorno autorizado.

API: `GET/POST /api/v1/security/recoveries/`, `POST /api/v1/security/recoveries/{id}/review/` y acción `recover` del endpoint MFA existente. Solicitudes/revisiones tienen referencias y motivo obligatorios; los secretos no se incluyen en la consulta histórica.


## Verificación

Regresión completa: **284 pruebas aprobadas**, incluyendo dieciocho nuevas del procedimiento excepcional. Tras reforzar la exclusión de cuentas técnicas por nombramiento, se repitieron las 32 pruebas del área MFA y aprobaron. Cubren reinscripción obligatoria, sesiones previas, códigos vencidos/de un uso, concurrencia, mandatos revocados, alcance institucional, rechazo/revocación, historial y finalización.

Dos recorridos de navegador con API real aprobaron en la versión final: MFA habitual y recuperación excepcional completa. Build 0.30/TypeScript, comprobación Django, ausencia de migraciones pendientes de generar y OpenAPI sin advertencias, correctos. Durante la implementación se corrigieron un bloqueo SQL sobre una relación de revisor nullable y nombres de componentes del esquema que coincidían con otros módulos; las verificaciones posteriores aprobaron.

Todos los ensayos utilizaron PostgreSQL temporal por socket Unix y servidores propios en loopback. Los recursos temporales fueron detenidos y eliminados por los ejecutores. No se aplicó la migración a producción, no se enviaron mensajes ni se modificaron otras aplicaciones del VPS. Fuentes DOCX/prompt intactas por SHA-256.

Reproducción: `python3 tests/run_backend.py` para regresión completa, o `python3 tests/run_backend.py core.test_mfa core.test_exceptional_mfa` para el área MFA. Los casos de seguridad habilitan la función sólo en sus ajustes de prueba; el ejecutor de navegador la habilita únicamente en su entorno sintético desechable.
