# Separación de escuelas — 0.38.1

Decisión expresa del usuario del 01/10/2026: Salud no tiene acceso a Odontología ni viceversa. Sustituye la estrategia anterior de consulta académica entre escuelas. Gonzalo mantiene su autoridad institucional de superusuario sobre ambas.

El servidor ignora cualquier autorización histórica de consulta cruzada, impide crear nuevas y restringe los tableros, listados académicos e informes a la escuela autorizada. La interfaz ya no presenta formularios de compartir ni otras escuelas para los directores. Se conserva el directorio público de servicios para pacientes; no concede acceso a registros internos.

Migración 0045: revoca las autorizaciones históricas sin borrar registros. Su reversión no reactiva permisos. No cambiar contraseñas, membresías ni prácticas. La versión incluye la tabla de cuentas solicitada anteriormente (ver CUENTAS_ESCOLARES_0_38.md).

Validación: 36 pruebas backend de cuentas/escuelas, checks, OpenAPI, TypeScript/build y dos recorridos de navegador. Restauración aislada por socket privado: 2.890 registros de 44 tablas conservados, con la única modificación prevista en revoked_at de autorizaciones cruzadas. Advertencia preexistente: fecha fija de core.Task.starts.

Publicada el 01/10/2026 con respaldo previo y sin escritores, paquete `deploy/demo/runtime/releases/0.38.1-20261001T185539Z`. Migración 0045 aplicada. Activador comprueba rutas HTTPS e inventario ajeno sin cambios. 0.38.0 preparada queda marcada como sustituida para impedir su publicación accidental.

No restaurar versiones con capacidad de compartir entre escuelas sin volver a revisar esta disposición institucional.
