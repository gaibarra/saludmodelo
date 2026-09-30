# Entrega 0.27 — capacidad y ausencias vinculadas a tareas

Seguimiento incorpora «Capacidad y ausencias en la planificación». Al elegir el inicio de una ventana de siete días, compara por persona y fecha la carga estimada de tareas comprometidas abiertas con la capacidad aprobada asignada a ese servicio. Cada fila identifica las tareas que producen la carga, su distribución de minutos y el exceso detectado.

## Cálculo y estados

La estimación completa de cada tarea se distribuye uniformemente entre los días laborales de sus fechas de línea base, según el calendario institucional confirmado. Los minutos indivisibles se asignan a los primeros días laborales, conservando exactamente el total estimado. Se suman las tareas concurrentes del mismo titular. No incluye propuestas fuera de línea base, tareas aceptadas ni canceladas. Las tareas bloqueadas o en revisión siguen representando compromiso abierto.

Las tareas sin estimación o sin días laborales se señalan explícitamente; no se presupone carga cero validada. Sin calendario confirmado no se calcula distribución. Cada consulta muestra la versión del calendario y cada fila la versión de capacidad usada.

- **Dentro de capacidad:** carga estimada no supera asignación aprobada al servicio.
- **Sobrecarga:** exceso de carga respecto a la asignación aprobada, incluido un día aprobado sin asignación al servicio.
- **Sin capacidad aprobada:** día inexistente o pendiente de aprobación; capacidad y exceso desconocidos, no cero.
- **Nombramiento requiere revisión:** titular sin cuenta activa/rol de trabajo o Dirección vigente para esa fecha; no se presume utilizable la capacidad antigua.

La capacidad diaria aprobada ya descuenta indisponibilidad antes de distribuir minutos a servicios. La comparación usa esa distribución, sin restar ausencias nuevamente ni utilizar capacidad reservada a otros servicios. Señala presencia de indisponibilidad aprobada, pero no expone motivos, minutos totales institucionales ni distribución de otras unidades.

## Actualización y límites

Aprobar un cambio de capacidad o ausencia cambia el resultado de la siguiente consulta. También se reflejan modificaciones aprobadas de tareas y calendario. La pantalla permite volver a consultar después de esos cambios. Se usa una instantánea consistente de sólo lectura, con permisos vigentes del servicio y respuestas privadas sin caché.

La consulta no modifica responsables, suplencias, fechas, estados ni línea base; tampoco reserva minutos. Es un diagnóstico de planificación por fechas de línea base, separado del pronóstico por dependencias. No calcula trabajo restante a partir de horas reales, franjas horarias, capacidad entre instituciones ni reasignaciones automáticas. No valida retroactivamente la disponibilidad histórica: muestra compromisos y aprobaciones actuales para las fechas consultadas.

API: `GET /api/v1/tracking/services/{service}/capacity/?start=YYYY-MM-DD`. Inicio obligatorio desde 1 de octubre de 2026. Máximo mil tareas comprometidas abiertas solapadas; intervalo individual máximo 3660 días. Los excesos se rechazan explícitamente. No requiere migración ni nuevos trabajadores.

Permanecen pendientes reserva explícita de capacidad por tarea, simulación previa a aprobar una propuesta, redistribución coordinada, consumo de reserva institucional y aceptación del piloto. Los 354 h de referencia siguen siendo provisionales; esta consulta no los convierte en capacidad confirmada.

## Verificación

27 pruebas de capacidad y seguimiento aprobadas, incluidas siete nuevas: reparto exacto de minutos, ausencias/sobrecarga, capacidad desconocida, calendario y festivos, tareas cerradas/propuestas, permisos/revocación, suma de tareas y aislamiento de asignaciones de otros servicios. Dos recorridos de navegador con API real aislada aprobados: comparación capacidad/ausencia/sobrecarga y regresión de correcciones de horas.

Compilación final 0.27 y TypeScript aprobados tras corregir el tipo del identificador de servicio. OpenAPI sin advertencias; sin migraciones pendientes. Fuentes originales intactas por SHA-256. PostgreSQL propio por socket Unix detenido al finalizar; no se alteraron aplicaciones ajenas del VPS ni se activó producción.
