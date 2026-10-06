# Portal de usuarios de servicios 0.40.0

Publicación autorizada expresamente por el usuario el 06/10/2026. Preparación con `python3 deploy/demo/prepare-pilot.py`; activación exclusiva del paquete generado con `python3 deploy/demo/redeploy-pilot.py activate RUTA_DEL_PAQUETE`.

Pruebas aprobadas: 53 backend, checks/OpenAPI, build/TypeScript y navegador contra API/PostgreSQL aislados. Sin migraciones ni bootstrap. Registro persistente; MFA_PASSWORD_ONLY_PILOT permite el acceso acordado por contraseña. No hay cuentas o solicitudes inventadas en el sitio activo. El catálogo no recibe solicitudes hasta configurar enlaces de servicios y responsables vigentes.

Estado: publicada y verificada el 06/10/2026. Paquete `runtime/releases/0.40.0-20261006T142322Z`. Respaldo restaurado en ensayo privado: 2.886 registros de 44 tablas conservados; esquema 0046 sin migraciones pendientes. Respaldos previo/sin escritores y archivos privados conservados. HTTPS/navegador: formulario de registro visible, portal y excepción de contraseña activos, banner ficticio ausente y móvil sin desbordamiento. Cero cuentas y solicitudes creadas durante la verificación. Los 13 contenedores ajenos permanecieron intactos. Evidencias: `public-verification.json`, `portal-desktop.png`, `portal-mobile.png`, `rehearsal.json` y `verified-*.json` dentro del paquete.
