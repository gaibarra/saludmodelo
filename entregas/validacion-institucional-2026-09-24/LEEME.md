# Paquete de revisión institucional — Salud Modelo

Preparación técnica del punto 5. **Todas las filas están pendientes.** Este paquete contiene las fuentes editoriales, no una exportación de la base ni un reporte de aprobaciones vigentes. No tiene datos de pacientes, cuentas, nombramientos ni decisiones institucionales reales. Ningún archivo se envía automáticamente.

## Qué abrir

Abra `fichas.html` en un navegador, sin conexión. El índice agrupa las **177 fichas: 120 originales, 54 de cumplimiento y tres párrafos compuestos**, sin dividir ni cambiar códigos. Cada ficha conserva el texto, localizador XML, diez apartados de ayuda y referencias literales. Busque con Ctrl+F. Los ejemplos son ficticios. Para imprimir referencias, abra sus desplegables primero.

Las hojas CSV usan UTF-8 con BOM y coma como separador. Ábralas con un editor de hojas de cálculo y conserve identificadores, localizadores y huellas como texto. Las celdas de captura están vacías; `pendiente` no es una decisión. Guarde cada sesión en una copia nueva con fecha, alcance y versión. No sobrescriba el paquete original. Una hoja llenada no modifica el gestor ni acredita por sí sola una aprobación.

| Archivo | Trabajo que prepara |
|---|---|
| `revision_fichas.csv` | 177 filas con identificador y huella: selección, adaptación, suficiencia, responsables y observaciones por servicio |
| `servicios.csv` | Nueve referencias de unidades/procesos propuestas por el plan: confirmar servicios reales, sedes, oferta y exclusiones |
| `responsables.csv` | Plantilla vacía para nombramientos, competencia, alcance, vigencias, suplencias y aprobador distinto |
| `reglas.csv` | Once temas de decisión: alcance, permisos, fichas, evidencia, cambios, normas, IA, capacidad, calendario, seguridad y aceptación |
| `reglas_fuente.json` | Secciones literales del prompt que fundamentan los temas; anexos orientativos para cotejo |
| `usabilidad.csv` | 27 casos vacíos: uno normal y dos excepciones por cada referencia de unidad; duplicar por cada servicio/sede confirmado |
| `acta_modelo.md` | Acta sin firmas ni decisiones precargadas para una sesión de revisión |
| `fichas.json` | Catálogo estructurado para cotejo; no es un formato de importación de aprobaciones |
| `manifest.json` | Alcance, autor técnico, fecha y hashes del paquete y sus fuentes |

## Orden de revisión y registro

