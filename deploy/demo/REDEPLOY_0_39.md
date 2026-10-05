# Caja 0.39.0 — publicada

Paquete: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.0-20261001T191505Z`.

Incluye Caja por servicio con responsables por turno, operaciones sólo en efectivo MXN, apertura, cobros, ingresos de fondo, retiros, devoluciones referidas al cobro original, arqueo/cierre y monitoreo escolar/institucional. Conserva separación estricta de escuelas. Detalle: docs/CAJA_0_39.md.

Migración aditiva 0046 crea CashShift y CashMovement. Bootstrap deshabilitado: no crea cuentas, turnos ni movimientos ficticios. Imágenes propias backend/frontend fijadas por digest; Compose conserva gateway/db y servicios ajenos. Ensayo de restauración en PostgreSQL privado sin TCP preservó exactamente 2.891 filas originales en 44 tablas pobladas. Manifiesto, respaldo preparation.dump y rehearsal.json dentro del paquete privado. Check de despliegue aprobado.

Validación: 44 pruebas de Caja/cuentas/escuelas, una prueba adicional concurrente de retiros; checks/OpenAPI, build/TypeScript y navegador con recorrido completo/móvil aprobados. Se corrigieron los nombres de operaciones OpenAPI y nombres accesibles de listas antes de finalizar.

El rechazo inicial quedó resuelto por autorización expresa del usuario. Publicada el 01/10/2026 a las 19:18 UTC: migración 0046 aplicada, respaldo previo y sin escritores conservados, rutas HTTPS aprobadas. Lecturas con las cuentas de Carla, Mario y Gonzalo verifican acceso a Caja dentro de su alcance. Cero turnos y movimientos ficticios; migrate --check aprobado. Once contenedores ajenos conservan inventario intacto. No volver a ejecutar activate sobre este paquete ya activo.

Comandos utilizados para esta publicación (registro histórico):

```bash
python3 deploy/demo/redeploy.py check /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.0-20261001T191505Z
python3 deploy/demo/redeploy.py activate /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.0-20261001T191505Z
```

El activador genera respaldo previo y sin escritores, aplica migraciones, recrea únicamente backend/frontend/worker propios y recarga gateway propio; verifica inventario ajeno/rutas. Validar adicionalmente `/caja`, acceso de las tres cuentas institucionales y `migrate --check`. No registrar efectivo real ni ficticio para comprobar producción. Script de lectura preparado `/tmp/check-cash-live.py`.

Previo al uso real se mantienen los requisitos operativos y de seguridad del proyecto (incluida restauración de MFA). No habilitar solicitudes reales de pacientes ni otros medios de pago por este despliegue.
