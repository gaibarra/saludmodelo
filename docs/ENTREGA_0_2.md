# Entrega 0.2 — administración y publicación de cuestionarios

Implementada el 23 de septiembre de 2026. No se desplegó en el VPS ni se crearon cuentas institucionales reales.

## Funciones entregadas

- Ruta `/administracion` con campus, sedes, servicios y confirmación explícita del alcance.
- Cuentas sin permisos precargados; nombramientos por servicio, rol y periodo; fundamento, revocación e historial. Autoasignaciones, periodos inválidos y accesos ajenos rechazados.
- Alta institucional inicial mediante `bootstrap_institution`, con aprobador y Director distintos. El mandato no sustituye roles clínicos ni abre respuestas detalladas.
- Inventario autorizado por institución; selección de preguntas sin duplicados y registro de cambios de alcance.
- Editor de los diez apartados de ayuda, borradores retomables, versiones inmutables, revisión por otra persona, devolución y publicación. Cobertura completa de las fichas seleccionadas requerida antes de publicar.
- Correcciones de ayuda conservan la versión publicada hasta su nueva publicación. Al publicar, se retira la validación actual afectada y se conserva la evidencia histórica.
- Migración histórica, API OpenAPI y corrección del proxy de acceso para rutas Django.

## Verificación

- Suite Django/PostgreSQL: 21 pruebas de flujos, permisos, aislamiento, conflictos, revocación, cobertura y conservación al migrar.
- Playwright/Chromium: dos pruebas aprobadas. Recorrido completo de Dirección → estructura → cuentas → nombramientos → selección de pregunta → autoría de ayuda → revisión independiente → publicación → captura → recarga persistida → evidencia TXT → revisión → dashboard actualizado. Segunda prueba: acceso a 390 px y foco de teclado.
- Compilación Next.js y TypeScript comprobada.
- OpenAPI validado sin advertencias ni errores.
- Capturas del recorrido y móvil inspeccionadas. Son datos sintéticos; están en `frontend/test-results/` y se regeneran con `python3 tests/run_browser.py`.

## Límites y siguiente paquete

Se entregó el mecanismo para preparar y revisar ayudas, no las 177 fichas específicas aprobadas. Faltan su redacción y revisión institucional, extracción PDF/Office/OCR, IA, cumplimiento, suplentes/MFA, métricas completas, respaldos/restauración y módulos clínicos. Continúa el backlog íntegro. El próximo paquete se centrará en borradores de ayuda sustentados en el plan, observaciones/consulta humana y evidencia documental segura.

Para habilitar usuarios reales hacen falta nombres, servicios, periodos y nombramientos autorizados. El README documenta el alta; no se inventaron personas ni autorizaciones. El calendario institucional conserva inicio 1 de octubre y aceptación objetivo 15 de diciembre de 2026.

Restricción permanente: no afectar aplicaciones existentes del VPS 194.113.64.91. Los procesos de prueba se ejecutaron en recursos propios y temporales; las plantillas Nginx/systemd siguen sin instalarse.
