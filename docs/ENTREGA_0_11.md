# Entrega 0.11 — acciones explícitas de IA

La asistencia distingue ahora cuatro acciones persistidas: `suggest`, `explain`, `interview` y `extract`. El usuario elige la acción en la interfaz y el servicio debe autorizarla expresamente. Las políticas y solicitudes anteriores conservan `suggest`; la migración 0017 no habilita nuevas acciones en políticas existentes.

| Acción | Entrada y resultado | Escritura en respuesta |
|---|---|---|
| Proponer con mis documentos | Pregunta y al menos un fragmento autorizado; propuesta con citas verificadas | Sólo mediante confirmación explícita; crea borrador por confirmar |
| Explícame | Pregunta y fragmentos opcionales; explicación obligatoria | No permitida |
| Guíame paso a paso | Pregunta y fragmentos opcionales; una o dos aclaraciones obligatorias | No permitida; puede incorporarse a la entrevista persistente con su control existente |
| Extraer datos de mis documentos | Pregunta y al menos un fragmento autorizado; citas literales o faltantes explícitos | No permitida |

Las extracciones son salidas de consulta en el contrato existente, no nuevos campos clínicos tipados. La guía generada no recibe memoria de entrevista ni respuestas escritas; el recorrido persistente local conserva los avances. No se envían nombres de usuario, nombres originales de archivos, documentos completos ni el texto actual del editor.

La acción forma parte de la clave de reintento: reutilizar una clave con otra acción se rechaza. La política se comprueba al solicitar, antes de enviar, al terminar y al consultar o utilizar el resultado. Una revocación bloquea usos posteriores; no puede deshacer datos que ya se hayan enviado. El contrato rechaza propuestas de campos fuera de `suggest`. Se mantienen citas verificadas, cuotas, vigencia documental, aislamiento por servicio y revisión humana.

## Configuración revisable

`AI_MODELS_JSON` admite `actions` por proveedor. Cada entrada de acción debe contener el mismo conjunto completo de configuración existente: `model`, `max_output_tokens`, `input_per_million`, `output_per_million` y `rates_verified_on`. Si no hay entrada para esa acción, se utiliza la configuración general del proveedor; si tampoco es válida, se rechaza antes del envío. Tarifas y fechas mantienen las verificaciones existentes. No se configuraron ni recomendaron modelos, precios o claves reales.

El administrador puede seleccionar acciones en la política de asistencia. Esto no elimina la autorización independiente requerida para cada fragmento. La salida externa sigue deshabilitada hasta disponer de configuración y política válidas. Los contratos HTTP de los proveedores no cambian; el contexto incorpora acción e instrucción fija, con versión de prompt `salud-actions-2` en solicitudes nuevas.

## Verificación y límites

Pruebas de backend cubren autorización por defecto, acciones desconocidas, idempotencia, explicación sin documentos, rechazo de escritura, rechazo de propuestas en extracción, evidencia requerida, revocación antes/durante/después de la llamada y selección de modelo por acción. El navegador comprueba selección, requisitos de documentos y ausencia de botón de aplicación para explicación con API simulada. Resultado: 133 pruebas de backend aprobadas, una nueva prueba de navegador aprobada y compilación/TypeScript correctos. OpenAPI validado sin advertencias. Sin llamadas reales a proveedores.

La revisión de suficiencia de una respuesta escrita (`review`), informes, detección específica de contradicciones como acción, memoria externa autorizada y evaluación humana siguen pendientes. Incorporar `review` requiere autorización explícita para el texto que saldría y comparación con su versión vigente; no se reutiliza implícitamente la autorización de fragmentos. Las contradicciones ya pueden aparecer en el contrato general, pero este incremento no implementa una acción especializada ni certifica su detección semántica.

Se mantienen todos los pendientes clínicos, institucionales y operativos del backlog. No se instalaron plantillas, no se activó producción y no se modificaron servicios de otras aplicaciones del VPS.
