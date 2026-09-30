# Redespliegue 0.35 completado — 30/09/2026

**Activo en https://plansaludmodelo.online.** Migraciones 0039, 0040, 0041 y 0042 aplicadas; `migrate --check` confirma que no quedan migraciones pendientes. Backend, frontend y worker usan las imágenes 0.35. Base y gateway propios conservaron sus contenedores; las otras once aplicaciones en contenedores no se modificaron. No se cambió Nginx del VPS, Certbot ni sus certificados.

## Cuentas creadas por instrucción expresa del usuario

| Cuenta de acceso | Nombre | Autoridad |
|---|---|---|
| amiraleon@modelo.edu.mx | Carla Amira Leon Pinto | Dirección de Salud; consulta académica de Odontología sin administración |
| mariososa@modelo.edu.mx | Dr. Mario Sosa Correa | Dirección de Odontología; administración de su escuela |
| gibarra@modelo.edu.mx | C.P. Gonzalo Arturo Ibarra Mendoza | Superusuario y administración institucional de ambas escuelas |

Correo y nombre de usuario coinciden. Se utilizó únicamente para estas altas la contraseña inicial elegida expresamente por el usuario; la política global no se redujo. La contraseña no se reproduce en esta documentación. No se enviaron correos de invitación.

MFA permanece obligatorio en las tres cuentas. Cada titular debe ingresar con su correo y contraseña, abrir **Activar autenticador**, confirmar la contraseña y pulsar **Preparar autenticador**. Después debe vincular su aplicación autenticadora, confirmar el código y conservar sus códigos de recuperación. No se inscribieron autenticadores en nombre de otras personas.

Vigencia inicial de nombramientos y consulta compartida: 30/09/2026–30/09/2027. La cuenta de superusuario no caduca por esas fechas, pero su mandato institucional sí tiene esa vigencia. La revisión o renovación corresponde al operador autorizado.

## Configuración aplicada

- Institución 1 identificada como **Universidad Modelo — entorno de demostración**, conservando identificador e historial del nombre anterior.
- Escuela de Salud (1) y Escuela de Odontología (2) como unidades pares.
- Servicio Odontología · DEMO (1) asignado a Odontología. No se inventaron servicios adicionales, alumnos ni ciclos.
- Consulta académica de Odontología por Dirección de Salud autorizada con vigencia y motivo. Sin consulta recíproca implícita.
- Cuentas ficticias de Odontología, revisión y colaboración conservan sus funciones de servicio. `demo_direccion` queda limitado a Salud y a consulta académica de Odontología; se revocó su antiguo rol de dirección dental. Los mandatos institucionales amplios de las cuentas ficticias de dirección/revisión quedaron vencidos, con auditoría.
- Pacientes reales e IA externa continúan desactivados. Existen cuentas institucionales reales, pero los datos de operación siguen siendo de demostración.

## Evidencia y respaldos privados

Entrega activa:

`/home/gaibarra/plandetrabajo/deploy/demo/runtime/releases/0.35.0-20260930T160107Z`

El archivo `runtime/active-release.txt` apunta a esa entrega. Contiene manifiesto, configuraciones fijadas a imágenes SHA, respaldos de base y archivos privados, configuración de cuentas restringida, ensayo, resultado de configuración y verificación pública. No compartir runtime: contiene secretos y respaldos.

Se ensayó la restauración, migración y creación de cuentas en PostgreSQL temporal sin TCP. El script se ejecutó dentro de la imagen final contra el socket de prueba y se comprobó su idempotencia. La copia original de 2.650 registros se conservó, con modificaciones explícitas de nombre institucional y alcances anteriores. La última copia, posterior a las migraciones y configuración, conservó 2.757 registros de 43 tablas durante la repetición, sin modificaciones de registros originales.

Antes de cada activación se tomó otro respaldo, incluyendo una copia de base con backend/worker propios detenidos. No se restauró ningún respaldo sobre la base activa ni se borraron datos.

Verificación pública mediante `smoke-schools.mjs`: las tres cuentas aceptan sus credenciales, requieren MFA y no acceden a API protegida antes de verificarlo. Dos cuentas ficticias con MFA existente comprobaron ingreso completo, dashboard de Salud, consulta de Odontología sin administración y conservación del alcance del responsable dental. Backend checks y worker correctos.

## Incidencias resueltas

Primer intento: migraciones correctas, script de cuentas sin ruta de importación Django dentro del contenedor; no creó cuentas y se restauró el código anterior. Se corrigió y ensayó dentro de la imagen.

Segundo intento: cuentas/configuración correctas; la comprobación inmediata de `/escuelas` recibió 502 de un proceso anterior durante la recarga asíncrona del gateway. Se restauró el código anterior, conservando cuentas y datos. El activador ahora espera hasta 45 segundos ante 502/503/504 durante esa transición.

Tercer intento: comprobaciones HTTPS y activación completas. La repetición reconoció la configuración existente y no duplicó cuentas ni restableció contraseñas. Imágenes anteriores conservadas.

## Operación y reversión

Para consultas de estado/logs, `docker compose -p salud-modelo-demo -f deploy/demo/compose.yaml ps` y `logs` son válidos. **Para recrear servicios**, incluir además el override de la entrega activa; el archivo base conserva etiquetas históricas 0.31 y no debe usarse solo con `up`.

Reversión de código, sólo si se necesita y se autoriza:

```bash
python3 deploy/demo/redeploy.py rollback deploy/demo/runtime/releases/0.35.0-20260930T160107Z
```

Conserva esquema, cuentas y registros; 0.31 no conoce las pantallas ni los mandatos escolares, por lo que no equivale a mantener el funcionamiento de 0.35. No degrada migraciones ni restaura copias sobre cambios posteriores. No volver a ejecutar el bootstrap para restablecer contraseñas.

El antiguo `smoke.mjs public` presupone los permisos ficticios de 0.31 y dejó de representar la configuración actual; usar `smoke-schools.mjs` para la comprobación escolar. Este último verifica el requisito MFA de las cuentas institucionales sin utilizar ni inscribir sus autenticadores personales.
