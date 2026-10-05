# Corrección de nombres 0.39.3 — publicada

Paquete `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.3-20261001T204011Z`.

Backend/frontend actualizados para corregir sólo nombre/apellidos de cuentas protegidas elegibles. Sin migraciones: esquema 0046. Bootstrap deshabilitado, sin crear/reactivar cuentas DEMO ni alterar nombres reales. Detalle: docs/CORRECCION_NOMBRES_0_39_3.md.

Validaciones: 38 pruebas backend de cuentas/escuelas, checks/OpenAPI, build/TypeScript y dos recorridos navegador (corrección protegida + CRUD habitual), incluido móvil. Restauración aislada por socket privado preserva exactamente 2.884 registros originales en 44 tablas; no hay migraciones por aplicar. Respaldo preparation.dump, manifiesto y rehearsal.json conservados; preflight aprobado.

Publicada el 01/10/2026 tras autorización expresa. Respaldos previo y sin escritores conservados, sin migraciones pendientes. Once contenedores ajenos intactos. HTTPS autenticado verifica modal de corrección en ambas escuelas, sin campos de acceso y sin guardar cambios reales; las cuentas DEMO permanecen fuera del directorio. Evidencia: name-correction-https-verified.json y verified-*.json. Comandos utilizados (registro histórico, no repetir activación):

```bash
python3 deploy/demo/redeploy.py check /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.3-20261001T204011Z
python3 deploy/demo/redeploy.py activate /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.39.3-20261001T204011Z
```

Tras publicar, verificar lectura de can_edit_name y modal con cuentas institucionales, sin guardar cambios en datos reales como prueba. Inventario ajeno protegido por activador. Las cuentas DEMO retiradas deben permanecer inactivas y fuera de directorios.
