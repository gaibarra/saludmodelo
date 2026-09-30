# Entrega 0.22 — programación de borradores semanales

En «Informes semanales», Dirección con acceso vigente al servicio puede habilitar o pausar la generación periódica de borradores. La configuración no instala ni inicia procesos. El comando `scheduled_reports`, incorporado al ciclo del trabajador existente, genera un informe conservado por servicio y semana elegible, pendiente de revisión humana y sin envío.

## Período y primer informe

Se utiliza America/Merida, la zona del informe semanal existente. En cada ejecución se considera la última semana completa, de lunes a domingo; se puede generar desde el lunes siguiente, cuando se ejecute el trabajador. No se calcula una hora de entrega garantizada ni se utiliza el calendario de días hábiles de tareas.

Al habilitar se toma como primer período la semana actual; el primer período permitido del plan es el lunes 5 de octubre de 2026. Por ejemplo, habilitar el viernes 9 permite generar la semana del 5 al 11 desde el lunes 12. Pausar y reactivar vuelve a establecer el primer período en la semana de reactivación. Si el trabajador no se ejecuta durante varias semanas, sólo genera la última semana completa elegible; no rellena automáticamente períodos omitidos.

La actividad corresponde al intervalo semanal. Las métricas de situación son las observadas al generar: no reconstruyen un cierre histórico. Se conservan las limitaciones y referencias del generador existente.

## Autorización y revisión

Para configurar se requieren lectura vigente y autoridad de Dirección en el servicio. El trabajador vuelve a comprobar que la cuenta autorizante esté activa y conserve esas facultades, antes del cálculo y antes de guardar. La pérdida de autoridad deja el estado «Requiere renovar autorización», sin generar un informe; otra persona habilitada puede actualizar la configuración con fundamento.

Cada borrador conserva su contenido y huella, vínculo al período, programación y versión autorizada. Consulta, exportación e interfaz identifican su origen automático. La persona autorizante figura como responsable de la generación, sin presentarla como elaboración manual. No se registra aprobación automática y esa persona tampoco puede aprobar su propio borrador: sigue haciendo falta otra persona de Dirección con acceso.

Pausar impide nuevas generaciones; no retira ni modifica informes ya guardados. Retirar o rechazar un informe tampoco provoca otra generación automática de esa semana: una corrección utiliza el recorrido manual y su revisión independiente. Se conservan los recorridos existentes de revisión, rechazo, retiro y sustitución. No hay envío a usuarios ni proveedores de IA.

## Concurrencia, reintentos y diagnóstico

El cálculo usa la instantánea consistente de lectura del informe manual. El guardado bloquea el servicio y vuelve a comprobar la versión/configuración y los permisos. Una pausa o cambio durante el cálculo impide guardar con autorización desactualizada. Una restricción única por programación/período y una transacción conjunta de informe y ejecución evitan duplicados y registros incompletos, incluso con ciclos simultáneos.

Dos ciclos pueden calcular la misma semana simultáneamente; sólo uno conserva el resultado. Un fallo de cálculo deja estado fallido sin crear borrador, y la siguiente ejecución puede reintentar. La interfaz muestra última comprobación, estado y últimas veinte generaciones; la base conserva las anteriores y los informes mantienen su historial. Los cambios de configuración guardan versión, fundamento, autoría y período inicial en auditoría institucional.

El comando procesa las programaciones habilitadas y devuelve fallo observable si alguna requiere autorización o falla. El ciclo del trabajador registra ese fallo en su señal privada. No imprime contenido de informes ni detalles sensibles de excepciones. El estado de configuración no acredita que exista un temporizador activo.

## API y operación

- `GET/POST /api/v1/reports/services/{service}/schedule/`: consulta y configuración versionada.
- `manage.py scheduled_reports`: ejecutar generación local autorizada.
- `manage.py worker_cycle --state-dir ...`: incorpora generación al ciclo existente, después de las tareas previas; si una fase previa falla, esa ejecución no llega a la generación.

Migración aditiva 0030: `ReportSchedule` y `ScheduledReportRun`. Ningún servicio recibe programación automática por migrar. Sólo se crearon configuraciones sintéticas de ensayo. No se instalaron ni activaron temporizadores del VPS.

## Pendientes conservados

Esta entrega cubre generación programada, no distribución programada. Permanecen canales y destinatarios autorizados, seguimiento de entrega, recuperación explícita de semanas omitidas, otras frecuencias/horarios, integración de capacidad/ausencias, validación de un servicio piloto, base asistencial y operación de producción. No se declara completado el alcance clínico.

## Verificación realizada

215 pruebas de backend aprobadas con PostgreSQL aislado. Trece pruebas de programación/informes conservados aprobadas de nuevo después de identificar el origen automático en exportación e interfaz. Siete casos nuevos comprueban semana completa, ausencia de aprobación/envío, reintentos, configuración versionada, permisos/revocación, pausa durante cálculo, fallos recuperables y ciclos concurrentes. Recorrido de navegador con API real aislada aprobado: habilitar, recargar y pausar. Compilación 0.22/TypeScript y OpenAPI sin advertencias. Migración sólo en base privada por socket Unix y clúster propio detenido al cierre; fuentes originales verificadas por SHA-256. Aplicaciones ajenas del VPS intactas.
