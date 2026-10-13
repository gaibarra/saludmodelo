# Cuentas de colaboradores de Salud — 13 de octubre de 2026

Solicitud: crear las cuentas de `Salud_colaboradores.xlsx`, excepto LEON PINTO CARLA AMIRA, con la contraseña provisional indicada expresamente por el usuario. El libro contiene 54 personas: 53 altas previstas y una exclusión.

Se utiliza el correo normalizado como usuario y se conserva el nombre de la fuente, incluido el apellido compuesto SAN ROMAN. Se cargan únicamente nombre, apellidos y correo; la clave de origen y huella SHA-256 quedan en la auditoría. RFC, CURP, IMSS y datos laborales no se importan.

Las cuentas se vinculan exclusivamente a Salud, sin privilegios administrativos, mandatos ni asignaciones clínicas automáticas. No se comparte la cuenta del personal con Odontología. Las cuentas existentes no se modifican ni se restablecen sus contraseñas.

Se reutiliza el cambio de contraseña personal publicado en 0.40.1: acceso del personal → Cambiar contraseña. La contraseña provisional se recibe en memoria, se almacena mediante el hash de Django y no se incluye en código, reportes o auditoría. La excepción de alta no modifica los validadores de las contraseñas posteriores.

Procedimiento: previsualización de duplicados, respaldo, ensayo de restauración/importación en PostgreSQL privado por socket Unix, segunda ejecución sin duplicados y comprobación explícita de exclusión de Carla. Aplicación del lote en una transacción con respaldo inmediato previo y conservación comprobada de las cuentas existentes. Inventario de contenedores comparado antes y después; sin despliegues, migraciones o reinicios.

Herramientas: `deploy/demo/import-health-accounts.py`, `run-health-import.py`, `rehearse-health-accounts.py` y `verify-health-accounts.cjs`. Datos mínimos y evidencias privados en `deploy/demo/runtime/salud-20261013/`. El importador debe utilizarse sólo para este lote autorizado; no envía correos.

Estado: completado el 13/10/2026. Se crearon 53 cuentas y se conservaron intactas las 65 preexistentes. La comprobación posterior encontró cero altas pendientes y 53 coincidencias. El ensayo aislado conservó 3.112 registros originales de 45 tablas, creó 53 cuentas y omitió las mismas 53 en la segunda ejecución; también verificó el rechazo de Carla como candidata al alta. HTTPS confirmó ingreso y formulario de cambio de contraseña, sin modificar la contraseña provisional. Los 18 contenedores activos permanecieron intactos.

Relación entregada: `entregables/salud/Cuentas_colaboradores_2026-10-13.csv`, sin contraseñas. Respaldo previo `before-accounts.dump`, ensayo `rehearsal.json` y reportes `created.json`, `preview.json`, `https-verification.json` conservados en el directorio privado del lote.
