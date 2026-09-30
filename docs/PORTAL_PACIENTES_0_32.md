# Portal inicial para pacientes — incremento 0.32

El portal propuesto traduce la imagen `escuela de salud.png` a un recorrido funcional. Al entrar a `/portal`, cualquier persona puede explorar Odontología, Fisioterapia, Nutrición, Psicología, Ciencias del deporte y Atención comunitaria. Cada página conserva las pestañas de las seis áreas. Los textos de presentación son borradores para revisión de Dirección y responsables de servicio.

La persona crea su cuenta con nombre, correo, teléfono y contraseña. Luego escoge un servicio, sede preferida y, opcionalmente, día preferido. La solicitud queda **pendiente**; no reserva una cita. Desde su cuenta ve sus propias solicitudes y puede retirar las pendientes. Un miembro del personal con nombramiento vigente en ese servicio consulta su bandeja y confirma fecha, hora y sede, o indica falta de disponibilidad. El paciente ve el resultado en su cuenta. No hay envío externo de correos o mensajes, ni captura de síntomas, diagnósticos, expedientes o archivos clínicos.

El catálogo permanece visible aunque un área aún no esté lista para recibir solicitudes. En tal caso el formulario la identifica como no disponible y la API impide crear la solicitud. Cuentas de pacientes y permisos del personal permanecen separados. El registro y la recepción real están apagados por defecto (`PATIENT_PORTAL_ENABLED=0`). La demo pública actual sigue siendo de datos sintéticos y no se actualizó con este incremento.

Para habilitar solicitudes reales faltan: validación institucional de los nombres, descripciones y sedes; responsable y nombramiento vigentes para cada servicio; aviso de privacidad, retención y procedimiento de atención de solicitudes; verificación del correo y recuperación de cuenta; pruebas de uso con pacientes y personal; y despliegue aislado revisado. La IA administrativa queda pendiente de categorías y límites expresos; no participa en confirmaciones clínicas.


## Relación con la prioridad académica de Dirección

Aclaración del usuario del 30/09/2026: el objetivo central es consultar y recuperar toda la información de las prácticas de los alumnos, durante el ciclo académico y al finalizarlo, en todos los servicios. El portal permite iniciar la relación con el servicio. En el desarrollo posterior, la atención o actividad efectivamente realizada deberá vincularse a las participaciones de los alumnos y a su supervisor. Una solicitud o cita confirmada no acredita actividad, horas ni competencias. El expediente académico, su validación y los informes de cierre están pendientes de desarrollo; el portal 0.32 no los incluye.
