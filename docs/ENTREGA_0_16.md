# Entrega 0.16 — capacidad y ausencias

La pantalla `/capacidad` permite proponer capacidad diaria por persona, descontar minutos de indisponibilidad y distribuir el tiempo restante entre servicios de una institución. Otra persona con mandato institucional vigente debe aprobar o rechazar cada propuesta. Una propuesta pendiente no equivale a disponibilidad confirmada; no se presuponen jornadas de ocho horas.

## Reglas y conservación

La capacidad se expresa en minutos, hasta 1440 por día, desde el 1 de octubre de 2026. La indisponibilidad no puede exceder la capacidad y la suma de asignaciones no puede exceder el saldo disponible. Cada propuesta contiene la distribución completa, con hasta veinte servicios distintos. Requiere nombramiento de trabajo o Dirección vigente para la persona, fecha e institución, y asignación vigente en cada servicio indicado.

La revisión es independiente, exige fundamento y conserva propuesta, estado anterior, autoría y resolución. Versiones optimistas, bloqueo por institución y claves de reintento ligadas al contenido protegen frente a duplicados y aprobaciones concurrentes. La aprobación revalida contenido y permisos. No existe eliminación mediante API. Las filas de distribución vigente son una proyección reemplazable; las propuestas y estados anteriores conservan el historial.

La pérdida de un nombramiento marca las asignaciones para revisión sin liberar automáticamente minutos. Se permite proponer y aprobar capacidad cero sin asignaciones para cancelar explícitamente un día ya registrado, incluso después de la pérdida del nombramiento. No se registran motivos médicos; los fundamentos deben limitarse a planificación.

## API y alcance

- `GET /api/v1/capacity/institutions/`: instituciones con mandato vigente.
- `GET/POST /api/v1/capacity/institutions/{institution}/`: semana de siete días y creación de propuestas.
- `POST /api/v1/capacity/changes/{id}/review/`: revisión independiente.

Las respuestas son privadas y no se almacenan en caché. La consulta rechaza explícitamente semanas con más de 500 registros o cambios, sin truncar historia. Migración aditiva 0023: días, asignaciones vigentes y propuestas/revisiones.

La capacidad se controla dentro de cada institución: no se detectan compromisos de una persona en instituciones distintas. No hay calendario laboral automático, autorización laboral de permisos, reserva horaria de tareas ni sincronización automática con Gantt o tiempo real. Los 295 + 59 = 354 h siguen siendo una referencia institucional provisional; no se multiplican por servicio ni se comprometen mediante esta pantalla.

## Verificación

175 pruebas de backend aprobadas, incluidas nueve de capacidad: límites, aislamiento institucional, pérdida de permisos, cancelación explícita, contenido alterado, reintentos, historia y concurrencia. Recorrido de navegador con API real aislada aprobado: propuesta de 480 minutos, indisponibilidad de 60, asignación de 300 y aprobación independiente; saldo disponible 420 y sin asignar 120. OpenAPI validado sin advertencias.

Los datos reales de capacidad y ausencias necesitan captura y aprobación institucional. Permanecen suplencias, ampliaciones de avisos, aprobación y programación de informes, validación de fichas, evaluación humana de IA, alcance clínico/administrativo y operación de producción. Esta entrega no acredita aceptación clínica ni completa el plan maestro.

Compilación 0.16 y TypeScript correctos; sin migraciones pendientes de generar. Migración aplicada únicamente en la base privada de desarrollo, clúster propio detenido al cierre y fuentes originales intactas por SHA-256. No se activó producción ni se modificaron aplicaciones ajenas del VPS.
