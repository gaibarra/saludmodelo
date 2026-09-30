# Panel académico de inicio 0.35.4 — publicado

Al autenticarse en `/personal`, se presenta el panel académico con navegación lateral, métricas de las escuelas visibles, tarjetas por escuela y accesos a prácticas, evaluaciones, informes y actividades. La etiqueta Administración o Consulta académica refleja `can_manage` del backend. Los indicadores vacíos no se sustituyen por datos ilustrativos. Sin escuelas autorizadas se muestran accesos personales sin métricas globales.

El gestor de cuestionarios se conserva en `/personal/plan`. Ambas rutas comparten autenticación y no cambian permisos. Los enlaces de escuelas seleccionan la escuela solicitada sólo cuando está en la lista autorizada. El portal público sigue en `/`.

Paquete: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.4-20260930T165723Z`. Frontend `salud-modelo-demo-frontend:0.35.4`; backend/worker 0.35.3 y esquema 0042 intactos. Conservado el modo de contraseña temporal autorizado; MFA debe reactivarse antes de datos reales según `REDEPLOY_0_35_3.md`.

Verificación: compilación/TypeScript, imagen sin red, cuatro recorridos funcionales aprobados (panel con tres roles/plan/móvil; prácticas académicas; escuelas/permisos; contraseña sin segundo factor). La prueba del panel usa un superusuario con mandato institucional explícito, como la cuenta real configurada, sin ampliar permisos de producción.

Sólo frontend se recreó y el gateway propio se recargó. Los otros quince contenedores mantuvieron identificadores, inicio, imagen, puertos y montajes. Sin cambios al host, certificados o datos. Capturas en `docs/capturas/panel-academico-*-0.35.4.png`; las marcadas ensayo contienen únicamente datos sintéticos del entorno aislado.

Para operar Compose, incluir siempre `release.compose.json` del paquete activo. Activación/reversión de este parche: `redeploy-dashboard.py`. Reversión exclusiva al frontend 0.35.3:

```bash
python3 deploy/demo/redeploy-dashboard.py rollback /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.4-20260930T165723Z
```

La reversión recupera el inicio anterior; no restaura bases ni altera cuentas. Los activadores anteriores se conservan para sus propios manifiestos.

Comprobación posterior por HTTPS: cinco cuentas ingresaron con contraseña y conservaron sesión/permisos. Revisión visual adicional de las tres institucionales: Salud muestra dos escuelas y consulta dental; Odontología sólo la propia con administración; Gonzalo ambas con administración. Capturas públicas de escritorio y móvil guardadas. Un intento adicional alcanzó el límite de autenticación durante la comprobación repetida; tras el intervalo permitido, las tres revisiones terminaron correctamente sin alterar límites ni seguridad.
