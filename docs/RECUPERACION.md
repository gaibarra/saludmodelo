# Respaldo cifrado y ensayo de restauración — punto 6, primer incremento

Se implementa una herramienta local de recuperación del gestor. **No instala servicios, no programa respaldos, no envía copias fuera del VPS y no restaura sobre bases existentes.** Este documento describe el primer incremento de recuperación sobre 0.8. MFA se incorporó después en 0.9 y también se ensayó su restauración; ver ENTREGA_0_9.md. Monitoreo general y recuperación de producción siguen pendientes.

## Qué se respalda

`tools/recovery.py backup` usa una transacción PostgreSQL de sólo lectura y una instantánea exportada compartida con `pg_dump`. Incluye el esquema y los datos de la base, los originales referenciados por `EvidenceDocument`, el DOCX y el prompt fuente. Conserva en un manifiesto los conteos y huellas del contenido de todas las tablas públicas, de los archivos y de las referencias documentales. Esto abarca respuestas/revisiones, fichas, permisos, historial, evidencias, tareas y eventos pendientes.

Copia los originales desde almacenamiento privado y comprueba cada SHA-256 contra la base; un documento ausente, alterado, no regular o enlazado fuera del directorio cancela el respaldo. Un archivo añadido después del corte no pertenece a la instantánea. La herramienta depende de originales inmutables, como los del gestor: no permite dar por válido un respaldo cuando faltan archivos históricos. No ejecutar limpieza de originales durante el respaldo.

El paquete se cifra con `age` para una clave pública nativa X25519. El proceso de respaldo no necesita la clave privada. Publica una carpeta nueva con `backup.tar.age` y `receipt.json`; no reemplaza respaldos anteriores. El recibo contiene fechas, duración y huella del cifrado, sin contraseñas ni contenido de registros. Su estado es `encrypted_local_only`, no una prueba de copia externa o recuperación. La operación CLI usa permisos 0700/0600 y retira temporales tanto al finalizar como al fallar.

No incluye secretos de entorno, claves de cifrado, configuración del VPS, identidades PostgreSQL globales, binarios OCR/antivirus ni código de aplicación. El manifiesto registra la huella del lockfile; la recuperación completa exige conservar también el código, lockfiles, artefactos y configuración autorizada de la misma versión. El DOCX/prompt del paquete provienen del árbol de trabajo; una futura segunda fuente exige ampliar esta estrategia para conservar los originales de todos los lotes.

## Ensayo repetible con datos sintéticos

Desde la raíz del proyecto:

```bash
backend/.venv/bin/python -m unittest discover -s tests -p test_recovery.py -v
```

Usa PostgreSQL 16 y `age`/`age-keygen` ya disponibles; no instala paquetes ni toca clústeres existentes. Genera claves temporales, una base sintética completa con migraciones y datos propios, respaldo cifrado y clústeres nuevos de recuperación en `/tmp/salud-*`, con directorios privados y **sin escucha TCP**. Al terminar se retiran clústeres, archivos y claves de prueba. Sólo se conserva `docs/recovery-test-report.json`, sin datos identificables ni secretos. Este informe registra un ensayo sintético, no constituye una bitácora inmutable ni una firma institucional.

La restauración coteja todas las tablas y archivos antes de comprobar mediante el código de aplicación que las versiones y permisos funcionan. No inicia servidores web, trabajadores, IA ni avisos. Verifica descarga del propietario autorizado, denegación de otro servicio y del superusuario técnico sin alcance, revisiones anteriores, revisión de ayuda, tarea/outbox pendientes e inserción posterior sin conflicto de secuencia.

## Uso manual, sólo en entorno propio autorizado

Esta versión restringe origen a un directorio de socket Unix privado del usuario, puerto interno 5432, base con prefijo `salud_`, almacenamiento privado y esquema conocido del gestor. Rechaza tablas públicas y esquemas ajenos. No admite origen TCP ni un destino PostgreSQL existente. Requiere autenticación local ya autorizada; no recibe contraseñas en argumentos ni configura usuarios, autenticación o servidores.

Con una clave pública institucional previamente verificada, sustituya los valores de ejemplo por recursos propios. El script no crea ni decide la custodia institucional de claves:

