# Cuentas de colaboradores de Odontología — 0.40.1

Solicitud del 13/10/2026: crear las cuentas del archivo `Cirujano destista_colaboradores.xlsx`, excluyendo a SOSA CORREA MARIO, cuya cuenta ya está activa. El archivo contiene 57 personas; se preparan 56 altas con el correo normalizado como usuario. Se conserva el nombre del documento y se contempla el registro con un solo apellido. No se importan RFC, CURP, IMSS, horas ni datos laborales.

Cada alta se vincula únicamente a la institución y a la Escuela de Odontología. No se otorgan mandatos administrativos, funciones clínicas ni acceso a otra escuela. Esas asignaciones permanecen como decisiones de Dirección. El importador verifica duplicados, conserva todas las cuentas preexistentes y registra auditoría por alta con huella de la fuente y clave del colaborador. No envía correos.

La contraseña provisional indicada expresamente por el usuario se aplica sólo a estas nuevas cuentas mediante hash Django, como excepción de alta a la longitud mínima habitual. No se almacena en el código, archivos de reporte ni auditoría; no se desactivan los validadores generales. Las contraseñas existentes, incluida la de Mario, no se restablecen.

Se agrega cambio de contraseña personal en `/seguridad`, con enlace visible desde `/personal`. Endpoint `POST /api/v1/security/password/`: sesión autenticada, CSRF, contraseña actual, nueva contraseña y confirmación; valida longitud y reglas generales. Sólo modifica al usuario autenticado, con límite propio de cinco intentos por minuto. Conserva la sesión utilizada e invalida las demás mediante la comprobación del hash de sesión de Django; registra `password.changed` sin guardar secretos. No incorpora restablecimiento administrativo ni obliga automáticamente a cambiar la contraseña al primer acceso.

Validación: 31 pruebas backend de contraseña/cuentas escolares/MFA, checks Django, OpenAPI y compilación frontend aprobados; navegador contra API y PostgreSQL aislado verifica cambio y reingreso. Importación ensayada sobre respaldo restaurado en socket Unix privado, incluyendo segunda ejecución sin duplicados ni restablecimiento de contraseñas.

Relación con ODO-OBJ-11: aporta identidad, acceso individual y trazabilidad de cuentas. No constituye implementación ni validación completa de la protección del expediente clínico.

Estado de publicación y altas: ver `deploy/demo/REDEPLOY_0_40_1.md`.
