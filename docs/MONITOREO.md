# Monitoreo y alertas locales del gestor

Continuación del punto 6. Se implementan observaciones técnicas, señal del trabajador y registro privado de cambios de alerta. **No se instalaron servicios ni temporizadores, no hay supervisión externa activa y no se envían mensajes.** Este incremento no altera las pantallas, contratos API, modelos ni permisos de la versión 0.9.

## Comandos y archivos

`monitor_health` lee el estado de la base y los recursos expresamente configurados del proyecto. No consume colas, reintenta trabajos, repara archivos, cambia configuraciones ni consulta otras aplicaciones del VPS. Es una herramienta del operador autorizado de infraestructura, no un endpoint público ni un rol que conceda acceso clínico.

Desde la raíz, con el entorno de la base propia configurado:

```bash
backend/.venv/bin/python backend/manage.py monitor_health \
  --state-dir /RUTA_PROPIA/monitoring
```

Para una instalación específicamente autorizada, se pueden añadir:

```text
--backend-url http://127.0.0.1:PUERTO_PROPIO/api/v1/session/
--frontend-url http://127.0.0.1:PUERTO_PROPIO/
--certificate /RUTA_DEL_CERTIFICADO_DE_ESTE_PROYECTO.pem
--backup /DIRECTORIO_DEL_CORTE_PROPIO
--restore-report /INFORME_DEL_ENSAYO_DE_ESE_CORTE.json
```

Las rutas y puertos son datos pendientes, **no valores para copiar sin revisión**. Comprobar previamente que pertenecen exclusivamente a Salud Modelo. El monitor no descubre servicios ni explora puertos. Las sondas HTTP aceptan únicamente `127.0.0.1`, puerto explícito y las rutas indicadas; hacen HEAD con límite de dos segundos y sin seguir redirecciones. No verifican DNS, HTTPS público ni una transacción de negocio. No se leen claves privadas del certificado.

El directorio de estado debe pertenecer al usuario ejecutor, con modo 0700. Si es nuevo se crea; si existe con permisos más amplios se rechaza, sin cambiar permisos existentes. Los JSON y bloqueos se crean con modo 0600. `monitor.json` se escribe mediante sustitución atómica y bloqueo exclusivo; contiene fecha UTC, resultado global, 16 comprobaciones y últimos 200 cambios de estado. Un informe más antiguo no reemplaza uno más reciente. Si el estado anterior es ilegible, se falla explícitamente; no se borra el historial para simular normalidad.

El comando imprime JSON y devuelve:

- **0:** todas las comprobaciones incluidas están conformes.
- **1:** hay advertencias o estados desconocidos.
- **2:** hay condiciones críticas o no se puede conservar el informe.

Un estado desconocido nunca se convierte en saludable. En esta entrega, la copia externa y la agregación de errores web aún carecen de verificación, por lo que el conjunto no alcanza estado global conforme. Es intencional; los componentes que sí se comprobaron tienen su resultado individual.

## Comprobaciones y umbrales iniciales

Estos son umbrales técnicos iniciales, no acuerdos de servicio institucionales aprobados.

| Comprobación | Resultado y umbral |
|---|---|
| Base | Lectura de prueba e instantánea de sólo lectura. Consultas limitadas a cinco segundos; conexión nueva por defecto limitada a cinco segundos. Fallo implica colas/presupuesto desconocidos, nunca cero |
| Documentos | Crítico si hay extracciones fallidas o arrendamientos vencidos/ausentes en trabajos en curso; advertencia para pendientes con documento de más de quince minutos o documentos sin trabajo |
| Cola IA | Crítico para trabajos en curso con inicio ausente o de más de dos minutos; advertencia para pendientes de más de quince minutos o fallos terminados en la última hora |
| Outbox | Advertencia si quedan avisos internos; crítico desde cien. No se calcula antigüedad porque la tabla no registra fecha de encolado |
| Intentos MFA | Advertencia desde cinco fallos y crítico desde veinte en quince minutos, agregados sin nombres. No incluye fallos de contraseña primaria |
| Presupuesto IA | Reservas mensuales por servicio: advertencia desde 80 %, crítico al agotar llamadas, tokens o importe, o si hay límites nulos/cero en una política habilitada. No es factura del proveedor ni cuota individual de usuario |
| Trabajador | Señal ausente: desconocido. Fallo, señal inválida/futura o de más de 45 minutos: crítico. Señal reciente: informa si está en curso o finalizó |
| Disco | Crítico con menos de 1 GiB o 5 % libres; advertencia con menos de 5 GiB o 10 %. Sólo volumen de adjuntos; no inodos ni todos los volúmenes |
| Certificado | Crítico si aún no entra en vigencia o le quedan siete días o menos; advertencia hasta treinta días. Sólo fechas del PEM local, no cadena de confianza, dominio o renovación |
| Respaldo | Tamaño, cabecera age, SHA-256 y fechas del corte local. Crítico si no coincide, es inaccesible/futuro o supera una hora desde el corte. No descifra ni acredita recuperabilidad |
| Restauración | Informe del mismo hash de respaldo; advertencia si el ensayo tiene más de siete días. Ausencia, incompatibilidad o fecha futura: desconocido. No autentica al autor del informe ni acredita RTO |
| Copia externa | Desconocido: un indicador booleano en un recibo local no acredita custodia fuera del VPS |
| Backend/frontend HTTP | HEAD a rutas locales explícitas, 200 o alerta. Sin configurar: desconocido. No reemplaza una sonda exterior ni prueba de acceso funcional |
| Errores web | Desconocido: agregación de logs/5xx aún no implementada |
| Configuración MFA | Crítico si falta formato de clave válido o se desactiva exigencia a privilegiados. No demuestra custodia de clave ni enrolamiento humano |

