# Acceso temporal de demostración 0.35.3

Solicitud expresa del usuario: durante demostración y pruebas, entrar únicamente con usuario y contraseña; volver a incorporar el autenticador antes de trabajar con información real.

Implementación: `MFA_DEMO_PASSWORD_ONLY=1` exclusivamente en backend/worker del paquete de demostración. Valor predeterminado del código: `0`. `MFA_REQUIRE_PRIVILEGED=1` se conserva para recuperar la protección al retirar la excepción. El modo temporal no funciona si `PATIENT_PORTAL_ENABLED=1`. Esta salvaguarda no sustituye la revisión previa al uso de datos reales en los módulos del personal.

No se eliminan ni modifican dispositivos, claves cifradas o códigos de recuperación existentes. Las sesiones de demostración no obtienen una marca de verificación MFA artificial. Al reactivar MFA, las sesiones sin verificación vuelven a quedar bloqueadas. Se mantienen contraseña, permisos escolares, sesiones, CSRF y HTTPS.

La página `/personal` informa del acceso temporal con contraseña y oculta la indicación de dos etapas cuando ese modo está activo.

Paquete: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.3-20260930T164612Z`. Imágenes backend/frontend 0.35.3, esquema 0042 sin nuevas migraciones. Activador: `redeploy.py`. Configuración privada original intacta; la excepción reside en `release.compose.json`. Incluir siempre ese archivo al operar Compose.

Validación: 62 pruebas backend de MFA/recuperación/permisos escolares; checks, OpenAPI y ausencia de nuevas migraciones; compilación/TypeScript; dos recorridos de navegador aislados (cuenta previamente inscrita entra con contraseña y administración escolar). Copia de la base restaurada por socket Unix privado: tres cuentas institucionales entran sin MFA y vuelven a quedar bloqueadas al retirar la excepción; dispositivos conservados. Respaldos previos a la activación, incluida copia sin escritores. No se volvió a ejecutar el alta de cuentas.

Se actualizaron únicamente backend/frontend/worker propios y se recargó el gateway propio. Las once aplicaciones ajenas conservaron sus contenedores. Base y gateway propios conservaron sus identificadores. Sin cambios a Nginx/certificados/servicios del host.

## Antes de información real

1. Preparar una nueva entrega con `MFA_DEMO_PASSWORD_ONLY=0` en backend y worker, manteniendo `MFA_REQUIRE_PRIVILEGED=1`; actualizar manifiesto y repetir comprobaciones.
2. Activar únicamente los servicios propios y comprobar que una sesión sin segundo factor recibe 403 en las APIs protegidas.
3. Completar la inscripción/verificación personal de cada titular; revisar la configuración de Gonzalo iniciada y expuesta en la captura de la conversación, y sustituirla antes del uso real si llegó a activarse.
4. Ensayar ingreso y recuperación con los titulares antes de habilitar información real. La aceptación clínica/institucional sigue siendo un pendiente separado.

No ejecutar el smoke de contraseñas después de reactivar MFA. Utilizar el recorrido de MFA con el manifiesto de esa futura entrega.
