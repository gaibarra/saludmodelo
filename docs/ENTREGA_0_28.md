# Entrega 0.28 — controles para cierre del gestor de planificación

## Reservas, presupuesto y ausencias

Las propuestas de línea base admiten reservas explícitas por fecha, responsable o suplente de tarea. Deben sumar exactamente la estimación y pertenecer al intervalo de la tarea. Dirección simula o aprueba; la simulación ejecuta la misma validación y revierte todas las escrituras. La aprobación independiente guarda reservas actuales y trazabilidad de versiones de capacidad en los eventos.

La aprobación usa bloqueo institucional antes del servicio/tarea. Revalida calendario, nombramientos, capacidad aprobada y minutos disponibles para cada persona/servicio/día; dos aprobaciones concurrentes no pueden ocupar la misma disponibilidad. Las reservas de tareas aceptadas permanecen contabilizadas para no reutilizar minutos ya comprometidos; cancelar conserva historia y libera la reserva vigente.

En Capacidad, una persona con mandato institucional confirma presupuestos base/reserva y puede activar el control obligatorio. Los datos previos permanecen compatibles durante la regularización: antes de activar, todas las tareas abiertas con esfuerzo deben tener reservas completas. No se convierten automáticamente las 354 horas provisionales en autorización. Cada cambio de control conserva valores previos/nuevos y motivo en auditoría.

La indisponibilidad aprobada puede crear conflicto en compromisos anteriores: se muestra en el control, sin borrar reservas ni rechazar el registro de una ausencia real. Cambios de línea base pueden resolver conflictos por etapas, pero no crear o agravar ninguno. La redistribución se realiza proponiendo fechas/responsable/suplente y nuevas reservas, con revisión independiente; no se modifica la titularidad al actuar por suplencia.

El control distingue minutos estimados comprometidos, presupuesto aprobado, saldo y minutos reales efectivos de las categorías base/reserva. Cada entrada de tiempo conserva su categoría al registrarse; una reclasificación posterior de tarea no mueve retroactivamente horas anteriores. Las correcciones de minutos siguen imputadas a esa categoría. Horas anteriores a esta entrega se clasifican como base; no se inventa consumo histórico de reserva. El saldo resta el mayor entre compromiso y tiempo real de cada tarea, y también conserva el tiempo real de tareas canceladas; cancelar no permite gastar de nuevo presupuesto ya consumido. Horas reales no se bloquean por exceder presupuesto: representan hechos declarados, no permisos de planificación.

## Dependencias entre servicios

Se permiten predecesoras de la misma institución para las que el proponente tiene lectura. El revisor debe tener autoridad en ambos servicios. Se conserva validación de fechas, ciclos, cierre previo y reapertura de sucesoras. Las mutaciones de grafo/línea base usan bloqueo institucional. No se admite dependencia entre instituciones. La selección sólo muestra tareas dentro del alcance de lectura; no expone títulos de servicios ajenos por errores.

## Historial completo

La consulta por tarea pagina actividad, cambios de línea base, horas y ajustes mediante identificadores descendentes, 50 registros por página. Permite llegar a entradas anteriores a los cien registros del resumen y corregir horas propias desde ese historial. Cada página vuelve a validar acceso. El resumen conserva su límite; el historial nuevo no tiene ese corte total.

## Cambios de fuente

Dirección puede proponer una versión posterior de la misma pregunta perteneciente al catálogo autorizado. Otra persona de Dirección con lectura revisa el cambio observado. Se comprueban versión y autorización del catálogo nuevamente al aprobar. La aprobación conserva fuentes y revisiones anteriores, atribuye origen a las ayudas antiguas, cambia la fuente vigente y retira publicación/validación actual. Una nueva ayuda debe guardarse, revisarse y publicarse; la respuesta debe guardarse contra la ayuda vigente antes de volver a enviarse. La importación de un DOCX sigue siendo un procedimiento explícito, no una sustitución automática.

## Operación y límites de cierre

Migraciones aditivas 0034–0036. API e interfaz deben publicarse juntas. No se activó control sobre instituciones reales, trabajadores, canales externos ni despliegue. Límites: 500 filas de reserva por tarea; catálogo de dependencias de hasta mil opciones con rechazo explícito del exceso; las reservas son minutos diarios, no citas o franjas de agenda clínica.

No se declara cierre institucional. El piloto será definido en la reunión indicada en REUNION_CIERRE_2026_09_29.md. Quedan como decisiones/requisitos de puesta en uso: presupuestos reales, activación del control tras regularizar tareas, usuarios y revisión de fichas, canal externo con datos y autorización, procedimientos excepcionales, entorno aislado y aceptación del piloto. El alcance clínico completo permanece pendiente.

## Verificación final

254 pruebas de regresión completa del servidor aprobadas. Tras reforzar el saldo para conservar consumo de tareas canceladas, seis pruebas de reservas se repitieron y aprobaron. Tres pruebas de cambios de fuente se repitieron y aprobaron tras añadir texto/localizador anterior y nuevo a la consulta histórica.

Navegador: 25 de 26 recorridos aprobaron en la corrida general; el restante esperaba el texto previo del saldo mientras se ajustaba esa presentación. El recorrido de reservas se repitió y aprobó con la versión final. Los recorridos nuevos de reservas/fuentes usan API real y recursos temporales; los casos de IA y fechas futuras previamente simulados conservan esa condición. Captura sintética para revisión en `entregas/cierre-gestor-2026-09-28/presupuesto-sintetico.png`.

Compilación final 0.28 y TypeScript aprobados; OpenAPI validado sin advertencias tras declarar explícitamente que la simulación no requiere cuerpo. Sin migraciones pendientes de generar. 0034–0036 aplicadas únicamente en la base privada del proyecto por socket Unix. Fuentes originales intactas por SHA-256. Ninguna aplicación ajena del VPS modificada.

El canal externo sigue pendiente de selección y de completar su implementación/configuración/pruebas con los datos autorizados; no se presenta como un envío ya disponible. Los procedimientos excepcionales requieren definición institucional y su implementación correspondiente. Estos puntos y el piloto impiden declarar el cierre total del gestor en operación.
