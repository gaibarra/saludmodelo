# Entrega 0.25 — paginación de distribución e informes recibidos

Se elimina el rechazo de consultas con más de 500 destinatarios, entregas o informes recibidos. Cada respuesta devuelve hasta 50 registros por defecto, con máximo configurable de 100. La interfaz permite cargar más registros y mantiene la selección explícita de destinatarios entre páginas; cada envío conserva el límite de 100 personas y revalida el lote completo.

## Contrato y navegación

- `GET /reports/inbox/`: devuelve `{results, next_before}`. Para continuar, usar `before=next_before`.
- `GET /reports/saved/{id}/distribution/`: conserva `eligible_recipients` y `deliveries`, y añade `next_people_after` y `next_deliveries_before`. Continuar cada listado con `people_after` o `deliveries_before`, respectivamente.
- Ambos aceptan `page_size` entre 1 y 100. Parámetros desconocidos, duplicados o inválidos se rechazan con 400. Cursor nulo indica fin.

El contrato de bandeja cambia de arreglo a objeto paginado; frontend y API deben actualizarse juntos. No requiere migración de base de datos. Los POST de entrega y lectura conservan su contrato.

Se usan identificadores ordenados: personas en ascendente y entregas en descendente. Una entrega posterior no desplaza páginas anteriores; se ve al actualizar desde el inicio. Los cursores son posiciones, no credenciales: cada consulta vuelve a aplicar permisos y estado de cuenta. Las altas y revocaciones pueden cambiar el conjunto visible; no se promete una instantánea fija durante todo el recorrido. Para revisar cambios en personas ya recorridas, actualizar la consulta.

La interfaz carga páginas adicionales bajo demanda, conserva selecciones y muestra el número seleccionado. Actualizar destinatarios o completar un envío limpia la selección. Actualizar bandeja reinicia su recorrido. Ante fallo de consulta se limpia el listado afectado. Los errores de la carga inicial cancelada no sobrescriben resultados vigentes.

## Límites y alcance

No se seleccionan ni envían destinatarios automáticamente; tampoco se activan correo, temporizadores ni servicios de producción. Esta entrega pagina únicamente la bandeja y la consulta de distribución; otros listados y las ampliaciones de capacidad, correcciones de horas, piloto institucional y módulos clínicos permanecen pendientes.

## Verificación

29 pruebas del área de informes aprobadas, incluidas nueve de distribución. Los casos nuevos recorren 505 informes recibidos y 505 destinatarios/entregas, inserción entre páginas, aislamiento de cuentas, revocación y parámetros inválidos/repetidos. Pruebas sobre PostgreSQL propio por socket Unix, detenido al finalizar.

Dos recorridos de navegador aprobados: aprobación/distribución/lectura con API real y páginas de un destinatario para comprobar selección persistente; carga adicional/reinicio de bandeja con respuestas simuladas. Compilación final 0.25 y TypeScript aprobados. OpenAPI validado sin advertencias; no hay migraciones nuevas. Fuentes originales verificadas por SHA-256. Ninguna aplicación ajena del VPS modificada.
