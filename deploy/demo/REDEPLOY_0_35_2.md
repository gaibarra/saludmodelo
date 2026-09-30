# Interfaz del personal 0.35.2 — publicada el 30/09/2026

`/personal` adopta la identidad visual del portal, presenta Salud y Odontología como escuelas pares y explica el espacio de trabajo académico. El acceso y la verificación se presentan en una tarjeta con dos etapas, instrucciones y ayuda para cambiar de cuenta. MFA y permisos se conservan; cerrar la sesión desde la verificación vuelve a `/personal`.

Paquete activo: `/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.2-20260930T162345Z`. Imagen frontend `salud-modelo-demo-frontend:0.35.2`. Backend/worker 0.35 y esquema 0042 sin cambios. No se modificaron cuentas, datos ni flags de pacientes/IA.

Validación: compilación y TypeScript, dos recorridos aislados de navegador (portada con MFA pendiente/cambio de cuenta/móvil y escuelas independientes), imagen sin red y prueba HTTPS de las tres cuentas institucionales y dos ficticias. Capturas en `docs/capturas/personal-*-0.35.2.png`.

Sólo se recreó frontend y se recargó el gateway propio. Los otros quince contenedores mantuvieron identificadores, inicio, imágenes, puertos y montajes. Sin cambios a servicios del host ni certificados.

Incluir siempre el `release.compose.json` activo al operar Compose. Activador de este paquete: `redeploy-personal.py`; los activadores anteriores se conservan intactos para sus propios manifiestos. Reversión exclusiva a la interfaz 0.35.1:

```bash
python3 deploy/demo/redeploy-personal.py rollback /home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.2-20260930T162345Z
```

Las comprobaciones del manifiesto impiden revertir si el entorno ya cambió. No se restauran bases ni se vuelven a crear cuentas.