```bash
backend/.venv/bin/python tools/recovery.py backup \
  --socket /ruta/privada/socket \
  --database salud_ENTORNO_PROPIO \
  --user USUARIO_AUTORIZADO \
  --storage /ruta/privada/adjuntos \
  --recipient CLAVE_PUBLICA_AGE_VERIFICADA \
  --output /ruta/privada/respaldos/CORTE_NUEVO

backend/.venv/bin/python tools/recovery.py restore-check \
  --archive /ruta/privada/respaldos/CORTE_NUEVO/backup.tar.age \
  --expected-sha256 HUELLA_DEL_RECIBO_DE_PROCEDENCIA_CONFIABLE \
  --identity /ruta/privada/identidad_recuperacion.txt \
  --report /ruta/privada/informes/ENSAYO_NUEVO.json
```

El ensayo exige una identidad nativa privada del usuario con modo 0600 y una huella esperada de procedencia confiable. Comprueba integridad del cifrado, inventario, tamaños y huellas; rechaza rutas ascendentes/absolutas, enlaces y duplicados del archivo TAR. **Una huella no autentica al emisor**: use sólo respaldos propios de procedencia verificada. Restaurar un dump ejecuta las instrucciones SQL de su fuente; un socket privado no constituye una caja de aislamiento frente a SQL malicioso. El ensayo no es un analizador de respaldos de terceros.

La restauración sólo crea un clúster temporal nuevo, restaura en una base vacía y lo retira al finalizar. Nunca promociona el resultado a producción ni borra/modifica registros en un destino activo. La transición a operación, conciliación de cambios posteriores al corte, revisión de sesiones restauradas, custodia de secretos y reanudación de colas requieren un procedimiento posterior. Los eventos se conservan, pero no se ejecutan en el ensayo.

Límites de esta versión: paquete de hasta 1 GiB y 100000 archivos; original de hasta 10 MiB; operaciones externas con límite de 300 segundos. Material descifrado transitorio en directorio privado; para producción debe acordarse almacenamiento temporal cifrado y su política de retirada, pues eliminar archivos no acredita borrado físico seguro. No implementa retención, rotación, PITR/WAL, copia remota ni alerta programada. La versión `age 1.0.0` instalada se utilizó sólo en los ensayos; dependencias y soporte deben revalidarse antes de producción.

## Resultados observados y RPO/RTO

El primer cierre ejecutó **ocho pruebas aprobadas**. Restauró **56 tablas, 317 filas y un adjunto sintético**; la medición del ensayo fue **2.086 segundos**, en el primer ensayo. La repetición 0.9 con MFA recuperó 58 tablas/329 filas en 2.722 segundos. El informe actual `recovery-test-report.json` corresponde a 0.10 con MFA y entrevista (60 tablas, 345 filas, un adjunto, 2.562 segundos), clave efímera separada y ocho pruebas aprobadas. Se probaron también:

- Alteración del cifrado: rechazo por huella y por autenticación del cifrado, incluso al sustituir la huella esperada en la prueba.
- Identidad equivocada, adjunto ausente/modificado y rutas/enlaces/duplicados TAR: fallo sin informe de éxito.
- Destino existente, intento de origen TCP y esquema ajeno: rechazo.
- Inserción concurrente posterior a exportar la instantánea: no aparece en el corte restaurado; dump y huellas permanecen concordantes.

La duración corresponde a una muestra pequeña local; **no demuestra RTO de cuatro horas para producción**. No hay periodicidad, transferencia externa ni medición del último corte recuperable: **RPO de una hora tampoco está demostrado**. Falta definir custodia y destino externo, estrategia de retención y PITR/WAL si se requiere, capacidad/volumen real, disponibilidad de claves y medición desde incidente hasta recuperación operativa. No confundir una copia local cifrada con protección ante pérdida del VPS.

## Referencias técnicas

La instantánea compartida usa [`pg_dump --snapshot`](https://www.postgresql.org/docs/16/app-pgdump.html) y [`pg_export_snapshot`](https://www.postgresql.org/docs/16/functions-admin.html). Las opciones de cifrado e identidad se cotejaron con la ayuda del ejecutable instalado y la [documentación oficial de age](https://github.com/FiloSottile/age/blob/main/doc/age.1.html). No se cambiaron aplicaciones del VPS 194.113.64.91.
