# Entrega 0.12 — revisión de respuesta con autorización de salida

La acción `review` permite solicitar observaciones sobre una respuesta guardada. Requiere política de servicio que habilite la acción, autorización independiente para el texto exacto y confirmación explícita del capturista. Las políticas existentes no se amplían automáticamente.

## Recorrido

1. Guardar el texto en la pregunta publicada.
2. Otra persona con permiso de revisión consulta «Autorizar salida de una respuesta a IA», coteja el texto y su clasificación pública o anonimizada/revisada, elige proveedor y vencimiento, y registra fundamento y confirmación. No debe autorizar texto que contenga datos personales, expedientes identificables, secretos o información confidencial. No se implementa anonimización automática.
3. El capturista abre asistencia, elige «Revisar mi respuesta», proveedor y autorización vigente. Ve el texto guardado y confirma su envío; puede incluir hasta ocho fragmentos con autorización independiente. La interfaz bloquea el envío si el editor tiene cambios sin guardar.
4. El trabajador valida permisos, políticas, cuotas y vigencia antes de llamar. La revisión produce explicación, faltantes, fuentes y posibles contradicciones. No reemplaza la respuesta ni cambia su aprobación.

## Controles y trazabilidad

Migración 0018 aditiva: `AIAnswerRelease` referencia una revisión inmutable y su etag, huella SHA-256 del texto, proveedor, clasificación, persona revisora, fundamento, vencimiento y revocación. La solicitud referencia esa autorización; la clave de reintento incluye su identificador. Nuevas solicitudes usan prompt `salud-actions-3`.

Se rechazan autorizaciones propias del autor, versiones obsoletas, texto vacío, cotejo no confirmado, proveedor incompatible y permisos ajenos. La persona que autoriza debe conservar cuenta activa y permiso vigente de revisión. Se vuelve a comprobar al enviar, recibir, consultar resultados e incorporar aclaraciones a entrevista. La revocación conserva historia y auditoría. Cambios del etag —incluso sin cambiar texto— exigen nueva autorización. La huella detecta una alteración del contenido que conserve accidentalmente el identificador de revisión.

El navegador envía sólo la referencia de autorización y la confirmación; el servidor obtiene el texto guardado. No acepta texto libre en la solicitud de IA. Sólo `review` incorpora `answer: {version, text}` en el contexto. Las demás acciones continúan excluyendo respuesta y memoria; tampoco salen autores, nombres de archivo ni historial. La autorización documental por sí sola no permite enviar una respuesta.

Revocar no puede retirar una llamada ya enviada. Una revocación/cambio detectado al terminar descarta la salida; un cambio posterior bloquea su consulta o uso. No hay bloqueo de escritura durante toda una llamada externa. Las salidas y las autorizaciones históricas conservan los controles de acceso existentes; su retención depende de la política institucional aún pendiente.

## Límites

Sin documentos autorizados, se puede revisar redacción y faltantes frente a la pregunta, pero no acreditar hechos. El texto de respuesta se trata como datos no confiables y no como instrucciones. El contrato técnico obliga a explicación no vacía y prohíbe propuestas de campos o aprobación automática. La fidelidad de las observaciones sigue requiriendo evaluación humana; ningún ensayo sintético acredita desempeño de modelos reales.

Este incremento usa el contrato general: las citas verificadas corresponden a fragmentos documentales; las observaciones sobre la respuesta se muestran en la explicación. No incorpora citas estructuradas de segmentos de respuesta, rúbricas institucionales específicas ni una nueva acción especializada de contradicciones. Informes, memoria externa autorizada y aceptación institucional continúan pendientes.

## Verificación

Seis pruebas nuevas de backend comprueban confirmación explícita, texto exacto, idempotencia, ausencia de escritura, aislamiento por servicio/proveedor, independencia, vencimiento, revocación, pérdida de permiso de quien autoriza, cambios antes del envío/después del resultado y huella alterada. El navegador comprueba selección, vista del texto, confirmación obligatoria, bloqueo de cambios sin guardar y ausencia de aplicación automática con API simulada.

Sin llamadas reales a IA ni activación de producción. Pruebas PostgreSQL por socket Unix privado, sin puerto TCP. Fuentes originales e instalaciones de otras aplicaciones conservadas.

Resultado técnico: 139 pruebas de backend aprobadas, dos casos de navegador aprobados entre corrida inicial y repetición, compilación 0.12/TypeScript y OpenAPI correctos. La migración 0018 se aplicó únicamente en la base privada de desarrollo; el clúster se detuvo al terminar.
