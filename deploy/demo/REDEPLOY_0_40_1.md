# Alta de colaboradores y cambio de contraseña — 0.40.1

Preparación: `prepare-account-password.py`; activación con `redeploy-pilot.py` sobre el paquete generado. Se conservan las banderas del piloto 0.40.0, sin migraciones, bootstrap ni datos simulados en vivo. Copias previas y reversión exclusiva de imágenes/configuración, conservando la base y las cuentas posteriores.

Las altas usan `run-dental-import.py`: primero previsualización, después respaldo exclusivo de la base propia y carga transaccional con contraseña recibida por stdin. Reportes y datos mínimos en `runtime/odontologia-20261013/`, con permisos privados. No ejecutar sin la autorización específica del lote. El importador omite cuentas coincidentes ya vinculadas y nunca restablece sus contraseñas.

Estado: publicada el 13/10/2026 tras autorización expresa «Sí, publicar 0.40.1». Paquete `runtime/releases/0.40.1-20261013T155757Z`. La revisión automática rechazó inicialmente el despliegue por requerir autorización específica; resuelto con la confirmación del usuario.

Restauración aislada: 2.888 registros originales de 45 tablas conservados. Ensayo de importación: 56 creados y 56 omitidos en segunda ejecución, nueve cuentas preexistentes intactas. En vivo: 56 altas transaccionales; nueve cuentas preexistentes intactas, Mario excluido, cero funciones asignadas. Respaldo `runtime/odontologia-20261013/before-accounts.dump` y respaldos posteriores previos a la publicación. Verificación posterior sin escrituras: cero altas pendientes y 56 coincidencias. HTTPS confirma ingreso y formulario de cambio con una nueva cuenta; su contraseña no se modificó. Esquema 0046 sin pendientes; 13 contenedores ajenos intactos.

Relación de acceso sin contraseñas: `entregables/odontologia/Cuentas_colaboradores_2026-10-13.csv`. Evidencias privadas: `created.json`, `preview.json`, `https-verification.json` y `password-form.png` en `runtime/odontologia-20261013/`.
