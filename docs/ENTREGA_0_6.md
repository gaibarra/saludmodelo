# Entrega 0.6 — asistencia con documentos autorizados

Preparación técnica: 24 de septiembre de 2026. Avance del punto 2; no representa aceptación integral de IA ni de los módulos clínicos.

## Implementado

- Adaptadores de servidor OpenAI Responses y DeepSeek Chat Completions con contrato Pydantic cerrado, máximos de texto y rechazo de salidas truncadas, negativas, referencias inexistentes y campos desconocidos. Sin herramientas, URLs arbitrarias ni almacenamiento de razonamiento.
- Política por servicio, aprobada por quien administra su alcance, con proveedores y topes mensuales de llamadas por usuario y servicio, tokens reservados y USD. Credenciales, modelo y tarifas sólo en servidor. No hay identificadores de modelo ni precios supuestos en configuración de producción.
- Autorización de fragmentos públicos o anonimizados revisados, por otra persona, para un proveedor y periodo concretos; revocación desde la interfaz. La revisión de anonimización es humana: el sistema no certifica automáticamente que un texto carezca de identificadores.
- Contexto limitado a pregunta original y hasta ocho fragmentos de evidencia aceptada, vigente y de la versión actual de respuesta. Comprobación de permisos antes y después de la llamada. La respuesta del capturista, nombres de archivo y documentos completos no se envían.
- Cola PostgreSQL con clave de idempotencia, reserva transaccional de presupuesto antes de llamar, un intento por solicitud, límites de red y corte temporal tras fallos. Una llamada interrumpida se conserva como incierta, sin repetición o devolución de reserva automáticas.
- Propuestas comparadas con el texto actual y citas literales comprobadas mediante ID, localizador y huella del documento. La acción expresa del usuario crea una revisión atribuida a usuario y solicitud IA, en borrador y con hechos pendientes de confirmación. No valida respuestas, cumplimiento ni actos clínicos.
- Cancelación de solicitudes y rechazo explícito de propuestas con auditoría. Cancelar impide conservar o aplicar un resultado tardío; no revierte un envío ya realizado ni libera automáticamente su reserva.
- Ayuda revisada y captura manual disponibles cuando la salida externa está deshabilitada. Las pruebas sólo utilizan respuestas simuladas de proveedores; no se enviaron documentos institucionales ni se efectuaron llamadas facturables.

Migraciones 0011–0012 aditivas. Una política previa sin cuota individual queda bloqueada hasta que Dirección establezca un límite positivo.

## Configuración y uso

La salida externa permanece deshabilitada por defecto. Configurar `AI_EXTERNAL_ENABLED=1` sólo en el entorno propio autorizado, claves de proveedor y `AI_MODELS_JSON`. Este objeto contiene una entrada por proveedor autorizado con `model`, `max_output_tokens` (256–4000), `input_per_million`, `output_per_million` y `rates_verified_on` (fecha ISO, máximo treinta días de antigüedad). Las tarifas son USD por millón de tokens, verificadas para el modelo concreto; no se aceptan valores negativos o no finitos.

Desde Administración, registrar política, fundamento y presupuesto del servicio. Una persona revisora distinta del autor/uploader coteja el documento y autoriza fragmentos. El capturista los selecciona en «Asistencia con documentos» y solicita la propuesta. El trabajador propio ejecuta `python backend/manage.py process_ai`, hasta diez solicitudes por invocación; la plantilla systemd no se instaló. Consultar resultado, comparar y decidir su uso en borrador.

La reserva usa un máximo conservador basado en bytes UTF-8, esquema y salida; no representa consumo real. Se conservan reserva, uso reportado, tarifas y costo estimado. Las reservas no se liberan automáticamente, incluso si la llamada falla, para impedir exceder presupuesto por resultados inciertos. Si el proveedor reporta uso superior a la reserva, la política se deshabilita. Verificar facturación real antes de producción.

## Pendientes del punto 2

Entrevista persistente con respuestas confirmadas y campos compuestos; acciones separadas de explicación/revisión/informe; edición de propuestas por campo; reintentos con espera progresiva; alertas de presupuesto y segunda revisión opcional; corpus autorizado por servicio y evaluación humana de claridad/fidelidad/utilidad. No se declara fidelidad semántica por superar la comprobación literal de citas. La vigencia jurídica y suficiencia documental requieren revisión profesional.

El siguiente incremento debe completar estos pendientes de IA antes de pasar a la matriz de cumplimiento. Mantener los restantes paquetes de `BACKLOG.md`, la revisión institucional de las 177 fichas y las condiciones específicas de despliegue.

## Referencias de implementación

- [OpenAI: salidas estructuradas](https://developers.openai.com/api/docs/guides/structured-outputs).
- [OpenAI: Responses](https://developers.openai.com/api/docs/guides/migrate-to-responses).
- [DeepSeek: Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/).

## Verificación

Cierre: **69 pruebas Django aprobadas** (incluidas quince de IA), **dos recorridos Playwright aprobados**, compilación Next.js/TypeScript correcta y OpenAPI validado sin advertencias. Migraciones 0008–0012 aplicadas correctamente únicamente al clúster privado; comprobación de migraciones sin cambios pendientes. Pruebas de proveedores mediante HTTP simulado; permisos, revocaciones durante llamada, presupuesto agotado, idempotencia, citas inventadas y conflicto de versión en PostgreSQL privado. El recorrido de navegador incluye ayuda manual con IA deshabilitada, autorización/revocación de fragmentos y flujo documental DOCX con antivirus real.
