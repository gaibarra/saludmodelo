# Entrega 0.26 — correcciones de horas con historial

En Seguimiento → Revisar tarea → Actividad y tiempo registrado, la persona que registró una entrada puede corregir sus minutos y justificar el ajuste. El registro original conserva fecha, tarea, autor, minutos y nota. Cada ajuste añade una versión con minutos efectivos, motivo, autor y fecha; los eventos de tarea registran la operación.

## Reglas

- Sólo el autor original, con cuenta activa y rol de trabajo vigente en el servicio, puede ajustar. Una suplencia, rol de Dirección o cuenta técnica no permite corregir registros ajenos.
- Minutos efectivos entre cero y 1440. Cero anula el cómputo sin borrar la entrada; un ajuste posterior puede restablecer minutos. Un ajuste sin cambio o sin motivo se rechaza.
- Se comparte el bloqueo de servicio → tarea → persona con las altas de tiempo. El total efectivo diario de la persona, sumado entre tareas/servicios, no puede superar 1440 minutos. Correcciones y nuevos registros usan el mismo cálculo.
- La versión observada evita sobrescribir un ajuste concurrente. La repetición exacta del último ajuste devuelve el mismo resultado; una versión desactualizada incompatible recibe 409.
- Se permite corregir registros de tareas cerradas o canceladas, conservando el estado y línea base de la tarea. No modifica estimaciones, calendario ni capacidad aprobada.

Tablero, detalle y nuevos informes semanales suman minutos efectivos. El informe conserva los minutos originales y añade valor efectivo y versión del ajuste en cada entrada exportada. La cifra corresponde al estado observado al generar el informe; no reconstruye el valor conocido en el cierre histórico. Los informes ya guardados mantienen su contenido y huella: para reflejar una corrección, generar y revisar otro informe y, si procede, sustituir explícitamente el anterior.

## API y operación

`POST /api/v1/tracking/time/{id}/correct/` recibe `version`, `minutes` y `rationale`, y devuelve el detalle de tarea actualizado. La migración aditiva 0033 crea `TimeCorrection`, con unicidad por entrada/versión y relaciones protegidas. No reescribe entradas existentes.

La pantalla muestra hasta cien entradas por tarea y cien ajustes por entrada; el historial anterior se conserva en base. Paginación de ese historial sigue pendiente. Para corregir fecha o tarea, anular el registro y capturar una nueva entrada con los controles habituales; no existe traslado automático ni una transacción conjunta entre esas dos acciones.

Esta entrega cubre ajustes de minutos por su autor. Una solicitud para corregir registros de personas sin acceso, aprobación administrativa de ajustes y cierres contables requieren un procedimiento institucional adicional. No hay integración con nómina, caja ni módulos clínicos.

## Verificación

236 pruebas de regresión del servidor aprobadas, incluidas seis nuevas de correcciones: historia, idempotencia/conflicto, permisos, desactivación, límites diarios combinados con altas, concurrencia e informes conservados. Recorrido de navegador con API real aislada aprobado: 60 → 25 → 0 minutos, original y ambos ajustes visibles. El primer intento de navegador usó por error un selector de avisos; se corrigió para usar el botón de tarea y se repitió satisfactoriamente.

Build 0.26/TypeScript aprobado; OpenAPI validado sin advertencias y sin migraciones pendientes de generar. 0033 aplicada sólo en la base propia por socket Unix, clúster detenido al finalizar. Fuentes DOCX/prompt intactas por SHA-256. No se modificaron otras aplicaciones del VPS ni se activó producción. El recorrido emplea una entrada sintética del inicio del plan cargada por la fixture; no acredita horas institucionales trabajadas antes de esa fecha.
