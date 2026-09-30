# Entrega 0.9 — autenticación MFA

Continuación del punto 6. Se incorpora MFA al gestor y se comprueba su conservación en una restauración sintética. **No se activó producción ni se configuraron autenticadores institucionales reales.** Monitoreo, copia externa y demostración de RPO/RTO de producción siguen pendientes.

## Acceso y alcance

Después de comprobar la contraseña, una cuenta que necesita MFA sólo puede acceder a los endpoints de sesión y MFA hasta completar el segundo factor. La comprobación se realiza en la autenticación de todas las API de negocio, incluidas exportaciones y descargas. No basta con ocultar pantallas. Las sesiones anteriores también vuelven a comprobar el requisito en cada solicitud.

MFA se exige por defecto a cuentas `staff`/superusuario, titulares de mandato institucional vigente y roles vigentes `director`, `coordinator`, `manager`, `compliance`, `clinical`, `technical` y `developer`. El nombramiento o mandato no concede por sí mismo permisos adicionales de negocio. Colaboradores y auditores pueden activarlo voluntariamente; una cuenta con autenticador activo siempre necesita segundo factor, aunque cambie de rol o se desactive la exigencia general en un entorno de pruebas. Un nuevo nombramiento privilegiado hace que se exija MFA desde la siguiente solicitud.

La verificación vale un máximo de doce horas y se vincula a la generación del dispositivo. La sesión parcial de contraseña permite diez minutos para completar MFA; después debe ingresar de nuevo. Un nuevo ingreso con contraseña limpia la marca MFA anterior. Activar/reemplazar autenticador, regenerar códigos o utilizar recuperación invalida la verificación de otras sesiones. El acceso se vuelve a evaluar al siguiente pedido; esto no retira información ya descargada.

## Uso por la persona

1. Ingrese con usuario y contraseña. Si su rol exige MFA, verá **Verificación en dos pasos**. Si es opcional, abra **Seguridad de la cuenta** desde Mi trabajo.
2. Confirme su contraseña y pulse **Preparar autenticador**. Añada manualmente una cuenta de tiempo (TOTP) en su aplicación: emisor Salud Modelo, su usuario, la clave mostrada, seis dígitos y periodo de treinta segundos. No se solicita enviar la clave a servicios externos. En esta entrega se proporciona clave manual; no hay imagen QR.
3. Escriba el código generado y confirme. La configuración pendiente vence a los diez minutos y sólo puede confirmarse desde la sesión que la inició. No se activa por el mero hecho de mostrar la clave.
4. Guarde los ocho códigos de recuperación que se muestran una sola vez. Son secretos de 128 bits, de uso único; conserve una copia privada separada del autenticador. El servidor conserva sólo sus hashes, no el texto de los códigos.
5. En ingresos posteriores use el código del autenticador o un código de recuperación. Un TOTP ya consumido se rechaza, también desde otra sesión. El consumo de recuperación se serializa por cuenta para impedir su doble utilización concurrente.
6. Para sustituir el teléfono, verifique acceso y abra Seguridad. **Reemplazar autenticador** exige de nuevo contraseña y un factor actual; el anterior sigue activo hasta confirmar el nuevo. También puede **Renovar códigos**, con contraseña y factor, invalidando todos los anteriores.

Si pierde tanto el autenticador como todos los códigos, no hay un botón de anulación por correo ni un bypass técnico en el producto. El procedimiento institucional de recuperación excepcional, con comprobación de identidad y autoridades competentes, queda pendiente de definir e implementar. No borre filas ni desactive la exigencia para simular ese procedimiento. El alta inicial parte de una cuenta y contraseña entregadas por el mecanismo institucional autorizado; no se implementó una comprobación de identidad fuera de banda para el primer enrolamiento.

## Controles implementados

