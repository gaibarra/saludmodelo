# Punto 5 — preparación de la validación institucional

Se preparó un paquete offline para que la institución revise servicios, responsables, fichas y reglas. **La preparación técnica está realizada; la validación institucional sigue pendiente.** Este incremento documental no cambia la versión 0.8 de la aplicación, modelos, permisos ni flujos de aprobación.

## Entregables

Carpeta: `entregas/validacion-institucional-2026-09-24/`. Archivo distribuible: `paquete_revision.zip`. No se ha enviado a terceros.

- HTML navegable con 177 preguntas, 1770 apartados de ayuda y referencias literales, organizado por secciones y compatible con móvil.
- Hoja de revisión de 177 fichas, con identificador y huella; se duplica por servicio/sede confirmado.
- Nueve referencias de unidades/procesos para confirmar servicios reales; no son nueve servicios ya constituidos.
- Plantilla de responsables sin nombres inventados, con competencias, vigencias, suplencias y aprobador.
- Once temas de reglas con sus secciones literales del prompt y hojas de decisión.
- 27 casos de usabilidad por completar: uno normal y dos excepciones por referencia de unidad; se amplían a cada servicio/sede real.
- Guía de sesión, acta vacía, catálogo JSON y manifiesto con fecha, autor técnico, alcance y huellas de archivos/fuentes.

El paquete no lee la base de datos ni certifica su estado. Todas sus decisiones están pendientes. No importa CSV completados, no firma actas ni publica fichas automáticamente. La guía conecta las decisiones humanas con Administración, Cumplimiento, Seguimiento y políticas IA existentes. Las reglas sin flujo implementado se conservan en acta y backlog.

## Generación y verificación

Desde la raíz del proyecto, siempre con una carpeta de salida nueva:

```bash
python3 tools/build_institutional_review.py --output entregas/validacion-institucional-NUEVA-VERSION
python3 -m unittest discover -s tests -p test_institutional_review.py -v
node tests/check_review_browser.cjs entregas/validacion-institucional-NUEVA-VERSION/fichas.html
```

El generador coteja los hashes exactos del DOCX y prompt originales, vuelve a analizar el DOCX y compara el inventario literal. Comprueba conciliación 120+54+3, contenido de preguntas, diez apartados y cada referencia. Rechaza cambios inconsistentes y carpetas existentes para preservar anotaciones. Escapa el HTML y neutraliza prefijos de fórmula en CSV. No usa Django, PostgreSQL, proveedores IA, red ni servicios; reutiliza sólo el analizador de DOCX de biblioteca estándar.

**Verificación ejecutada:** siete pruebas Python aprobadas; navegador Chromium comprobó las 177 fichas y 1770 apartados, navegación interna y despliegue de referencias, sin desbordamiento en 1280/375 px, errores JavaScript ni peticiones HTTP. Integridad de cada archivo del ZIP cotejada con el manifiesto. Las fuentes originales permanecen intactas. No se repitió la regresión del gestor: su código y configuración no cambiaron.

## Lo que requiere a la institución

Faltan confirmar servicios/sedes, asignar personas competentes y periodos reales, decidir selección y adaptar las fichas por servicio, revisar y publicar versiones concretas, confirmar reglas y ejecutar las pruebas de usabilidad con directivos. No se han realizado ni simulado esas decisiones. Las 177 propuestas editoriales no equivalen a 177 fichas institucionalmente aprobadas.

Se conserva el alcance clínico completo y los pendientes previos. La siguiente tarea técnica independiente de la secuencia es el punto 6: seguridad, MFA, respaldos/restauración y monitoreo en recursos aislados. No se autoriza despliegue por preparar este paquete. No se alteró ninguna aplicación del VPS 194.113.64.91 ni se iniciaron bases o servidores.
