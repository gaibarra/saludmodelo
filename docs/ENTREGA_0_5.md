# Entrega 0.5 — documentos binarios y OCR

Punto 1 de la secuencia solicitada: implementación de PDF, DOCX, XLSX, PNG/JPEG y OCR con análisis de seguridad y límites explícitos. Preparada el 24 de septiembre de 2026; sin despliegue ni cambios a servicios ajenos.

- Antivirus ClamAV con firmas configuradas y actuales; cuarentena ante detección, indisponibilidad o fallo del aislamiento. Copias privadas de definiciones públicas en pruebas, sin modificar ClamAV del VPS.
- Bubblewrap y seccomp: red, procesos y sistema de archivos aislados; fuentes de sólo lectura y sin credenciales. Se impide crear procesos desde el analizador; los límites no dependen del número global de procesos del usuario. Se distingue el fallo de lanzamiento de una detección antivirus.
- PDF textual con páginas reales; DOCX con párrafos XML y partes adicionales; XLSX con hojas/celdas y fórmulas sin evaluar. Rechazos explícitos de ZIP excesivo, macros, DTD, objetos activos, relaciones externas y formatos antiguos.
- OCR de PDF escaneado y PNG/JPEG usando runtime privado y reconstruible, sin instalación global. Método y confianza orientativa conservados; aceptación requiere cotejo humano explícito por otra persona.
- Exigencia de escaneo fijada en recepción y mantenida si cambia la configuración; TXT/CSV nuevos también pasan seguridad cuando está configurada. Descargas comprueban la huella exacta de los bytes servidos. Salidas de analizadores validadas antes de persistir.
- Lotes de diez, arrendamiento de 180 segundos, tres intentos máximos; migraciones 0008–0010 aditivas.

Límites: entrada de 10 MB; PDF textual hasta 200 páginas; OCR hasta diez páginas y cincuenta segundos por documento; imagen hasta dieciséis megapíxeles; expansión Office de 30 MB/mil entradas; texto máximo dos millones de caracteres. No se interpreta contenido de gráficos o imágenes incrustadas en Office. Una extracción correcta no prueba autenticidad, vigencia ni suficiencia clínica o normativa.

## Verificación

Pruebas de backend con sandbox real, antivirus real, firma sintética, OCR real, cuarentena, archivos alterados, entradas hostiles, cotejo, permisos y migraciones. El recorrido Playwright con DOCX y antivirus real pasó junto con el acceso móvil. Compilación Next.js/TypeScript comprobada. Cierre conjunto 0.5–0.6: 69 pruebas Django y dos recorridos Playwright aprobados; OpenAPI validado sin advertencias y compilación Next.js/TypeScript correcta.

## Operación y continuidad

Configurar `DOCUMENT_SIGNATURES` y certificados públicos del motor para habilitar binarios. Para OCR ejecutar `python3 deploy/prepare_ocr.py` y configurar `DOCUMENT_OCR_RUNTIME` con su ruta privada. El script extrae paquetes fijados y verifica hashes; no los instala en el sistema. Antes de producción deben revalidarse versiones, firmas, corpus e infraestructura.

El punto 2 continúa con adaptadores OpenAI/DeepSeek, contratos cerrados, políticas de salida y citas verificadas. No hay llamadas reales a proveedores ni documentos institucionales enviados. Retención, aceptación institucional, matriz normativa y módulos clínicos permanecen en el backlog.
