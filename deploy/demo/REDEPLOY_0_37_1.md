# Atención Comunitaria · La Casita — 0.37.1 publicada

Paquete: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.37.1-20261001T164502Z`.

Corrección solicitada: Atención Comunitaria debe aparecer como servicio independiente bajo Salud, pendiente de confirmación en `/escuelas`. Compartir sede con Psicología no implica compartir su registro administrativo.

- Se conserva Psicología con su mismo identificador, confirmación, permisos, asignaciones y prácticas.
- Se crea sólo el Service y ficha `modelo-atencion-comunitaria-casita`, nombre «Atención Comunitaria · La Casita», `confirmed=False`, sin copiar roles ni activar citas.
- Se crea la Site «La Casita» en el campus de referencia ya existente; dirección exacta no inventada. Psicología deja la sede provisional exclusivamente si conserva el marcador original; sedes personalizadas no se alteran. Ningún otro servicio se traslada.
- Cada ficha usa su área propia; siete fichas institucionales totales, cinco de Salud. Reimportación idempotente.
- No hay migraciones nuevas: permanece esquema 0044. Dataset nuevo `institutional_services_20261001_1.json`; fuentes anteriores conservadas.

Validación: 38 pruebas backend aprobadas; checks/OpenAPI y compilación/TypeScript; recorrido aislado de navegador. Restauración por socket privado sin TCP con 2.871 registros originales retenidos en 44 tablas, permitiendo sólo sede/etag de Psicología y metadatos previstos de su ficha. Imagen preparada ensayada e importación repetida sin duplicados. La nueva Atención Comunitaria queda sin confirmar; ambas sedes coinciden. `redeploy.py check` aprobado.

**Estado: PUBLICADA.** El usuario autorizó expresamente publicar 0.37.1 con respaldo previo e interrupción breve sólo del proyecto. Activación completada el 01/10/2026 a las 16:52 UTC, resolviendo el rechazo inicial de autorización. Respaldos previo y sin escritores y copia de archivos privados conservados en el paquete; activación e inventario verificados.

Resultados en producción:

- Psicología conserva Service 6 y `confirmed=True`; sus relaciones no se reasignan.
- Atención Comunitaria es Service 8, `confirmed=False`, sin asignaciones copiadas ni slug de citas.
- Ambas comparten Site «La Casita». La respuesta autorizada de administración escolar incluye el servicio nuevo pendiente y la sede seleccionable.
- HTTPS/navegador: cada pestaña muestra su ficha propia, siete fichas generales, móvil sin desbordamiento; solicitudes reales deshabilitadas.
- `migrate --check` sin pendientes; esquema 0044 sin migración nueva.
- Once contenedores ajenos conservan su inventario completo. Db/gateway propios conservados; sólo backend/frontend/worker propios recreados y gateway propio recargado.

Evidencias privadas: `configured.json`, `activated.json`, `verified-*.json` y `public-psychology-check.json` del paquete. Capturas públicas en docs/capturas/*-0.37.1.png. Pendiente humano: confirmar Atención Comunitaria desde Escuelas cuando Dirección haya revisado sus datos y operación.
