# Verificación del incremento 0.1

Registro histórico. La verificación actual de administración, cuestionarios y navegador está en [ENTREGA_0_2.md](ENTREGA_0_2.md).

Ejecutada el 23 de septiembre de 2026, en el directorio del proyecto y clúster PostgreSQL 16 temporal propio por socket Unix privado. No se usó SQLite ni se modificaron aplicaciones o bases existentes del VPS.

- Django `check`: sin incidencias.
- Migraciones aplicadas en base temporal; `makemigrations --check --dry-run`: sin cambios pendientes.
- Django `test core --noinput`: 9 pruebas aprobadas, última ejecución 8.494 segundos.
- Cobertura de estos casos: permisos cruzados por servicio, asignación vencida, rechazo de login sin CSRF, publicación bloqueada sin revisión, versiones y conflicto, revisión por otra persona, desconocimiento con tarea/outbox idempotente, no aplicabilidad sin aprobación automática, descarga privada e importación repetible.
- Next.js `npm run build`: aprobado; comprobación TypeScript aprobada.
- OpenAPI `spectacular --validate`: generado sin advertencias ni errores en `docs/openapi.yaml`.
- Instalación npm: 0 vulnerabilidades reportadas por el registro en ese momento. Esto no equivale a una auditoría de seguridad de toda la aplicación.
- Inventario: 1525 párrafos no vacíos; 120 preguntas originales, 54 de cumplimiento y tres párrafos adicionales; 60 registros normativos, 12 requisitos, nueve párrafos de procesos y 34 encabezados de anexos (hay códigos repetidos en la fuente).

No ejecutado: navegador/Playwright, evaluación humana, APIs OpenAI/DeepSeek, extracción OCR, carga/estrés, auditoría de seguridad integral, restauración/RPO/RTO, despliegue o aceptación clínica/institucional. Ver BACKLOG.md.

La base temporal de pruebas fue destruida por Django al terminar. El clúster temporal se detuvo después de la verificación; no queda un servicio nuevo escuchando para esta entrega.
