# Restricciones del proyecto

- Instrucción expresa del usuario: no afectar ninguna aplicación que esté corriendo en el VPS 194.113.64.91.
- Trabajar dentro de /home/gaibarra/plandetrabajo y directorios temporales propios. No modificar, detener ni reiniciar servicios, bases, usuarios, certificados, reglas de red ni configuraciones existentes de otras aplicaciones.
- Las pruebas deben usar recursos aislados propios. PostgreSQL de pruebas por socket Unix privado, sin puerto TCP público. No reutilizar bases de otros proyectos.
- Las plantillas de deploy son archivos revisables; no instalarlas ni activar producción sin datos y autorización específicos. Comprobar aislamiento de rutas, puertos y servicios antes de proponer despliegue.
- Fuente funcional: Plan_Trabajo_Escuela_Salud_Modelo.docx v3.1 y Prompt_Maestro_Salud_Modelo_IA (1).md. Conservar fuentes, historial y códigos originales. No declarar completado el alcance clínico por terminar un incremento del gestor.
- Consultar docs/DECISIONES.md y docs/BACKLOG.md para continuar sin duplicar trabajo ni perder pendientes.

## Objetivos del expediente de Odontología

- Consultar [Objetivos del expediente integral de Odontología](entregables/odontologia/Objetivos_Expediente_Integral_Odontologia.md) al planear o implementar funcionalidades de Odontología. Mantener allí el desarrollo de los 19 objetivos para evitar duplicaciones y versiones contradictorias.
- Relacionar los cambios con los objetivos ODO-OBJ-01 a ODO-OBJ-19 que correspondan y conservar sus criterios de logro.
- Los objetivos orientan el desarrollo; no autorizan por sí solos implementar todos los módulos ni desplegar cambios.
- Conservar la separación entre escuelas: únicamente se comparte la cuenta del usuario de servicios, no expedientes ni permisos.
- Registrar avances y pendientes en docs/DECISIONES.md y docs/BACKLOG.md, distinguiendo implementación técnica de validación institucional.
