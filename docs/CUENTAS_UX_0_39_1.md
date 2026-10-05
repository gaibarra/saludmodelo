# Directorio y modales de cuentas — 0.39.1

Mejora visual de la sección «Alumnos y colaboradores» en Escuelas. Tabla visible inicialmente, encabezado con acción principal Crear cuenta, filtros agrupados, filas espaciadas, identidad/contacto agrupados, estados visuales y paginación secundaria. Las restricciones institucionales aparecen resumidas en la fila y completas en el detalle, sin ocupar la columna de acciones con párrafos.

Crear, consultar, editar, confirmar baja y reactivar utilizan ventanas modales nativas. El fondo queda fuera de interacción mientras están abiertas; Escape permite cerrar, se devuelve el foco al botón de origen y se pide descartar explícitamente cambios sin guardar. No se cierra una ventana durante un guardado. Los errores se muestran dentro de la ventana y se conservan los campos. El alta sustituye el formulario separado existente. La membresía escolar y los permisos siguen siendo los del servidor actual; sin cambios de API, base de datos, contraseñas o reglas de seguridad.

Publicación exclusivamente frontend. Backend/worker/db permanecen 0.39.0 y esquema 0046. El preparador de parches admite que las versiones actuales no tengan bootstrap.json; no genera ni ejecuta configuración de cuentas.

Validación final aprobada: build/TypeScript y navegador CRUD completo, Escape/restauración de foco, descarte explícito y móvil/teclado. Capturas sintéticas revisadas visualmente: `docs/capturas/cuentas-escolares-0.39.1.png` y `docs/capturas/cuenta-modal-0.39.1.png`. Paquete final 0.39.1-20261001T193003Z, publicado tras autorización expresa; frontend 0.39.1 activo, backend/esquema sin cambios. Verificación autenticada HTTPS de tabla/modales/Escape/móvil aprobada sin crear ni modificar cuentas.
