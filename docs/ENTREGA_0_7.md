# Entrega 0.7 — matriz de cumplimiento

Punto 3 solicitado: flujo de gestión y trazabilidad de cumplimiento. Las obligaciones, vigencias y aplicabilidades reales permanecen pendientes de revisión institucional. Ningún módulo clínico queda aceptado por esta entrega.

## Catálogo conservado

`imports/normative-catalog.json` contiene las 60 filas N01–N60 del DOCX, sus títulos, materias, alcance indicado y enlaces literales, además de los encabezados C01–C20 conservando sus repeticiones. La huella de la fuente es `72108682be8b63f71c15d70d8d43fa370a033f04fd8af4526b4acf10b0e236be`. Importar el catálogo no asigna vigencia, aplicabilidad ni cumplimiento.

La orden `import_plan` ahora concilia también las tablas normativas. Conserva su vista previa y exige `--approve-sha` y `--actor` para persistir. Si el lote ya existe, incorpora sólo sus entradas normativas faltantes mediante relaciones con las fuentes originales, sin reescribirlas ni publicar preguntas. El catálogo visible depende del permiso `CatalogAccess` de la institución. Las fuentes F01–F17 y el resto del inventario original se conservan; no se convierten automáticamente en obligaciones.

## Recorrido implementado

Desde «Cumplimiento» se selecciona un servicio autorizado y se crea un registro que relaciona:

1. Entrada normativa y numeral exacto; versión consultada, URL HTTPS y fecha de consulta.
2. Control C01–C20, proceso propio del servicio, obligación jurídica propuesta o mejora recomendada.
3. Supuesto de aplicabilidad y explicación del vínculo con una pregunta concreta.
4. Responsable con nombramiento vigente, versión de respuesta y documentos de esa misma pregunta y versión.
5. Prueba registrada con procedimiento, resultado esperado, resultado observado y autor.
6. Revisión independiente, fundamento y próxima revisión.

El servidor no descarga URLs ni verifica automáticamente su carácter oficial. Quien documenta la vigencia debe aportar versión, numeral, fecha y fuente; la persona revisora debe cotejarlos. Por defecto se registra «por verificar».

Cada edición crea una revisión inmutable y un nuevo borrador. Los conflictos de edición se rechazan con 409. Las pruebas y revisiones se vinculan con la versión exacta. El rol `compliance` puede aprobar o devolver; no puede aprobar su propia edición ni una prueba que haya ejecutado. `manager` y `compliance` editan; esos roles y `clinical` registran pruebas. Los roles lectores sólo ven servicios de su alcance; ser superusuario técnico no concede acceso.

Para aprobar una aplicabilidad afirmativa se exige vigencia documentada, responsable vigente, próxima revisión no vencida, respuesta actual validada, evidencia aceptada y vigente, análisis limpio cuando corresponda y prueba satisfactoria. «No aplica» exige su propio fundamento y revisión independiente; se muestra como «No aplicabilidad revisada», nunca como cumplimiento automático.

Una respuesta modificada, evidencia vencida/devuelta, cambio de prueba, retiro de catálogo o vencimiento del responsable/revisión hace que una aprobación previa aparezca como «Requiere nueva revisión». Su registro histórico permanece. El estado se calcula al consultar: no se generan avisos externos ni nuevas obligaciones legales.

## Exportación y API

Listado paginado de 25 registros; selección por servicio y control de permisos antes de consultar datos. Exportación JSON hasta mil registros con autor, fecha, alcance, versiones, huella/localizador de fuente, pruebas y decisiones; se audita y usa `private, no-store`. No constituye certificado jurídico o clínico.

- `/api/v1/compliance/services/{service}/options/`
- `/api/v1/compliance/services/{service}/`
- `/api/v1/compliance/services/{service}/export/`
- `/api/v1/compliance/records/{id}/`
- `/api/v1/compliance/records/{id}/test/`
- `/api/v1/compliance/records/{id}/review/`

Migración 0013 aditiva, con relaciones reales a fuentes, procesos, preguntas, respuestas, documentos, pruebas y revisiones. No borra ni reescribe información previa.

## Límites y siguientes decisiones

La matriz está implementada como herramienta de revisión. No se verificó externamente la vigencia de las 60 entradas ni se declaró ninguna aplicable a servicios reales. Corresponde a la institución asignar responsables, consultar fuentes oficiales, definir procesos y pruebas, y aceptar cada registro. No se crearon datos institucionales, numerales, plazos legales ni aprobaciones reales.

Detección programada de cambios normativos y avisos, exportaciones ofimáticas, catálogo completo de procesos operativos y firma/actas de aceptación se mantienen pendientes. Los registros se relacionan con una pregunta por fila; pueden añadirse filas para otros vínculos. Los pendientes de entrevista IA del punto 2 se conservan: se atendió el punto 3 por instrucción expresa del usuario.

## Verificación

**77 pruebas Django aprobadas**, incluidas ocho específicas de cumplimiento. Tras los ajustes finales, se repitieron y aprobaron las ocho específicas, incluido rechazo de evidencia ajena y descarga con encabezados de navegador. **Tres recorridos Playwright aprobados**: gestor documental, acceso móvil y matriz con captura, prueba, revisión independiente, descarga JSON e historial. Compilación Next.js/TypeScript y OpenAPI sin advertencias; migración 0013 aplicada sólo al PostgreSQL privado de pruebas.

El ensayo normativo usa una institución sintética separada y el flujo normal de publicación de ayudas. Se corrigieron durante la validación etiquetas accesibles y negociación de formato de descarga. No hubo llamadas externas, instalaciones de producción ni cambios a aplicaciones ajenas del VPS.
