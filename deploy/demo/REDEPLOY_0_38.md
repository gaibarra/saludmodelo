# Tabla de cuentas escolares — 0.38.0 preparada

Paquete revisado: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.38.0-20261001T181715Z`.

Imágenes backend/frontend 0.38.0 fijadas por digest. `bootstrap=False`: no importar catálogos, crear cuentas, cambiar contraseñas ni configurar escuelas durante la publicación. Sin migraciones nuevas (esquema 0044). Versión publicada actual: 0.37.1.

Funcionalidad y límites: `docs/CUENTAS_ESCOLARES_0_38.md`. Tabla plegable con búsqueda, estado, paginación, detalle, alta mediante formulario existente, edición, baja lógica y reactivación. Permisos escolares, protección de autoridades/cuentas compartidas, control de concurrencia y auditoría.

Validación aprobada: 34 pruebas backend (cuentas y escuelas), checks/makemigrations/OpenAPI, compilación y TypeScript; recorrido de navegador crear/buscar/ver/editar/baja/filtro/reactivar/móvil. Se corrigió el nombre accesible del filtro Estado, y el recorrido final pasó. Captura de datos ficticios: `docs/capturas/cuentas-escolares-ensayo-0.38.png`.

Restauración aislada por socket privado, sin TCP: 2.887 filas originales de 44 tablas pobladas conservadas exactamente, esquema 0044 sin cambios. Respaldo `preparation.dump`, manifiesto, inventario, archivos Compose de publicación/reversión y `rehearsal.json` en paquete privado. `redeploy.py check` aprobado. Advertencia preexistente ajena a este incremento: fecha fija en core.Task.starts.

**Pendiente: autorización específica para publicar 0.38.0.** No se intentó activación; la autorización anterior mencionaba 0.37.1. AGENTS.md exige autorización específica antes de activar producción.

Después de autorización repetir check. Si los contenedores o configuración difieren, preparar otro paquete:

```bash
python3 deploy/demo/redeploy.py check /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.38.0-20261001T181715Z
python3 deploy/demo/redeploy.py activate /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.38.0-20261001T181715Z
```

Activación limitada a backend/frontend/worker propios, respaldo previo/sin escritores y archivos privados, recarga de gateway propio, sin modificar db/gateway ni aplicaciones ajenas. Puede producir breve interrupción de Salud Modelo. Tras publicar comprobar tabla y consultas autorizadas, no realizar bajas/altas reales como prueba, verificar inventario ajeno y ausencia de migraciones pendientes. Pruebas de mutaciones ya ejecutadas en entorno aislado.
