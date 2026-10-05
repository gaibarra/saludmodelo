# Psicología / La Casita — 0.37.0 publicada

Solicitud: incluir Psicología en código y base de datos como servicio de la Escuela de Salud.

Se conserva el identificador del Service vinculado a `modelo-usc-casita`; no se crea un segundo servicio. La ficha se presenta como «Psicología · USC Casita», área principal `psicologia`, área adicional `atencion-comunitaria`. Ambas pestañas muestran la misma ficha, sin duplicarla en el directorio general ni en los totales de Escuela. Los módulos de administración, colaboradores, tareas y prácticas siguen utilizando la misma clave foránea.

La migración aditiva `0044_institutional_service_areas_sources` agrega áreas y fuentes adicionales a InstitutionalService. La importación revisada usa `institutional_services_20261001.json` y conserva la fuente original del 30/09. Añade el directorio estatal 2024 (página 48), archivado en `docs/fuentes-institucionales/psicologia-casita-2026-10-01.pdf`, SHA256 `5bc1d514b8faad3d0253e865884f9702658f9f56db937fa84329d0926b1364db`.

Fuente: https://www.yucatan.gob.mx/docs/air/AIR_1699_2.pdf. Documenta servicio psicológico al público general en La Casita. La adscripción a Salud sigue la instrucción del usuario del 01/10/2026. No se trasladan teléfonos de longitud dudosa ni direcciones correspondientes a otras instituciones. Se conservan contacto y horarios generales de La Casita publicados por Universidad Modelo, aclarando que la disponibilidad específica, modalidades y responsables de Psicología deben confirmarse.

El nombre operativo se actualiza sólo si sigue siendo exactamente «USC Casita» y aumenta su etag; los nombres personalizados se respetan. No cambia confirmación operativa, publicación, slug de citas, sede, asignaciones, permisos, alumnos ni participaciones. La confirmación pública del servicio no activa solicitudes de pacientes ni captura clínica. No se cambian autorizaciones académicas entre escuelas.

## Validación

- 36 pruebas backend de catálogo/portal/escuelas aprobadas, checks, ausencia de migraciones de código faltantes y OpenAPI.
- Compilación Next.js / TypeScript aprobada.
- Recorrido aislado de navegador: Psicología y Atención Comunitaria comparten una ficha, seis fichas generales, fuentes, contactos, móvil y permisos de escuelas.
- Restauración de respaldo en PostgreSQL temporal por socket privado, sin TCP. Migración e importación con la imagen preparada; segunda ejecución sin duplicaciones.
- 2.869 registros originales de 44 tablas pobladas retenidos; comparación campo a campo, permitiendo únicamente nombre/etag del Service Casita y contenido público/área/procedencia de su ficha. No se crean Service adicionales. Las decisiones operativas existentes se conservan.
- Advertencia preexistente de Django: `core.Task.starts` tiene valor de fecha fijo. Fuera del alcance de este cambio.

## Estado de publicación

Publicada el 01/10/2026 tras autorización explícita del usuario para desplegar y aplicar la migración con respaldo previo y breve interrupción sólo de Salud Modelo. Migración 0044 aplicada; `migrate --check` sin pendientes. La carga modificó exclusivamente `modelo-usc-casita`, sin crear servicios ni restablecer cuentas.

Respaldo previo y respaldo sin escritores conservados en el paquete privado. Verificación HTTPS y navegador: ficha única en Psicología y Atención Comunitaria, seis fichas generales, adscripción a Salud, procedencia visible y móvil sin desbordamiento. Solicitudes de pacientes siguen deshabilitadas. Once contenedores ajenos y db/gateway propios conservan inventario completo (identidad, inicio, imagen, puertos y montajes).

El rechazo inicial del control automático quedó resuelto con la autorización expresa posterior. Ver `deploy/demo/REDEPLOY_0_37.md` para operación y evidencia.
