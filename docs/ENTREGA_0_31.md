# Entrega 0.31 — historial completo de informes

La consulta de informes conservados deja de fallar al superar 500 versiones. Ahora muestra páginas de 50 registros, con opción de cargar versiones anteriores. La API admite páginas de hasta 100. Cada consulta comprueba nuevamente el permiso de lectura del servicio.

## Uso

En Informes → Versiones conservadas y revisión, «Cargar más versiones conservadas» incorpora registros anteriores sin perder las páginas ya consultadas. «Actualizar versiones» vuelve al inicio para mostrar las altas recientes. Una versión abierta sigue siendo consultable mientras conserve permisos; una operación fallida limpia los resultados de la pantalla y muestra el error para que se actualicen.

La sustitución dispone de «Buscar sustitutos aprobados» y «Cargar más sustitutos aprobados». Consulta directamente los informes aprobados, conservados y del mismo período, excluyendo el informe que se quiere sustituir. La búsqueda no depende de las versiones visibles en el listado principal. Permite elegir una versión antigua sin cargar todo el archivo. Al actualizar la búsqueda se limpia la selección; mientras se consulta una página se bloquea el botón de retiro/sustitución para evitar enviar una decisión incompleta.

El servidor conserva las comprobaciones de aprobación, integridad, servicio, período, retiro previo y permisos antes de registrar la sustitución. Que una versión aparezca como candidata no garantiza que siga siendo elegible al confirmar: si se retira o cambia su estado, la operación se rechaza. No se modifica el contenido ni la huella de informes históricos.

En Programación de informes se conserva el resumen de veinte borradores y se añade «Historial completo de borradores programados y recuperados». Permite llegar a todos los registros mediante páginas e indica semana, origen automático o recuperación explícita, configuración, motivo, estado actual del informe y enlace a la versión conservada. Es el historial de generaciones que produjeron un borrador; no pretende ser un registro completo de todos los intentos fallidos del trabajador.

## Contrato API

- `GET /api/v1/reports/services/{id}/saved/` devuelve `{results, next_before}`. Sustituye la respuesta anterior que era una lista. Parámetros opcionales: `before`, `page_size`, `start`, `state`, `retained_only`, `exclude`.
- `GET /api/v1/reports/services/{id}/schedule/runs/` devuelve `{results, next_before}`. Parámetros: `before`, `page_size`.
- Tamaño predeterminado 50, máximo 100. Cursores enteros positivos por identificador descendente. Parámetros inválidos, desconocidos o repetidos se rechazan.
- El orden del historial completo es por registro de generación; una recuperación reciente de una semana antigua aparece entre los registros nuevos. El resumen de veinte mantiene su orden previo por período.

No se promete una instantánea entre páginas. Altas posteriores a la primera página se ven al actualizar el inicio; cambios de estado o permisos se observan en las nuevas consultas. La paginación evita duplicar o saltar registros por desplazamiento cuando se incorporan informes nuevos. La búsqueda de sustitutos aplica los filtros antes de paginar.

## Operación y alcance

Sin migración. API e interfaz deben publicarse juntas por el cambio de respuesta del listado. No se activaron trabajadores, programación real ni canales de envío; no se desplegó a producción ni se alteraron servicios ajenos del VPS.

Esta entrega completa la navegación del archivo de informes; no añade frecuencias mensuales, informes integrales de IA ni avisos externos. Esas ampliaciones, retención documental, recuperación de cuentas excluidas/contraseñas, piloto humano y módulos clínicos permanecen pendientes.


## Verificación

41 pruebas del área de informes aprobadas, incluidas seis nuevas de navegación por cursores, archivo de más de 500 versiones, filtros de candidatos, rechazo de parámetros inválidos/repetidos, revocación de permisos y sustitución invalidada después de seleccionar. Se incluyeron pruebas existentes de conservación, disposición, programación, recuperación y distribución.

Cinco recorridos de navegador con API real aprobados: informe semanal, conservación/revisión, sustitución/retiro, configuración semanal y archivo grande con candidatos e historial en páginas posteriores. Compilación final 0.31/TypeScript y OpenAPI sin advertencias, correctos. Sin migraciones pendientes de generar.

No se repitió la suite global de módulos ajenos: la regresión de esta entrega se concentró en el área modificada. Pruebas ejecutadas con PostgreSQL temporal por socket Unix y servidores propios; recursos detenidos/eliminados al terminar. Fuentes originales intactas por SHA-256. No se modificaron aplicaciones ajenas del VPS ni se activó producción.
