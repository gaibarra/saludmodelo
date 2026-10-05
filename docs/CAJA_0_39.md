# Caja por servicio — 0.39.0

## Operación

Acceso desde «Caja» en el panel del personal o `/caja`. Moneda inicial: MXN. Únicamente efectivo; otros medios quedan excluidos tanto en API como por restricción de base de datos. La ampliación posterior requerirá una nueva migración y conciliación por medio.

1. Dirección selecciona un servicio y asigna un turno con horario y colaborador de su escuela. La cuenta debe estar activa. Una persona puede atender distintos turnos; cada turno tiene un responsable identificado.
2. El responsable ingresa con su propia cuenta, abre durante el horario programado y declara el fondo inicial contado. Sólo puede existir una caja abierta por servicio; no se programan horarios superpuestos del mismo servicio.
3. Registra cobros (importe neto después del cambio), ingresos de fondo, retiros/entregas y devoluciones. Cada movimiento conserva importe, concepto, referencia opcional, folio interno, autor y fecha. En retiros, el concepto debe identificar a quien recibe. No incluir diagnósticos en conceptos o referencias.
4. Una devolución referencia un cobro del mismo servicio, incluso de un turno anterior. No puede superar el importe no devuelto ni el efectivo disponible. No se modifican ni eliminan movimientos.
5. Antes de cerrar registra las entregas de efectivo efectuadas. Cuenta el efectivo restante y cierra; cualquier diferencia respecto del saldo esperado exige explicación. El cierre es definitivo y conserva contado, esperado y diferencia. No representa por sí mismo entrega a tesorería ni traslado automático al siguiente turno: éste declara su propio fondo contado.

Para corregir responsable u horario de un turno sin abrir, Dirección lo cancela con motivo y asigna otro. No existe sustitución silenciosa de responsables en turnos abiertos. Si un responsable queda indisponible durante un turno abierto, la conciliación y sustitución excepcional requieren un procedimiento institucional futuro, no usar su contraseña.

## Supervisión y permisos

Cada director supervisa exclusivamente su escuela. La autoridad institucional conserva visión de ambas; no hay consulta cruzada Salud/Odontología. El responsable ve y opera únicamente sus turnos, con membresía escolar comprobada en cada petición. Dirección puede consultar pero no operar en nombre de un cajero distinto. Las cuentas dadas de baja no acceden.

Monitoreo: cobros, devoluciones, ingresos de fondo, retiros, efectivo esperado en turnos abiertos, cierres y diferencias. Filtros por servicio, estado e inicio del turno; movimientos completos de esos turnos. Sin fechas incluye todo el historial autorizado. La diferencia neta se acompaña del número de cierres con diferencia para evitar ocultar diferencias que se compensan. Listas paginadas de 50 registros.

## Integridad

Importes decimales de dos posiciones, registros históricos protegidos, revisión contra cambios simultáneos, claves de solicitud para impedir duplicados por reintentos, bloqueo por servicio durante escritura y auditoría de asignación, apertura, movimientos, cancelación y cierre. La prueba con dos retiros simultáneos confirma que sólo uno puede consumir el saldo bajo la misma revisión.

Migración aditiva 0046: tablas CashShift y CashMovement, relaciones protegidas y restricciones. No crea ni modifica cuentas, servicios ni datos monetarios. No es facturación fiscal, contabilidad general, catálogo de tarifas ni integración con expediente clínico; utiliza referencias administrativas capturadas por el responsable. Esas ampliaciones y otros medios de pago quedan para acuerdos posteriores.

## Validación

44 pruebas de Caja/cuentas/escuelas más una prueba concurrente en PostgreSQL aislado; checks/migraciones/OpenAPI aprobados. Build/TypeScript y recorrido navegador de asignación, apertura, cobro, devolución, cierre con diferencia y ancho móvil aprobados. Captura sintética: `docs/capturas/caja-0.39-ensayo.png`. Advertencia previa fuera de este incremento: fecha fija en core.Task.starts.

## Estado de entrega

Publicada el 01/10/2026 tras autorización expresa del usuario. Respaldo previo/sin escritores y migración 0046 completados; HTTPS /caja y permisos de las tres cuentas institucionales verificados. Sin migraciones pendientes ni movimientos ficticios. Once contenedores ajenos intactos. El ensayo conservó exactamente 2.891 registros previos. Detalle: deploy/demo/REDEPLOY_0_39.md.
