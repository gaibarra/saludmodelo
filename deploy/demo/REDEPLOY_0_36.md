# Directorio institucional 0.36 — publicado

Paquete activo: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.36.0-20260930T171804Z`. Imágenes backend/frontend `0.36`; migración aditiva `0043_institutional_service_directory` aplicada. Seis nuevas fichas y servicios incorporados; registro dental DEMO previo intacto.

El bloque bootstrap del manifiesto ejecuta exclusivamente el importador de servicios institucionales, no el alta de cuentas. Script fuente: `bootstrap-institutional-services.py`; copia inmutable montada por el activador genérico como `bootstrap-school-release.py`. La configuración privada conserva los datos para comprobar las cuentas, pero el importador utiliza únicamente institución/actor/hash del dataset. No se restablecen contraseñas.

Validación: 35 pruebas backend de catálogo/portal/escuelas, checks y OpenAPI, compilación/TypeScript, recorrido de navegador del directorio público/contactos/público destinatario/móvil/paneles escolares. Ensayo sobre copia restaurada por socket Unix privado: 2.812 filas originales de 43 tablas idénticas antes/después, migración e importación mediante imagen final, repetición sin duplicados. Respaldos de base/archivos antes de activar, incluida copia sin escritores. `migrate --check` sin pendientes.

Despliegue limitado a backend/frontend/worker propios y recarga del gateway propio. Once contenedores ajenos y db/gateway propios conservan IDs, inicio, imágenes, puertos y montajes. Sin Nginx/certificados/servicios del host modificados. MFA temporal de demostración conservado; solicitudes de pacientes e IA externa siguen apagadas.

Fuente y límites: `docs/SERVICIOS_INSTITUCIONALES_0_36.md`. No se confirma automáticamente la operación de los nuevos servicios ni se asignan personas. Los campos de origen son información pública institucional, no datos de pacientes.

Usar siempre `release.compose.json` del paquete activo junto con la base Compose. Activador: `redeploy.py`; reversión de código mediante su modo rollback conserva la migración y los seis registros, no restaura la base ni elimina datos. Una reversión devuelve la interfaz anterior, donde no se muestran las fichas publicadas, pero las filas de servicio permanecen.

Prueba HTTPS posterior aprobada: seis fichas desde la base, contactos y discrepancia de Fisioterapia, ausencia explícita de consulta independiente de Psicología, unidad sólo para comunidad universitaria, panel personal, cuatro fichas de Salud y una de Odontología, vista móvil y fuente/fecha. Resultados privados en `public-catalog-smoke.json`; capturas `docs/capturas/directorio-publico-0.36.png` y `directorio-movil-0.36.png`.
