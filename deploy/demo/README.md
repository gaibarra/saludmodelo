# Entorno aislado de demostración de Salud Modelo

Autorización: el usuario pidió una prueba para presentar a Dirección y confirmó `plansaludmodelo.online` sobre `194.113.64.91`. La inspección identificó **49153 como SSH**. Este despliegue no reutiliza ese puerto ni ninguna base de otra aplicación.

**Versión activa: 0.35**, con escuelas independientes y cuentas institucionales creadas el 30/09/2026. Ver `REDEPLOY_0_35.md` para estado, accesos, MFA y operación. La configuración base conserva las etiquetas históricas: al recrear servicios se debe incluir el override de la entrega activa.

Actualización 0.34 superada por el requisito de escuelas independientes, sin activar: consultar `REDEPLOY_0_34.md`. Estado y pruebas de la publicación inicial: consultar `VERIFICACION.md`. No confundir disponibilidad en loopback con publicación HTTPS.

## Recursos exclusivos

- Compose: `salud-modelo-demo`; imágenes `salud-modelo-demo-backend:0.31` y `salud-modelo-demo-frontend:0.31`.
- Servicios: db, backend, frontend, gateway y worker. Límites totales configurados: 1728 MiB y 3,25 CPU máximas; el consumo real es menor y depende de la carga.
- Único puerto de host: **127.0.0.1:3117**. El Nginx del VPS lo publica sólo para el dominio indicado.
- PostgreSQL: `salud_modelo_demo`, socket propio en volumen `salud-modelo-demo_socket`, sin escucha TCP y con `network_mode: none`.
- Volúmenes propios: database, socket y private; redes propias application (interna) e ingress (sólo gateway).
- Backend, frontend, worker y gateway sin root, sistema de archivos de sólo lectura y temporales propios. PostgreSQL utiliza su entrada oficial para preparar el volumen y ejecutarse como postgres.
- Datos y archivos persistentes. `restart: unless-stopped` permite recuperar estos contenedores cuando Docker vuelva a iniciar.
- MFA activo en las cuentas de demo; secretos independientes, IA externa desactivada. Ningún secreto en imágenes ni archivos públicos. `runtime/` es privado y está excluido de control de versiones y contextos de build.

## Publicación inicial completada el 29/09/2026

El dominio ya tiene HTTPS válido. Para actualizar la aplicación, seguir **REDEPLOY_0_34.md**; no repetir la activación del dominio. Las instrucciones siguientes se conservan como referencia de la instalación inicial.

Revisar `activate-domain.sh`, `domain-http.conf` y `domain-https.conf`; después ejecutar:

```bash
sudo bash /home/gaibarra/plandetrabajo/deploy/demo/activate-domain.sh
```

El script verifica conflictos de nombre, salud del upstream y configuración actual. Crea **sólo** `salud-modelo-demo.conf` en sites-available/enabled; recarga Nginx de forma gradual después de `nginx -t`, sin reiniciarlo. No edita sitios existentes. Si la activación del sitio falla, elimina exclusivamente esos dos archivos nuevos y valida/recarga la configuración anterior. No borra certificados emitidos ni datos de la app.

El primer intento del 29/09/2026 **sí emitió** el certificado, pero la comprobación HTTPS posterior rechazó el certificado servido por el dominio y retiró sólo el sitio nuevo. El script ahora reutiliza el certificado propio vigente, valida el sitio por loopback y comprueba también el acceso público antes de considerarlo activo. No se necesita volver a instalar Certbot.

Certbot usa directorios separados `/etc/letsencrypt-salud-modelo-demo`, `/var/lib/letsencrypt-salud-modelo-demo` y `/var/log/letsencrypt-salud-modelo-demo`; solicita únicamente el certificado del dominio dado. Utiliza aceptación no interactiva de los términos de Let's Encrypt y registro sin correo; no envía invitaciones ni avisos a personas. Instala su propio temporizador de renovación `salud-modelo-demo-cert-renew.timer`. No usa ni modifica certificados de otras aplicaciones. Si fallara instalar el temporizador tras activar HTTPS, el sitio queda activo y debe repararse sólo ese temporizador; no volver a ejecutar ciegamente el script completo.

Comprobar después:

```bash
curl --fail https://plansaludmodelo.online/health
node /home/gaibarra/plandetrabajo/deploy/demo/smoke-schools.mjs
```

El segundo comando usa contraseñas y TOTP exclusivamente desde el archivo privado. No los imprime. Realiza ingreso de las cuatro cuentas, comprueba aislamiento, consulta las seis preguntas y carga tareas, capacidad e informe semanal. No desactiva la validación TLS. Evitar repetirlo dentro del mismo intervalo TOTP de 30 segundos.

## Operación acotada

Desde `/home/gaibarra/plandetrabajo`:

```bash
docker compose -f deploy/demo/compose.yaml ps
docker compose -f deploy/demo/compose.yaml logs --tail 30 worker gateway
```

El worker ejecuta el ciclo de avisos internos y trabajos autorizados cada 30 segundos. No habilita proveedores de IA ni envíos externos. El estado está en `/private/worker-state/worker.json`, dentro del volumen propio.

Copia previa a la reunión, con archivo privado y sin detener la app:

```bash
umask 077
docker compose -f deploy/demo/compose.yaml exec -T db pg_dump -U salud_modelo_demo -Fc salud_modelo_demo > deploy/demo/runtime/antes-reunion.dump
```

Esta copia local sintética no sustituye una política de respaldo y restauración de producción real. Conservar también backend.env, database.env y el volumen privado cuando se planifique una restauración. No borrar ni reinicializar el volumen para «reiniciar la demo»; preserva las acciones realizadas.

## Construcción y carga inicial (ya ejecutadas)

Interfaz separada: `SALUD_DEMO_BUILD=1 NEXT_PUBLIC_DEMO_MODE=1 npm run build`, dentro de `frontend`. Conserva `.next` y escribe `.next-demo`. Usar `build-release-image.py` para enviar un contexto explícitamente limitado por imagen; también existe `.dockerignore` raíz para Docker clásico. Los secretos y respaldos quedan fuera de esos contextos.

Los secretos se generaron aleatoriamente con permisos 600 en `runtime/`. No regenerarlos al actualizar imágenes. Para una base nueva exclusivamente: esperar salud de db, ejecutar `manage.py migrate`, y cargar `/app/demo_seed.py` con montaje temporal de runtime en `/demo-private`. El cargador exige el nombre/socket/marcador exactos y rechaza usuarios, instituciones o archivo de accesos ya existentes. No incorpora un reset destructivo.

La aplicación permanente no monta el archivo de accesos de los usuarios. Las credenciales de base y cifrado se reciben por variables de entorno privadas.

Presentación: `GUIA_REUNION.md`. Accesos: `runtime/ACCESOS_PRIVADOS.md`, sólo para el operador de la reunión.
