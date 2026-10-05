# Directorio de cuentas UX/UI 0.39.1 — publicado

Paquete frontend: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.1-20261001T193003Z`.

Sólo sustituye frontend; backend, worker y base conservan 0.39.0 / esquema 0046. No hay migraciones, importaciones ni cambios de cuentas. Interfaz: docs/CUENTAS_UX_0_39_1.md.

Compilación/TypeScript aprobados, imagen fijada por digest, configuración Compose validada e inventario protegido capturado. El activador verifica que todos los contenedores excepto frontend permanezcan iguales, recarga sólo gateway propio y conserva imagen de reversión. Preparador actualizado para paquetes actuales sin bootstrap.json; no requiere configuración de cuentas para cambios visuales.

Publicada el 01/10/2026 tras autorización expresa para 0.39.1. Sólo frontend reemplazado; 15 contenedores protegidos intactos (incluidos backend/db/worker y once ajenos). HTTPS autenticado verifica tabla, modales de consulta y alta sin envío, Escape y móvil; no se modificaron cuentas. Evidencia en activate-verified.json y accounts-https-verified.json. Comando utilizado (no repetir sobre paquete activo):

```bash
python3 deploy/demo/redeploy-interface.py activate /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.1-20261001T193003Z
```

Si el inventario/configuración cambió, el activador aborta y habrá que preparar nuevo paquete. Verificar tras publicación /escuelas y los modales en lectura; no crear/borrar cuentas reales como prueba. Las operaciones CRUD se ensayan en PostgreSQL privado aislado.

Recorrido final de navegador aprobado: crear, buscar, editar, baja, filtro, reactivar, Escape, restauración de foco, aviso de cambios sin guardar y modal en móvil/teclado. Capturas de tabla y detalle revisadas visualmente. El paquete preliminar 192737Z queda bloqueado como sustituido.
