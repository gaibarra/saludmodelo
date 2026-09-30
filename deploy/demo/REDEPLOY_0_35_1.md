# Corrección de portada 0.35.1 — publicada

La dirección principal mostraba el gestor anterior y recuperaba una sesión pendiente de MFA. Ahora `/` presenta el portal de los seis servicios; `/personal` contiene el gestor y su autenticación. `/portal` sigue disponible. Enlaces del personal actualizados y ambas escuelas identificadas en la portada.

Fecha: 30/09/2026. Frontend `salud-modelo-demo-frontend:0.35.1`; backend y worker conservan 0.35. Sin migraciones ni cambios de cuentas. Solicitudes reales e IA externa siguen apagadas; MFA obligatorio conservado.

Paquete activo: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.1-20260930T161656Z`. Contiene imagen SHA, configuración de release/reversión, inventario protegido y resultados de activación/prueba pública. Los archivos privados no se publican.

Verificación: build/TypeScript correctos, dos pruebas de navegador aisladas (portada con sesión pendiente de MFA, navegación entre servicios, vista móvil y permisos de escuelas), imagen ejecutada sin red, HTTPS público y cinco cuentas comprobadas. Las tres institucionales continúan requiriendo su verificación personal. Capturas: `docs/capturas/portada-publica-0.35.1.png` y `docs/capturas/portada-movil-0.35.1.png`.

Sólo se recreó frontend y se recargó Nginx dentro del gateway propio. Los otros quince contenedores conservaron identificadores, inicios, imágenes, puertos y montajes. Sin cambios en servicios, certificados o Nginx del host.

Para operar con Compose incluir siempre `release.compose.json` del paquete activo: el archivo base conserva etiquetas históricas. Este parche usa `redeploy-frontend.py`, **no** el activador completo `redeploy.py`. Reversión del parche:

```bash
python3 deploy/demo/redeploy-frontend.py rollback /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.1-20260930T161656Z
```

La reversión restaura exclusivamente la interfaz 0.35 y vuelve a mostrar el gestor en `/`; no modifica datos, esquema ni cuentas. El manifiesto verifica que no haya cambios posteriores antes de permitirla.
