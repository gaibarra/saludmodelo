# Configurar escuelas conservando los registros

Procedimiento para el operador de esta aplicación. No ejecutado sobre la demostración pública. Antes de aplicarlo: respaldo, ensayo privado y revisión de identidades/servicios; una migración de esquema por sí sola no separa datos ya existentes.

## Plan explícito

Preparar un JSON privado con esta estructura. Los números y usuarios son ejemplos, no identificadores para copiar sobre la base activa:

```json
{
  "institution": 123,
  "approved_by": "operador_institucional_existente",
  "starts": "2026-10-01",
  "ends": "2027-09-30",
  "rationale": "Clasificación revisada para la demostración sintética",
  "schools": [
    {
      "code": "salud",
      "name": "Escuela de Salud",
      "director": "direccion_salud_demo",
      "members": ["direccion_salud_demo", "supervisor_salud_demo", "alumno_salud_demo"],
      "services": [1001],
      "cycles": [2001],
      "students": [3001]
    },
    {
      "code": "odontologia",
      "name": "Escuela de Odontología",
      "director": "direccion_odontologia_demo",
      "members": ["direccion_odontologia_demo", "supervisor_dental_demo", "alumno_dental_demo"],
      "services": [1002],
      "cycles": [2002],
      "students": [3002]
    }
  ]
}
```

Todas las cuentas deben existir y estar vinculadas a la institución. No se crean contraseñas desde este archivo. Usar las fechas realmente autorizadas; las del ejemplo no constituyen un nombramiento. Un mismo identificador no puede aparecer en dos escuelas. Los registros no enumerados permanecen intactos y sin reclasificación.

Si un ciclo histórico contiene servicios de escuelas distintas, el comando lo rechaza. No dividir ni trasladar ese ciclo automáticamente: debe prepararse una solución de conservación del historial para ese caso.

## Validar y aplicar en el entorno propio elegido

Con el entorno Django y la conexión de **esta aplicación** configurados explícitamente por el operador:

```bash
python manage.py configure_schools --plan /ruta/privada/plan-revisado.json
```

Muestra cantidades e identificadores, sin contraseñas; revierte la transacción. No implica aprobación ni concede permisos persistentes.

Después del respaldo y ensayo, el operador puede aplicar el plan revisado:

```bash
python manage.py configure_schools --plan /ruta/privada/plan-revisado.json --apply
```

No usar estos comandos con bases o contenedores de otras aplicaciones. En Docker, deben ejecutarse con la imagen nueva del proyecto Salud Modelo y el archivo del plan montado sólo para esa operación; no incluye un montaje permanente de respaldos o secretos.

## Comprobar antes de publicar

1. Dirección de Odontología ve y administra únicamente su escuela; Dirección de Salud, la suya.
2. Odontología concede en la interfaz la consulta académica a Salud con vigencia y motivo. Salud puede consultar e imprimir informes; los intentos de modificación son rechazados.
3. Revocar el permiso elimina el acceso en la siguiente petición, incluida una URL de informe conocida.
4. Alumnos y supervisores conservan su alcance propio. Revisar nombramientos heredados y completar los miembros explícitos necesarios.
5. Los informes históricos mantienen sus huellas y los datos sin clasificar no aparecen por defecto en ambas escuelas.
6. Preparar imágenes, respaldo y manifiesto nuevos para la versión 0.35. El paquete 0.34 está superado y no debe desbloquearse.

La configuración de datos de demo debe utilizar nombres ficticios; los nombres reales informados para las direcciones no equivalen a autorización para crearles cuentas o asignar contraseñas.