1. **Confirmar estructura y alcance.** Dirección identifica institución, campus, sede, servicio real, oferta, población y exclusiones. Las nueve unidades del plan son referencias propuestas: no acreditan servicios existentes. Mérida/La Casita y vinculación jurídica requieren confirmación; no se presupone incorporación de otros campus. Registre la decisión y fundamento en `servicios.csv` y en el acta. Duplique filas si hay varios servicios/sedes.
2. **Confirmar personas y competencia.** Complete `responsables.csv` con quien captura, quien revisa, quien aprueba y suplente, alcance y fechas. Un título funcional no acredita nombramiento. Dirección registra los nombramientos autorizados en Administración; el mandato inicial requiere el procedimiento de `README.md`. Nunca incluya contraseñas. Las suplencias institucionales requieren completar su gobierno; no confundirlas con el suplente de una tarea.
3. **Seleccionar y adaptar cada ficha.** Duplique las filas de `revision_fichas.csv` por cada servicio y sede destinatarios. Conserve los originales, su huella y los cambios propuestos. Escriba `incluir`, `no_incluir_propuesto` o `por_confirmar` en selección, con motivo. Una propuesta de exclusión no elimina obligaciones ni aprueba no aplicabilidad normativa. No se exige asignar las 177 a todos los servicios; las preguntas comunes y transversales deben evaluarse para cada alcance. Revise los diez apartados, alternativas documentales/declaraciones y lenguaje comprensible.
4. **Revisar por otra persona competente.** En Administración seleccione las preguntas autorizadas, abra la propuesta, adapte y guarde una nueva versión. Otra persona revisa esa versión y fundamenta aprobación o devolución. Registre en la hoja la versión y decisión reales del gestor; no marque decisiones anticipadas. La publicación exige servicio confirmado y ayudas completas y aprobadas para todo el conjunto seleccionado. Una nueva corrección se revisa y publica con historial; el paquete inicial no se actualiza automáticamente.
5. **Resolver reglas y dependencias.** Use `reglas.csv` y el acta para documentar alcance, propuesta, autoridad competente, fundamento, fecha y versión. Registre decisiones concretas en la pantalla correspondiente: Administración, Cumplimiento, Seguimiento o políticas IA. La matriz necesita verificación humana de fuentes oficiales, vigencia, numerales y aplicabilidad; este paquete no verifica normas. Las reglas aún sin flujo en el gestor permanecen en acta y backlog, sin presentarlas como implementadas. Capacidad de 354 h y calendario siguen siendo propuestas hasta su confirmación.
6. **Observar usabilidad con personas.** Una muestra de directivos de cada servicio debe responder un caso normal y dos excepciones con las ayudas. Defina previamente casos anonimizados, resultado esperado y observador; registre dudas y resultados reales. Use como posibles excepciones información insuficiente y evidencia contradictoria/obsoleta, adaptadas al servicio. Corregir, revisar de nuevo y repetir los casos afectados. Una prueba automatizada no sustituye esta observación. Los 27 renglones son plantillas, no pruebas ejecutadas; unidades no incluidas requieren fundamento y servicios adicionales requieren nuevos casos.
7. **Cerrar sólo el alcance comprobado.** Complete acta con versiones exactas y decisiones individuales, pendientes con responsable y fecha, y evidencia de pruebas. Separe aceptación de fichas, respuestas, documentos, tareas, normas y procesos clínicos. No firme aceptación integral por disponer del gestor. Mantenga los originales y la copia revisada bajo acceso institucional autorizado.

## Criterios para una sesión cerrada

- Servicios/sedes confirmados y selección de fichas justificada para ese alcance, incluidas preguntas comunes y transversales.
- Personas con nombramiento vigente, competencia para la decisión y separación de autor/revisor; suplencias documentadas.
- Diez apartados adaptados por ficha seleccionada, revisión independiente de la versión concreta y publicación cuando corresponda.
- Casos de usabilidad ejecutados por personas, dudas corregidas y repetición documentada. No hay aceptación por porcentaje de borradores creados.
- Reglas con decisión atribuible o pendiente explícito. Ninguna obligación se da por cumplida por aparecer en el catálogo.

Los resultados institucionales siguen pendientes de personas, fechas, servicios y documentos reales. No se asignan nombres ni se fabrican firmas, evidencias o resultados.

## Integridad y límites

Los hashes cotejan bytes, **no son firmas ni autenticación de aprobadores**. Antes de anotar, conserve el ZIP original y coteje sus hashes con `manifest.json`. El generador vuelve a leer el DOCX, compara literalmente el inventario, las 177 preguntas, sus diez campos y cada referencia; rechaza fuentes modificadas, referencias inconsistentes y destinos existentes. Para otra versión de fuente hace falta conciliación explícita, no editar el hash para omitir el control.

El paquete no incluye una importación de hojas completadas. Transcriba las decisiones autorizadas a los flujos existentes con la persona y versión correspondientes. Los cambios de alcance y de una segunda fuente aún requieren el flujo pendiente descrito en BACKLOG. No use este material como sustituto de ese control ni como aprobación de producción. No conecta a PostgreSQL, no llama IA, no inicia servicios y no modifica aplicaciones del VPS.