- TOTP con PyOTP: tolerancia de un periodo anterior/posterior, contador consumido y comparación de tiempo constante; cinco fallos provocan un bloqueo de cinco minutos por cuenta. El estado de intentos está en PostgreSQL y se comparte entre procesos/sesiones. El límite existente de solicitudes sigue aplicándose, con límite de usuario también en el endpoint de sesión.
- Secretos de dispositivo y configuración pendiente cifrados con Fernet y una clave `MFA_ENCRYPTION_KEY` independiente de `DJANGO_SECRET_KEY`. Nunca se guardan en texto claro en la sesión. Los códigos de recuperación aleatorios se verifican mediante SHA-256 y comparación constante.
- Confirmación pendiente vinculada a nonce de sesión, caducidad, rotación de identificador de sesión al verificar y revocación por generación. La recuperación retira configuraciones pendientes anteriores.
- Reconfirmación de contraseña para preparar/reemplazar autenticador y renovar códigos; CSRF en solicitudes que modifican el estado. Respuestas de sesión/MFA con `Cache-Control: no-store`; la UI mantiene los secretos sólo mientras los muestra, sin almacenamiento persistente del navegador.
- Eventos `SecurityEvent` de inicio de configuración, activación, TOTP, recuperación, renovación y fallos, sin códigos, contraseñas ni secretos. Variables sensibles marcadas para filtrado de reportes de excepción en producción. Consulta operativa/alertas de estos eventos aún pendientes.
- Migración aditiva `0015_mfadevice_securityevent`, sin modificar respuestas, documentos, permisos ni historia previa. No existen cuentas o claves precargadas.

MFA TOTP y códigos de recuperación no son resistentes al phishing. Passkeys/WebAuthn, autenticadores múltiples, notificación externa de cambios, rotación automatizada de la clave y recuperación excepcional siguen fuera de esta entrega. La defensa de la contraseña primaria también necesita los controles de despliegue, HTTPS y límites del proxy; no se presenta el límite de intentos MFA como solución completa del acceso.

## Configuración y recuperación del operador

`.env.example` contiene `MFA_REQUIRE_PRIVILEGED=1` y `MFA_ENCRYPTION_KEY` vacía. Antes de un despliegue autorizado, genere una clave Fernet independiente, configure su custodia y recuperación separadas del respaldo de base y mantenga permisos restrictivos del archivo de entorno. No reutilice la clave Django ni publique la clave en comandos, logs o repositorios. Sin clave válida no puede comenzar el enrolamiento. Una clave equivocada no descifra los dispositivos existentes: cambiarla sin migrar el cifrado bloquearía sus TOTP.

`manage.py check --deploy` añade errores `core.E001` si se desactiva la exigencia a privilegiados y `core.E002` si falta una clave Fernet válida. Son comprobaciones previas al despliegue; esta entrega no instaló servicios ni configuró claves reales. El modo sin exigencia general se usa expresamente en el runner de navegador para conservar los recorridos anteriores; el recorrido MFA activa un dispositivo y demuestra que a partir de ahí no puede saltarse el factor. Las pruebas de backend prueban la obligatoriedad con la opción activa.

El respaldo cifrado ahora incluye las nuevas tablas. La clave de cifrado MFA **no se incorpora al archivo de respaldo**; debe estar disponible por el mecanismo separado de recuperación. El ensayo usa una clave efímera y verifica que el dispositivo restaurado exige y acepta un TOTP real. Una restauración de producción debe invalidar sesiones y renovar material de recuperación que pudiera volver a aparecer como no consumido al restaurar un corte anterior. Ese procedimiento de promoción y conciliación sigue pendiente: el ensayo sólo comprueba y retira su entorno, no arranca trabajadores ni promueve copias.

## Verificación ejecutada

- **100 pruebas** de regresión Django aprobadas; después se aprobaron **14 pruebas finales de MFA**, incluidas concurrencia y controles de configuración. La cifra total actual de pruebas Django es 102; no se afirma haber ejecutado esas 102 juntas después de añadir las dos últimas.
- Cuatro recorridos anteriores de Playwright aprobados. El quinto, MFA en escritorio/móvil, pasó al repetirlo tras corregir un selector del ensayo que confundía la alerta de la aplicación con el anunciador de navegación de Next.js. Comprueba enrolamiento, códigos, bloqueo de API pendiente, recuperación y rechazo de reutilización.
- **Ocho pruebas de recuperación** aprobadas con MFA: 58 tablas, 329 filas y un adjunto sintético; 2.722 segundos en el ensayo local registrado en `recovery-test-report.json`. Conserva los permisos, la historia y el segundo factor con clave separada. No acredita RPO/RTO de producción.
- Compilación Next.js/TypeScript 0.9 correcta, `pip check` sin dependencias rotas, comprobación Django y migraciones sin cambios pendientes, OpenAPI validado sin advertencias. Migración aplicada sólo al PostgreSQL privado de desarrollo y ensayos.

Referencias: [PyOTP](https://pyauth.github.io/pyotp/) para TOTP, control de reutilización e intentos; [Fernet](https://cryptography.io/en/stable/fernet/) para cifrado autenticado y custodia de clave. Dependencias fijadas en `backend/requirements.lock`: PyOTP 2.10.0 y cryptography 50.0.1, instaladas sólo en el entorno virtual del proyecto.
