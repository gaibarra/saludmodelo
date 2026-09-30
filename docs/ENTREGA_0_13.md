# Entrega 0.13 — comparación de posibles contradicciones

Nueva acción `contradictions`, seleccionable como «Comparar posibles contradicciones». Requiere autorización explícita en la política del servicio; las políticas anteriores conservan sus acciones. Utiliza la configuración de modelo por acción ya existente o su configuración general válida, sin configurar proveedores reales.

El usuario selecciona entre dos y ocho fragmentos distintos de la misma pregunta de servicio, autorizados para el proveedor. Pueden proceder del mismo documento: se admiten contradicciones internas. Identificadores repetidos no satisfacen el mínimo. Se mantienen los controles de revisión documental, vigencia, OCR, seguridad y revocación antes de enviar y antes de retener/consultar resultados. No salen la respuesta escrita, memoria de entrevista, archivos completos ni nombres de usuario.

Cada salida debe contener explicación no vacía y al menos dos citas verificadas. Cada posible contradicción conserva referencias a dos o más fragmentos distintos citados literalmente. Si identifica conflictos debe plantear una o dos aclaraciones para resolución humana. No se admiten propuestas de campos ni aprobación automática. La interfaz presenta juntas las citas asociadas a cada hallazgo, con la etiqueta «Posible contradicción» y estado pendiente de resolución humana.

Sin hallazgos, se permite una salida con explicación y citas, pero la pantalla aclara que no acredita consistencia completa. No se fuerza al modelo a inventar un conflicto. Las instrucciones piden distinguir diferencias de fecha/alcance de incompatibilidades reales; el contrato técnico sólo comprueba estructura y procedencia, no demuestra que la interpretación sea correcta.

Migración 0019 amplía las opciones de acción sin eliminar información ni ampliar políticas automáticamente. Nuevas solicitudes usan `salud-actions-4`; historial existente conservado. No hay nuevas tablas ni transiciones de aprobación. La resolución se realiza mediante los recorridos humanos existentes; no se implementa en este incremento un registro estructurado de resolución de cada hallazgo.

## Verificación

Seis pruebas nuevas cubren mínimo de fragmentos distintos, autorización explícita, citas y aclaración requeridas, citas inventadas, conflictos con identificadores duplicados, resultado sin hallazgos, idempotencia, ausencia de respuesta en contexto, imposibilidad de aplicar como respuesta y revocación durante la llamada. La prueba de navegador utiliza API simulada para comprobar selección mínima, visualización conjunta de ambos lados y ausencia de aplicación automática.

No se llamó a proveedores reales ni se midió exactitud semántica. La aceptación humana con corpus institucional autorizado sigue pendiente. También siguen pendientes informes, memoria externa autorizada y el resto del alcance clínico y operativo. No se instalaron servicios ni se activó producción; las pruebas utilizan recursos propios y PostgreSQL por socket Unix privado.

Resultado técnico: 145 pruebas de backend aprobadas, una nueva prueba de navegador aprobada y compilación 0.13/TypeScript correctos. OpenAPI validado sin advertencias. Migración aplicada únicamente en la base privada de desarrollo; clúster propio detenido al terminar.
