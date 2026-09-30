# Prioridad a captura en Escuelas — 0.36.1

Publicado: bloque de información institucional plegado por defecto en `/escuelas`, con resumen «Consultar servicios publicados (N)». Se conserva la información y el portal público; el usuario puede abrir/cerrar el bloque.

Paquete: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.36.1-20260930T173718Z`. Frontend 0.36.1, backend/worker 0.36 y esquema 0043. Sin migraciones. Compilación/TypeScript y verificación HTTPS de estado inicial, apertura, cierre y recarga. Sólo frontend recreado y recarga del gateway propio; otros quince contenedores preservados.

Usar base Compose junto con el `release.compose.json` activo. Reversión exclusiva del frontend:

```bash
python3 deploy/demo/redeploy-interface.py rollback /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.36.1-20260930T173718Z
```

No cambia datos, cuentas o el modo temporal de autenticación.
