# Corrección de nombres — 0.39.3 publicada

Las cuentas ordinarias ya admitían edición de nombre/apellidos en «Editar». Las protecciones de cuentas propias y de autoridades impedían incluso esta corrección de captura. Se agrega «Corregir nombre», con modal limitado a nombre, apellidos y motivo, para cuentas protegidas elegibles.

Dirección puede corregir su propio nombre; administración institucional puede corregir nombres de autoridades registradas de sus instituciones, sin conceder edición general ni baja de esas cuentas. Las cuentas compartidas fuera del alcance institucional y las cuentas administrativas de mayor privilegio siguen protegidas; un director no obtiene acceso a la otra escuela. Las cuentas ordinarias conservan su edición existente.

Endpoint PATCH de nombre separado, con lista estricta de campos, revisión de concurrencia y auditoría de antes/después, actor y motivo. Usuario de acceso, correo, contraseña, estado y permisos no cambian; la corrección tampoco reescribe documentos históricos conservados. Sin migración y sin modificar nombres reales durante las pruebas.

38 pruebas backend de cuentas/escuelas, checks/OpenAPI y build/TypeScript aprobados. Publicada 0.39.3 tras autorización expresa del usuario.

Pruebas navegador de corrección protegida y CRUD aprobadas, incluyendo recarga/móvil. Captura sintética: docs/capturas/corregir-nombre-0.39.3.png. Ensayo de restauración preservó 2.884 filas originales, esquema 0046 intacto. Paquete preparado y verificado: 0.39.3-20261001T204011Z, publicado con respaldo previo y sin escritores. HTTPS autenticado confirma modal en ambas escuelas, sin cambios reales enviados ni reactivación de cuentas DEMO. Once contenedores ajenos intactos.
