# Verificación — 29 de septiembre de 2026

**Estado actual: demostración publicada y comprobada en HTTPS público el 29/09/2026, 20:37 UTC.** El párrafo siguiente documenta el estado previo a la activación. El primer intento de activación emitió correctamente un certificado válido para el dominio (vence el 28/12/2026), pero el HTTPS servido después siguió presentando otro certificado; el script retiró únicamente el sitio nuevo. Certbot está instalado (v1.21.0) y el script revisado reutilizará el certificado propio antes de repetir la comprobación local y pública. No se eludió la validación TLS ni se realizó ingreso a ese sitio público.

## Comprobado

- DNS IPv4 del dominio: 194.113.64.91. El puerto 49153 responde con identificación SSH.
- Build Next.js de demostración, TypeScript y aviso visible de datos ficticios correctos. Build separado `.next-demo`; no sustituye el build `.next` existente.
- 25 pruebas de seguimiento y MFA aprobadas con PostgreSQL temporal por socket Unix; comprobación de modelos/migraciones y OpenAPI sin cambios ni advertencias en ese ejecutor.
- Base de demostración nueva, migraciones 0001–0038 de core aplicadas sólo en ella. Escucha TCP de esa base desactivada y sin red de contenedor.
- Servicio propio accesible en `127.0.0.1:3117`: página y API de sesión devuelven HTTP 200. Gateway comprobado con `nginx -t`.
- Cinco contenedores propios activos. Trabajador con señal `ok`, procesa avisos internos cada 30 segundos; no habilita IA ni mensajería externa.
- Navegador real: cuatro cuentas con contraseña y TOTP; cada una ve un solo servicio y seis preguntas originales. Consulta efectiva del tablero, comparación de capacidad, registro de capacidad con 120 minutos disponibles el 05/10/2026 y generación del informe semanal. Pantallas de administración e informes cargadas sin errores JavaScript. Informe reproducible: `runtime/smoke-local.json` (17:38 UTC).
- Las pruebas de navegador locales enrutan el dominio al gateway privado mediante Playwright. **Esto no constituye una prueba de certificado ni de conexión HTTPS pública.** `smoke.mjs public` desactiva ese enrutamiento y requiere TLS válido; aún pendiente.
- Configuraciones propuestas de dominio HTTP/HTTPS comprobadas con Nginx del host, sustituyendo únicamente puertos por loopback alto y certificados por uno temporal. Validación exacta del conjunto activo con privilegios se ejecuta en `activate-domain.sh`, antes de cada recarga.
- `check --deploy` de Django avisa de X-Frame-Options, HSTS y redirección HTTPS porque están implementados en los proxies: gateway agrega X-Frame-Options; el sitio HTTPS propuesto agrega HSTS de una hora y redirección HTTP. Estas últimas protecciones públicas dependen de activar el sitio.
- Once contenedores ajenos conservan ID, fecha de arranque, puertos y estado activo. No se editaron sitios Nginx existentes, bases ajenas, SSH, certificados ni reglas de red de otras aplicaciones. Docker creó sólo las redes y la publicación loopback del proyecto nuevo.
- Fuentes DOCX/Markdown conservan sus SHA-256 originales. Secretos y accesos con permisos 600 dentro de runtime con permisos 700.
- Copia local de la base ficticia: `runtime/antes-reunion.dump` (formato PostgreSQL custom, permisos 600). No se declara probado un procedimiento de restauración de producción de este despliegue.

## Pasos pendientes al corte inicial (resueltos después)

1. Reejecutar desde terminal con sudo el script `activate-domain.sh` revisado; necesita modificar sólo el sitio nuevo en /etc/nginx y crear su certificado/temporizador propios. Esta sesión no dispone de sudo sin contraseña. Se solicitó al usuario ejecutar el paso, sin pedirle compartir credenciales.
2. Confirmar `https://plansaludmodelo.online/health`, comprobar acceso público con `node deploy/demo/smoke.mjs public` y actualizar este registro.
3. Ensayar el guion de la reunión con el presentador usando `GUIA_REUNION.md` y sus accesos privados.

La habilitación de esta demo no implica aceptación del piloto, aprobación de contenidos institucionales ni cierre del alcance clínico.

## Reintento de activación — 29/09/2026 14:33 CST

El certificado propio se detectó vigente y se reutilizó. Nginx validó y aceptó la señal de recarga, pero la comprobación HTTPS inmediata recibió el certificado anterior y el script retiró el sitio propio. Los procesos de trabajo observados después pertenecían a la recarga de reversión; el proceso de control informa éxito al enviar la señal, sin esperar a que termine el cambio de procesos. Como hipótesis técnica principal, la consulta inmediata llegó a un proceso anterior. El activador ahora espera repetidamente hasta que Nginx local y la URL pública sirvan el identificador de Salud Modelo o se agote un tiempo acotado; conserva la reversión exclusiva si sigue fallando. Pendiente reejecutar y verificar el resultado.

## Activación completada — 29/09/2026

El usuario ejecutó el activador v3. Sitio `salud-modelo-demo.conf` habilitado. Certificado propio de Let's Encrypt válido para `plansaludmodelo.online` y temporizador exclusivo de renovación activo/habilitado. HTTP redirige a HTTPS; `/` devuelve HTTP 200 y `/health` devuelve `salud-modelo-demo` con validación TLS normal. `node deploy/demo/smoke.mjs public` aprobó el acceso de las cuatro cuentas con MFA, seis preguntas originales por cuenta, tablero, capacidad, administración e informe; resultado en `runtime/smoke-public.json`. Sin excepciones de certificado ni errores JavaScript. Las decisiones reales del piloto y el alcance clínico siguen pendientes.

## Redespliegue 0.35 completado — 30/09/2026

Versión 0.35 activa; migraciones 0039–0042 aplicadas y check de migraciones aprobado. Escuelas independientes y cuentas institucionales solicitadas configuradas. Prueba pública `smoke-schools.mjs` aprobada: credenciales nuevas, MFA obligatorio antes de API protegida y acceso completo/consulta escolar con cuentas ficticias de MFA existente. Worker correcto. Ver REDEPLOY_0_35.md para alcance, incidencias resueltas, respaldos y guía de primer ingreso. No utilizar las expectativas de permisos de la prueba 0.31 para las cuentas ficticias ahora acotadas.

30/09/2026 — Corrección de entrada 0.35.1 publicada: portada en `/`, personal en `/personal`, seis pestañas y escuelas pares. Dos recorridos aislados, imagen sin red, compilación, navegador HTTPS con MFA pendiente y permisos escolares aprobados. Otros quince contenedores sin cambios. Ver `REDEPLOY_0_35_1.md`.

30/09/2026 — 0.35.4 publicado: inicio académico en `/personal`, gestor conservado en `/personal/plan`. Compilación, cuatro recorridos aislados y prueba pública de cinco cuentas aprobados. Tarjetas/acciones de los tres titulares comprobadas; capturas escritorio/móvil. Backend 0.35.3 y modo de contraseña conservados; otros quince contenedores sin cambios.

30/09/2026 — 0.36 publicado: seis fichas institucionales del sitio oficial incorporadas a base e interfaces; migración 0043 aplicada sin pendientes. 35 pruebas backend, navegador aislado y HTTPS público aprobados. Restauración/importación conserva 2.812 filas de 43 tablas, repetición idempotente. Once aplicaciones ajenas y db/gateway propios sin cambios. Detalle: `REDEPLOY_0_36.md`.
