# Apellidos antes de nombres — 0.40.3

Solicitud del 13/10/2026: mostrar primero apellidos y después nombres en toda la aplicación.

Formato compartido en backend (`person_name`): `last_name first_name`, conservando apellidos compuestos y datos originales; si no hay nombre, se muestra usuario. Aplicado a administración, selector de colaboradores, consultas, prácticas/alumnos/supervisores, evaluaciones e informes académicos nuevos, caja, cuenta de usuario de servicios y bandeja de solicitudes. Tablas y fichas escolares aplican el mismo formato. Caja y listas escolares ordenan por apellidos/nombres; el selector mantiene búsqueda y orden alfabético del nombre mostrado.

Formularios de alta/edición escolar, administración y portal muestran Apellidos antes de Nombre. El portal ahora captura `last_name` y `first_name` por separado. La API conserva compatibilidad con el campo histórico `name`, sin mezclarlo con los nuevos campos. Los registros antiguos cuyo nombre completo está en un solo campo se conservan literalmente hasta su corrección explícita; no se adivina dónde terminan los apellidos. Las búsquedas de cuentas admiten tanto el orden nuevo como el anterior.

Sin migraciones ni cambios a cuentas, contraseñas, permisos o separación entre escuelas. Los documentos, informes guardados y sus hashes/versiones históricas no se reescriben. Los identificadores de inicio de sesión conservan su función y formato.

Compilación y TypeScript, 56 pruebas backend y ensayo de restauración aprobados: 3.327 registros de 45 tablas conservados. Navegador del portal y recorrido completo de cuentas (alta, búsqueda, edición, baja/reactivación y teclado) aprobados. Se mantiene el estado del piloto activo y no se carga información de prueba en producción.

Paquete preparado: `deploy/demo/runtime/releases/0.40.3-20261013T171140Z`, con imágenes de backend/frontend y reversión. Publicado el 13/10/2026 tras autorización expresa, actualizando backend, frontend y worker propios; sin migraciones, cambios al gateway del host ni aplicaciones ajenas. Respaldos previo y sin escritores conservados. HTTPS autenticado verificó tablas y selectores de Salud (54 personas) y Odontología (57), orden por apellidos, búsqueda y reinicio de selección; el registro público presenta Apellidos antes de Nombre. No se enviaron asignaciones ni se crearon registros. Trece contenedores ajenos intactos. Evidencias: `selector-verification.json`, `selector-personas.png` y `verified-*.json` en el paquete.
