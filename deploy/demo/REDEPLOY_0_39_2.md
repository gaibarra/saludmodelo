# Logo institucional 0.39.2 — publicado

Paquete: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.2-20261001T195746Z`.

Sólo frontend; backend/worker/db conservan 0.39.0/esquema 0046. Logo original Modelo.jpg integrado en portal, personal, módulos, modales de cuentas e informes académicos/semanales; impresión A4 con márgenes y marca visible, icono de pestaña. Detalle: docs/IDENTIDAD_INSTITUCIONAL_0_39_2.md.

Build/TypeScript aprobados. Navegador recorre 6 rutas públicas, 15 internas, modal, carga efectiva de imagen, informe/PDF y cuatro rutas en móvil. PDF sintético revisado visualmente. Imagen fijada por digest y Compose validado. Sin cambios de registros ni reescritura de contenidos históricos.

Publicada el 01/10/2026 tras autorización expresa para 0.39.2. Sólo frontend sustituido; 15 contenedores protegidos intactos, incluidos once ajenos. Logo HTTPS cotejado por SHA-256 con el original; navegador autenticado verifica portal, personal, Caja, académico, reportes y modal móvil, sin modificar cuentas. Evidencia: activate-verified.json y logo-https-verified.json. Comando utilizado (no repetir sobre paquete activo):

```bash
python3 deploy/demo/redeploy-interface.py activate /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.2-20261001T195746Z
```

El activador aborta si cambia inventario/configuración y sustituye sólo frontend, con recarga del gateway propio. Conserva imagen/Compose anterior para reversión. No toca base de datos ni otras aplicaciones. Tras activar verificar por HTTPS la imagen original, portal, encabezado del personal y lectura de módulos/modales; no modificar cuentas ni generar registros reales para probar.
