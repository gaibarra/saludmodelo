# Cuentas y solicitudes de usuarios de servicios — 0.40.0

Autorización del 06/10/2026: publicar registro y solicitudes persistentes, sin datos precargados ni mocks en la aplicación. Una cuenta sirve para Salud y Odontología; las Direcciones y el personal conservan el aislamiento escolar. El usuario indicó expresamente mantener acceso del personal sólo con contraseña.

Configuración del paquete: `PATIENT_PORTAL_ENABLED=1`, `MFA_PASSWORD_ONLY_PILOT=1`, `MFA_DEMO_PASSWORD_ONLY=0`, `MFA_REQUIRE_PRIVILEGED=1`, `AI_EXTERNAL_ENABLED=0`. La excepción nueva está apagada por defecto. Desactivarla restablece MFA incluso para sesiones existentes, sin borrar dispositivos ni marcar sesiones como verificadas. `password_only_pilot` se agrega a la respuesta de sesión del personal; no cambian contratos de registro/solicitudes ni esquema de base.

Frontend compilado con `NEXT_PUBLIC_DEMO_MODE=0`: no anuncia datos ficticios ni registro deshabilitado. Cuenta de usuario de servicios con nombre, correo, teléfono y contraseña; solicitudes pendientes, confirmación/rechazo por personal autorizado y retiro por titular. No se agregan expedientes clínicos, verificación por correo, recuperación de contraseña ni envíos externos.

Inspección previa: cero cuentas públicas y cero solicitudes. Todos los servicios internos tienen `public_slug` sin asignar y no existen asignaciones operativas vigentes. Por eso ningún área recibe solicitudes inicialmente, aunque el registro queda habilitado. Para recibirlas se necesita vincular el servicio correcto con el área pública (`Service.public_slug`), mantenerlo confirmado y designar un responsable vigente autorizado. No se crean nombramientos ni se vincula el antiguo servicio DEMO. Estas condiciones deben configurarse por escuela; no implican compartir datos entre ellas.

Validación: 53 pruebas de portal/MFA/escuelas, checks Django, ausencia de migraciones, OpenAPI y build/TypeScript aprobados. Navegador contra API y PostgreSQL real aislado: registro, solicitudes en ambas escuelas, persistencia, cierre/reingreso, retiro y móvil. Datos de ensayo sólo en clúster efímero por socket privado. No se insertan cuentas ficticias en el sitio publicado.

Preparación y activación mediante `deploy/demo/prepare-pilot.py` y `deploy/demo/redeploy-pilot.py`. El segundo conserva el activador histórico, valida intake contra el manifiesto y rechaza bootstrap. Preflight controla imágenes, archivos, rutas, puertos y volúmenes propios. Reversión sólo de código/configuración: conserva esquema y registros posteriores. No restaurar automáticamente un respaldo anterior después de recibir registros.

Publicada y verificada por HTTPS el 06/10/2026. Paquete `runtime/releases/0.40.0-20261006T142322Z`; registro visible, excepción de contraseña activa y cero áreas receptoras hasta resolver las condiciones indicadas. Ver deploy/demo/REDEPLOY_0_40.md.
