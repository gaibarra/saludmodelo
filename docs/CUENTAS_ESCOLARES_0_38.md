# Tabla de cuentas escolares — 0.38.0

En Escuelas, dentro de Administración, «Abrir tabla de registrados» permite consultar las cuentas vinculadas a la escuela. Permanece plegada inicialmente para priorizar la captura. El enlace Crear cuenta lleva al formulario existente.

Funciones: búsqueda por nombre completo, usuario o correo; filtro Todos/Activos/Dados de baja; páginas de 50 registros; detalle; edición de usuario, nombre, apellidos y correo; baja lógica y reactivación con motivo. La baja bloquea el acceso, elimina sesiones y conserva identidad, membresías, asignaciones, prácticas y evaluaciones. Reactivar no restaura sesiones anteriores, pero vuelve a permitir acceso según permisos y vigencias conservados. No se cambian contraseñas desde esta tabla.

Sólo Dirección con autoridad de administración ve el directorio. Una autorización de consulta académica no habilita lectura ni escritura de cuentas de otra escuela. El servidor vuelve a comprobar alcance en cada acción. Cuentas propias, de autoridad, staff/superusuario y cuentas con membresías, funciones o vínculos académicos fuera de la escuela son consultables pero no modificables por esta vía; requieren gestión institucional.

Ediciones y cambios de estado tienen motivo y registro de auditoría. Un token firmado derivado de la versión de datos evita sobrescrituras; se devuelve conflicto si la cuenta cambió. No se exponen hashes de contraseña ni se aceptan atributos de privilegios en payloads. Se preservan formularios y flujos académicos existentes.

APIs: GET `schools/{id}/accounts/`, GET/PATCH/DELETE `schools/{id}/accounts/{user}/`, POST `schools/{id}/accounts/{user}/reactivate/`. DELETE es baja lógica, nunca borrado físico. Parámetros de listado: `q`, `state=all|active|inactive`, `page`.

No requiere migraciones nuevas: esquema 0044. La publicación del código no crea, edita, elimina ni reactiva usuarios; esas acciones corresponden a operadores autorizados desde la interfaz.

Estado y evidencia de despliegue: `deploy/demo/REDEPLOY_0_38.md`.
