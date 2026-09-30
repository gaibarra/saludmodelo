# Entrega 0.4 — extracción TXT/CSV y revisión de evidencia

Preparada el 24 de septiembre de 2026. Implementación local; sin despliegue, instalación de servicios ni cambios a aplicaciones existentes del VPS 194.113.64.91.

## Funciones

- Recepción privada de TXT y CSV UTF-8, con vínculo a la versión de respuesta y huella SHA-256 del original. PDF, Office e imágenes siguen bloqueados.
- Extracción persistente por proceso separado con límites: 256 MiB, cuatro segundos de CPU, ocho segundos totales, dos millones de caracteres, diez mil fragmentos, doscientas columnas y doscientos mil caracteres por celda CSV. El exceso se rechaza sin publicar resultados parciales.
- Localizadores de línea TXT y fila/líneas CSV; celdas y saltos internos conservados. No se evalúan fórmulas ni se siguen enlaces. Fragmentos paginados de cincuenta en cincuenta y descarga autenticada del original.
- Cola PostgreSQL con arrendamiento de sesenta segundos, bloqueo de trabajos disponibles, token por intento, recuperación de interrupciones y hasta tres intentos. Reintento explícito autorizado y controlado por versión; estados de fallo visibles.
- Aceptación y devolución con fundamento, persona revisora, fecha de vigencia e historial. La persona revisora debe ser distinta tanto de quien carga como de quien escribió la respuesta asociada. La aceptación exige extracción disponible y no valida automáticamente la respuesta.
- Señalización de vigencia vencida y documentos correspondientes a una versión anterior de respuesta. Conservación de originales y decisiones históricas.
- Permisos documentales para metadatos, fragmentos y originales; revalidación de acceso por servicio y protección frente a caché compartida en las nuevas rutas.
- Migración 0007 aditiva; incorporación de evidencias heredadas al ejecutar `extract_evidence`. Plantilla del trabajador actualizada como archivo revisable, sin instalarla.

## Verificación

- 43 pruebas Django/PostgreSQL aprobadas. Incluyen contenido literal, CSV multilínea y fórmulas inertes, límites, tiempos agotados, permisos y metadatos (incluido modo 0600 de nuevos archivos), revocación, revisión independiente, vigencia, contexto histórico, integridad del archivo, reintentos, recuperación por token y migraciones históricas.
- Dos pruebas Playwright/Chromium aprobadas. El recorrido incluye carga, extracción, lectura de localizadores y aceptación documental por otra persona; comprueba que la respuesta aún necesita su revisión propia. Mantiene el recorrido de ayudas, publicación, captura, consultas y acceso móvil.
- Compilación Next.js/TypeScript aprobada, OpenAPI validado y ausencia de migraciones pendientes de generar.
- Captura de evidencia en `frontend/test-results/evidencia.png`, generada con datos sintéticos e inspeccionada visualmente. El ensayo espera el resultado del trabajador mediante «Actualizar documento».
- Pruebas con PostgreSQL por socket Unix privado, procesos propios y sockets de loopback reservados. El runner limpia su base y procesos; el clúster temporal auxiliar se detiene al concluir.

## Límites y continuidad

El proceso limitado de TXT/CSV **no es un sandbox general ni un antivirus**: no confina por sí mismo acceso al sistema de archivos o red. Su código es un analizador de texto inerte de biblioteca estándar, sin credenciales Django ni llamadas externas. No se emplea para ejecutar código no confiable ni para abrir PDF/Office. Esos formatos requieren un paquete posterior de confinamiento, analizadores y pruebas específicas, además de OCR cuando corresponda.

Siguen pendientes retención, antivirus, autenticidad/verificación en sitio, búsqueda documental avanzada, extracción con citas hacia respuestas propuestas, gestión de cambios de fuente, IA, matriz normativa, suplencias/MFA, calendario completo, respaldos/restauración, despliegue y módulos clínicos. Las 177 ayudas continúan siendo propuestas sin aprobación institucional real. Los ensayos no representan aceptación clínica o normativa.
