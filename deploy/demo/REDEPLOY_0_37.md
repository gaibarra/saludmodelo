# Psicología 0.37.0 — publicada

Paquete revisado: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.37.0-20261001T163004Z`.

Proyecto: `salud-modelo-demo`. Dominio: `plansaludmodelo.online`. Imágenes backend/frontend `0.37.0`, fijadas por digest en manifiesto. Migración aditiva 0044; importación idempotente que actualiza exclusivamente la ficha de La Casita y su nombre operativo original. No ejecuta bootstrap de cuentas ni restablece contraseñas.

`redeploy.py check` aprobado. Respaldo `preparation.dump`, ensayo `rehearsal.json`, inventario y hashes dentro del paquete privado. No publicar estos respaldos. Validación funcional: docs/PSICOLOGIA_0_37.md.

El activador detiene brevemente backend/worker propios, obtiene un respaldo sin escritores, aplica la migración y carga revisada, recrea backend/frontend/worker propios y recarga exclusivamente el gateway del proyecto. El sitio podría tener una breve interrupción. No modifica Nginx del host, certificados, redes ni aplicaciones ajenas. Verifica su inventario al terminar. Conserva db/gateway propios y sus volúmenes. Reversión de código conserva migración aditiva y datos.

Publicada el 01/10/2026 a las 16:35 UTC tras autorización expresa del usuario, que resolvió el rechazo inicial de la revisión automática. `activated.json`, `configured.json` y `verified-*.json` documentan el resultado en el paquete privado.

Aplicada 0044; `migrate --check` correcto. El importador creó cero servicios y actualizó/renombró sólo `modelo-usc-casita`. Respaldo previo, copia sin escritores y archivos privados conservados. Backend/frontend/worker activos; db y gateway saludables. Once contenedores ajenos y db/gateway propios idénticos al inventario previo; sin cambios de host, certificados o sitios ajenos.

Comprobación pública en `public-psychology-check.json`: HTTPS, ficha única de Salud en Psicología y Atención Comunitaria, seis fichas generales, fuente estatal, móvil sin desbordamiento, solicitudes reales deshabilitadas. Capturas en `docs/capturas/psicologia-publico-0.37.png`, `atencion-comunitaria-publico-0.37.png` y `psicologia-movil-0.37.png`.

No volver a activar para verificar. Reversión de código, si se autoriza y fuera necesaria:

```bash
python3 deploy/demo/redeploy.py rollback /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.37.0-20261001T163004Z
```

La reversión conserva la migración aditiva y los datos; no restaura la base automáticamente.
