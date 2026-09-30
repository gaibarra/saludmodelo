# Entrega 0.3 — borradores sustentados y consultas privadas

Preparada el 23 de septiembre de 2026, dentro del proyecto y con recursos de prueba propios. No se desplegó ni se modificaron aplicaciones existentes del VPS 194.113.64.91.

## Funciones entregadas

- 177 borradores editoriales específicos: 120 preguntas originales, 54 de cumplimiento y tres párrafos compuestos. Cada uno tiene diez apartados, campos y ejemplo ficticio por pregunta, y referencias al inventario conservado. Cero revisiones o publicaciones institucionales reales.
- Comparación de cada propuesta con el texto actual del editor. Aplicación explícita al editor, adaptación y guardado como nueva revisión. La revisión independiente y publicación siguen siendo acciones separadas.
- Comprobación en servidor del SHA de fuente, texto exacto y referencias del mismo lote autorizado. El digest de la propuesta incluye la instancia; no se puede reutilizar para otro servicio. Citas inexistentes o alteradas se rechazan. Se conservan origen y referencias por revisión; la edición manual sigue disponible para otras fuentes.
- Consultas privadas desde la ficha o captura y bandeja `/consultas`: destinatario vigente del mismo servicio, fecha esperada, versiones de contexto, mensajes y resolución por quien abrió la consulta. Acceso limitado a participantes autorizados; envíos repetidos no duplican registros y conflictos conservan el texto del editor.
- Resolver una duda no cambia la aprobación de la ayuda o respuesta. Una consulta resuelta conserva el historial; otra duda requiere nueva consulta.
- Migración 0006 aditiva y contrato OpenAPI actualizado.

## Verificación

- Django/PostgreSQL: 31 pruebas aprobadas; incluye cobertura y hashes de las 177 propuestas, citas, autorización, propuestas cruzadas entre servicios, consultas privadas, revocación/vencimiento, idempotencia, conflictos y conservación histórica al migrar.
- Playwright/Chromium: dos pruebas aprobadas. Recorrido completo con comparación y adaptación del borrador, revisión independiente, publicación, captura persistida, evidencia TXT, validación, consulta, respuesta y resolución; se comprueba que la validación sigue intacta. También acceso móvil y foco de teclado.
- Compilación Next.js/TypeScript y contrato OpenAPI validados. Sin migraciones pendientes de generar.
- Captura `frontend/test-results/consultas.png` inspeccionada. Las capturas son sintéticas y se regeneran con el ensayo de navegador.
- PostgreSQL de pruebas por socket Unix privado, sin TCP público. El navegador usa sockets de loopback propios; el runner destruye sus procesos y base temporal. No se reutilizaron bases ni servidores existentes.

## Continuidad

El siguiente paquete es ampliar la evidencia documental segura con extracción aislada y localizadores verificables. Siguen pendientes adaptación y revisión institucional de las ayudas, gestión de cambios de fuente, entrevista guiada, PDF/Office/OCR, IA, matriz normativa, suplencias/MFA, calendario y métricas completos, respaldos/restauración, despliegue y módulos clínicos.

Las consultas incorporan contexto de versiones, pero no adjuntos específicos, reasignación de responsables ni avisos programados. El catálogo es editorial: no invoca APIs ni sustituye validación clínica, jurídica o institucional. La generación comprueba la versión de DOCX conocida y requiere revisar correspondencias si cambia la fuente. El reporte de borradores no sustituye indicadores reales por servicio.