Documentos y outbox pueden volver a aparecer como advertencia en ciclos sucesivos; eso es observación del pendiente, no un nuevo envío. El registro añade una transición sólo cuando cambia el estado de una comprobación, incluida la recuperación a `ok`. Un cambio de magnitud dentro del mismo estado actualiza métricas sin duplicar la transición. El límite de 200 entradas no constituye un archivo histórico inmutable ni sustituye auditoría y retención institucionales.

## Señal del trabajador

El nuevo comando `worker_cycle --state-dir /RUTA_PROPIA/monitoring` ejecuta en orden los comandos existentes: `tracking_reminders`, `worker`, `extract_evidence` y `process_ai`. A diferencia del monitor, **sí procesa trabajo**, con los permisos y políticas ya implementados. No lo ejecute contra una base ajena ni como una simple comprobación de salud.

Guarda `worker.json` al comenzar y al terminar/fallar; conserva la fecha del último ciclo exitoso. Impide ciclos simultáneos que compartan su directorio. La señal no contiene errores en bruto, credenciales ni documentos. Un trabajo que termina en estado fallido sin lanzar una excepción puede coexistir con un ciclo técnicamente finalizado: el monitor comprueba además las colas para mostrar el problema. Los operadores que invoquen directamente los comandos antiguos no actualizarán esta señal; debe adoptarse el ciclo observado en el despliegue autorizado.

Una terminación abrupta puede dejar `running`; la antigüedad de la señal hará que se marque crítico. El monitor no mata procesos ni libera arrendamientos. Su propio fallo o ausencia requiere un supervisor externo: no puede alertar por sí mismo si deja de ejecutarse.

## Plantillas y operación pendiente

`deploy/salud-worker.service` ahora propone invocar `worker_cycle`. `deploy/salud-monitor.service` y `.timer` proponen observación cada cinco minutos, con tiempo máximo de dos minutos y directorio de escritura limitado. **Son archivos revisables, no instalados ni habilitados.** No tienen dominios, certificados, puertos ni respaldos reales configurados. Los códigos 1/2 quedan como fallo observable por un supervisor futuro; no se añadió envío automático ni destinatario.

Antes de operación faltan: confirmar umbrales y responsables, revisar aislamiento de rutas/puertos/usuario, configurar y probar las sondas reales, monitoreo exterior de HTTPS y disponibilidad, agregación de errores web, inodos/volúmenes restantes, transferencia y recuperación externas de respaldo, custodia/rotación de claves, retención del historial, canal de alerta autorizado, escalamiento y pruebas de fallos operativos. Continúan pendientes recuperación excepcional MFA y demostración de RPO 1 h/RTO 4 h con volumen institucional. Ninguna alerta técnica acredita aceptación clínica o cumplimiento normativo.

## Verificación

Pruebas específicas en `core.test_monitoring`: lectura de colas sin consumirlas; presupuestos y fallos MFA; base indisponible sin filtración de error; señal vencida/futura/fallida; disco; certificados PEM sintéticos; integridad/antigüedad de copia e informe del mismo corte; rechazo de destinos HTTP externos y redirecciones; transiciones sin duplicados y recuperación; permisos/bloqueos; salida no cero; ciclo real del trabajador sobre datos sintéticos.

```bash
# Sólo con PostgreSQL de prueba propio por socket privado:
backend/.venv/bin/python backend/manage.py test core.test_monitoring --noinput
```

Las trece pruebas específicas pasaron y después se aprobaron las **115 pruebas de regresión Django** en PostgreSQL privado. `manage.py check` no reportó incidencias y no hay cambios de modelo sin migración. Se ejecutó también el comando real contra la base privada de desarrollo con estado/almacenamiento temporales: lectura de base correcta, dieciséis comprobaciones, informe 0600 y salida 2 por clave MFA ausente, sin presentar éxito falso. No se ejecutaron sondas sobre aplicaciones existentes. Las sondas de prueba usaron un servidor HTTP efímero propio; certificados y respaldos fueron sintéticos. No hay cambios de modelo ni API y no se requiere compilación nueva de frontend para este incremento.

Referencia de implementación para lectura de fechas PEM: [cryptography X.509](https://cryptography.io/en/latest/x509/reference/). El monitor no utiliza esa lectura como validación de confianza TLS.
