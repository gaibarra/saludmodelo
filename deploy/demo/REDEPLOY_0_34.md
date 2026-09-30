# Redespliegue preparado — 0.31 → 0.34

Estado actualizado al 30/09/2026: **paquete superado por el nuevo requisito de escuelas independientes; activación bloqueada**. La preparación técnica descrita abajo se conserva como antecedente, pero ya no representa una entrega lista para publicar. Ver `docs/ESCUELAS_INDEPENDIENTES.md`. La demo pública permanece en 0.31 y responde por HTTPS. Este documento cubre exclusivamente `salud-modelo-demo` en `plansaludmodelo.online`.

## Paquete preparado

Directorio privado:

`/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.34.0-20260930T145038Z`

Contiene el manifiesto con identificadores inmutables de imágenes, configuraciones de actualización/reversión, respaldo PostgreSQL, copia de archivos privados y configuración, hashes y resultados de verificación. Sus archivos tienen permisos 600 y están dentro de runtime privado. No compartir el directorio: contiene configuración y respaldos sensibles.

- Imágenes nuevas: `salud-modelo-demo-backend:0.34` y `salud-modelo-demo-frontend:0.34`. El despliegue usa sus identificadores SHA del manifiesto, no depende de que las etiquetas sigan apuntando a ellas.
- Versiones anteriores conservadas para volver a 0.31.
- Migraciones: 0039 portal, 0040 núcleo académico y 0041 competencias/informes. Son aditivas; la nueva columna de servicio admite nulos y no exige que el código 0.31 la escriba.
- Ensayo de restauración/migración: 2.650 registros originales de 39 tablas conservados, checks correctos, PostgreSQL temporal sin TCP. No se migró la base activa.
- Imágenes comprobadas en contenedores efímeros sin red, sin puertos del host y sin montajes de la base activa: backend, catálogo de seis servicios y siete rutas de interfaz, incluida portada PNG.
- Compilación demo 0.34 correcta; incorpora archivos públicos que faltaban en la receta anterior.
- Inventario final: cinco contenedores propios y once ajenos sin cambios. HTTPS de la demo comprobado.

## Comprobación previa (sólo lectura de servicios)

Desde `/home/gaibarra/plandetrabajo`:

```bash
python3 deploy/demo/redeploy.py check deploy/demo/runtime/releases/0.34.0-20260930T145038Z
```

Ya ejecutada satisfactoriamente. Comprueba imágenes nuevas y anteriores, hashes de configuraciones y respaldos, ensayo de restauración, cinco servicios esperados, volúmenes propios y puerto exclusivo `127.0.0.1:3117`. PostgreSQL debe conservar `network_mode: none`. Si cambian los contenedores o la configuración antes de activar, detenerse y preparar de nuevo; no eludir los controles ni editar hashes para hacerlos pasar.

## Activación preparada (todavía no ejecutada)

Ejecutar cuando se autorice actualizar esta demostración. Puede haber una breve interrupción de sus pantallas mientras se reemplazan los contenedores propios.

```bash
python3 deploy/demo/redeploy.py activate deploy/demo/runtime/releases/0.34.0-20260930T145038Z
```

El script:

1. Repite las comprobaciones y toma otro respaldo de la base inmediatamente antes del cambio.
2. Pausa únicamente el worker de la demo y aplica las migraciones desde la imagen nueva.
3. Sustituye sólo backend, frontend y worker, sin reconstruir imágenes ni recrear db o gateway.
4. Comprueba las nuevas aplicaciones y recarga únicamente el Nginx del **contenedor gateway de esta demo**, para actualizar las direcciones internas.
5. Verifica por HTTPS portada, portal, pantallas académicas, imagen y catálogo. Confirma que no se habilitó recepción de pacientes y compara el inventario de aplicaciones ajenas.

No requiere sudo, Certbot ni modificar/recargar Nginx del host. No ejecutar `activate-domain.sh` para esta actualización. No se usa `compose down`, no se eliminan volúmenes y no se ejecuta el cargador inicial. Las cuentas, contraseñas, MFA y datos existentes se conservan. El registro de pacientes y la IA externa quedan explícitamente apagados.

Después de activar, completar el recorrido autenticado:

```bash
node deploy/demo/smoke.mjs public
```

Usa los accesos privados existentes y no los imprime. Además, ingresar con Dirección a **Prácticas académicas → Competencias e informes de cierre**. Los módulos nuevos estarán inicialmente vacíos: la actualización no crea alumnos ni ciclos ficticios adicionales. Registrar un ejemplo sintético mediante la interfaz si se desea una presentación con datos académicos.

## Reversión del código

Ante un fallo de la activación, el script intenta recuperar automáticamente las tres imágenes anteriores. Para una reversión explícita después de una activación exitosa:

```bash
python3 deploy/demo/redeploy.py rollback deploy/demo/runtime/releases/0.34.0-20260930T145038Z
```

La reversión conserva el esquema ampliado y todos los registros. Las pantallas nuevas dejan de estar disponibles en 0.31, pero sus datos permanecen. No hace `pg_restore` ni retrocede migraciones: restaurar una copia sobre una base que ya recibió cambios podría perder registros y requeriría un procedimiento separado. La recuperación completa de base fue ensayada sólo en el entorno temporal.

Si falla también la reversión, revisar exclusivamente los logs de backend, frontend, worker y gateway de `salud-modelo-demo`. No intervenir aplicaciones ajenas. El script exige que las imágenes activas correspondan al paquete para evitar revertir por error una actualización posterior.

## Operación posterior

`compose.yaml` conserva las etiquetas originales 0.31 como referencia de instalación. Después de activar, cualquier futuro comando que recree servicios deberá incluir el archivo `release.compose.json` del directorio activo o una nueva entrega preparada; no usar un `compose up` genérico contra la base original.

Para reconstrucciones futuras, usar `build-release-image.py`: envía un contexto limitado por imagen compatible también con Docker clásico, sin runtime ni secretos. El frontend requiere compilar antes con `SALUD_DEMO_BUILD=1 NEXT_PUBLIC_DEMO_MODE=1 npm run build`. Un cambio de código requiere nuevas imágenes, ensayo y manifiesto; no reutilizar este manifiesto para código distinto.

Esta preparación no equivale a habilitar datos reales, aceptar institucionalmente el piloto ni terminar el alcance clínico. Resumen funcional: `docs/RESUMEN_2026_09_30.md`.
