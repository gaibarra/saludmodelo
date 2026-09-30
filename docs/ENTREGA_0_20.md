# Entrega 0.20 — suplencias temporales de nombramientos

En «Administración → Usuarios y nombramientos», el campo opcional «Nombramiento titular a suplir» vincula un nombramiento nuevo a su titular. Sin esa selección, el recorrido de nombramiento independiente conserva su comportamiento anterior.

## Alcance y permisos

Dirección dentro de su alcance autoriza una suplencia para otra persona activa y vinculada a la institución. Se requiere el mismo servicio y rol que el nombramiento titular, con fechas incluidas en su intervalo y fin no anterior al día de autorización. No se admite autoasignación, cubrirse a sí mismo, un titular revocado/inactivo ni cadenas de suplencias. Los controles de nombramientos solapados existentes también se aplican.

La suplencia es un permiso temporal real del rol elegido. No representa una credencial profesional ni sustituye comprobar competencia antes de autorizar. Se conserva quién aprobó, el fundamento y el vínculo al titular. Las acciones del suplente siguen registrándose con su propia identidad; no se firman actos en nombre del titular. Se mantienen MFA, alcance por servicio y revisión independiente según los controles existentes.

El permiso funciona mediante `RoleAssignment`, por lo que los recorridos actuales de cuestionarios, documentos, seguimiento y capacidad utilizan las mismas fechas y revocaciones. No se otorga automáticamente un mandato institucional: una suplencia del rol de Dirección de servicio sólo tiene ese alcance. Tampoco hereda los demás roles del titular.

## Fin y revocación

El acceso por ese nombramiento termina al vencer su fecha, sin tarea programada. Revocar el nombramiento titular mediante la API de administración revoca, en la misma transacción, todas sus suplencias no revocadas. Cada una conserva motivo y evento de auditoría. Revocar sólo una suplencia no revoca al titular ni a las demás.

Creación y revocación comparten bloqueo por servicio y revalidación de autoridad. Si una creación coincide con la revocación del titular, se rechaza o queda revocada en la misma secuencia, nunca como suplencia activa residual. Repetir una revocación no duplica eventos. Los registros permanecen en el historial y las relaciones son protegidas.

Cambios directos en base de datos o desactivación técnica de la cuenta titular no equivalen a revocar su nombramiento: las suplencias ya autorizadas conservan su propia vigencia hasta expiración o revocación. Para retirar la cobertura vinculada se debe revocar el nombramiento mediante administración. Un suplente puede conservar acceso por otros nombramientos independientes válidos; retirar esta suplencia no elimina esos permisos.

## API y operación

Migración aditiva 0027: `RoleAssignment.substitutes`, relación opcional al nombramiento original. No modifica ni enlaza automáticamente registros anteriores. Creación y lectura existentes de `/api/v1/administration/assignments/` incorporan el campo; la revocación existente realiza el cierre vinculado.

No hay cambios de servicios del VPS, nuevas tareas programadas ni despliegue. No se importan cuentas reales ni se conceden permisos fuera de los ensayos sintéticos.

## Pendientes

Esta entrega implementa suplencia de acceso por nombramiento. No mueve tareas, sustituye responsables de decisiones, redirige avisos, hereda autorizaciones de salida a IA, calcula ausencias ni reserva capacidad automáticamente. El suplente de una tarea sigue siendo una asignación explícita en seguimiento. Esas integraciones, programación/envío de informes, validación institucional y el alcance clínico/administrativo permanecen pendientes.

## Verificación realizada

200 pruebas de backend aprobadas; seis nuevas cubren acceso temporal y expiración, revocación vinculada e individual, conservación histórica, límites/roles/fechas, aislamiento institucional, autoasignación, cuentas inactivas y creación concurrente con revocación. Diecisiete pruebas específicas de administración/suplencias también aprobadas antes de la regresión completa. Recorrido de navegador con API real aislada aprobado tras corregir un selector del ensayo. Compilación 0.20/TypeScript y OpenAPI sin advertencias. Migración sólo en base privada por socket Unix; clúster propio detenido al cierre. Fuentes originales intactas por SHA-256.
