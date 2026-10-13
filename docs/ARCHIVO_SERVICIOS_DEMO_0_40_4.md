# Retiro operativo de servicios DEMO — 0.40.4

Solicitud del 13/10/2026: retirar los servicios DEMO para trabajar con servicios reales.

## Alcance preparado

Se identificó únicamente el servicio 1, `Odontología · DEMO`, separado de `Clínica Dental` (2). No se renombra ni se mezcla su información con el servicio real.

La migración aditiva 0047 incorpora `Service.archived_at`. Los servicios archivados desaparecen de selectores de escuela, administración, capacidad, caja y prácticas; pierden acceso operativo por funciones y no admiten solicitudes públicas. El catálogo institucional excluye registros publicados vinculados a servicios archivados. No se modifica el frontend ni sus contratos.

El comando `archive_demo_service` exige ID, nombre DEMO exacto y operador activo; por defecto sólo inspecciona. Con `--apply` registra fecha, desconfirma, incrementa versión y agrega auditoría, de forma transaccional e idempotente. No elimina ni traslada cuentas, asignaciones, cuestionarios, tareas, auditoría ni fuentes. Las funciones antiguas quedan inoperantes por el filtro del servicio archivado.

El servicio inspeccionado conserva 4 funciones históricas, 6 cuestionarios, 4 tareas, 26 eventos de auditoría, 2 eventos de gobierno previos y 5 distribuciones de capacidad. No contiene prácticas académicas ni turnos de caja. No se cambian los otros siete servicios, las cuentas ni sus contraseñas.

Aporte técnico a ODO-OBJ-11: conservación y trazabilidad del retiro. No constituye cumplimiento completo del objetivo ni validación institucional del expediente clínico.

## Validación y paquete

- Compilación Next.js y TypeScript aprobadas; frontend publicado 0.40.3 reutilizado.
- Restauración privada de PostgreSQL por socket Unix: 3.329 registros originales/45 tablas con datos conservados tras la migración. Archivo ensayado únicamente en esa copia, comparando todas las filas originales; sólo cambian confirmación y versión del servicio 1, además del nuevo campo y evento.
- 76 pruebas Django aprobadas, comprobaciones de Django/migraciones y esquema OpenAPI sin errores: archivo, idempotencia, conservación, rechazo de servicios reales, selectores, acceso directo, confirmación, asignación, solicitudes, aislamiento escolar y regresiones relacionadas.
- Se corrigieron fechas de inicio de funciones en la fixture de capacidad: escenarios fijos de octubre de 2026 no podían depender del día actual. No afecta datos de producción.
- Paquete: `deploy/demo/runtime/releases/0.40.4-20261013T173646Z`, con respaldo `preparation.dump`, ensayo, imágenes inmutables y reversión.

Estado: **publicado y aplicado el 13/10/2026**, tras autorización expresa del usuario para publicar 0.40.4 y aplicar el retiro.

## Aplicación tras autorización

1. Ejecutar `python3 deploy/demo/redeploy-pilot.py check <paquete>` y luego `activate <paquete>`. El runner respalda de nuevo y detiene sólo backend/worker propios durante la migración. Conserva la imagen del frontend, puertos, certificados y configuración del VPS. No ejecuta semillas.
2. En el backend actualizado ejecutar primero inspección y luego:
   `python manage.py archive_demo_service --service 1 --expected-name 'Odontología · DEMO' --actor gibarra@modelo.edu.mx --apply`.
3. Verificar por HTTPS, sin crear asignaciones: Odontología ofrece únicamente `Clínica Dental`; Salud conserva sus servicios; no hay DEMO en los selectores. Comprobar inventario de contenedores ajenos y guardar evidencia en el paquete.

Reversión: conservar base actual, historial y columna aditiva; nunca restaurar automáticamente un respaldo anterior. La imagen 0.40.3 no entiende el archivo y podría volver a mostrar DEMO si se revierte el código: revisar expresamente este efecto, manteniendo la desconfirmación y sin borrar datos. No reactivar cuentas DEMO.

## Resultado de publicación

Migración 0047 aplicada y servicio 1 archivado a las 17:42:29 UTC del 13/10/2026. Se comprobaron dentro de la transacción las cuentas, todos los registros relacionados (excepto el nuevo evento de auditoría) y los demás servicios: sin cambios. Respaldos previo y sin escritores conservados en el paquete; ninguna restauración de base.

HTTPS autenticado verificó que Odontología ofrece sólo `Clínica Dental` y Salud conserva sus cinco servicios; el acceso administrativo directo al servicio archivado devuelve 404. No se crearon asignaciones ni cuentas de prueba. Evidencia: `archive-https.json` y `servicios-reales.png` en el paquete.

Se actualizaron backend y worker; el contenedor frontend permaneció intacto. Trece contenedores ajenos sin cambios, sin modificaciones de puertos, certificados ni configuración del VPS. Comprobaciones de disponibilidad y preflight final aprobadas.
