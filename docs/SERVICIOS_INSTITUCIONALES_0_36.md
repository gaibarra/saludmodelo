# Servicios institucionales incorporados

Fuente: [Servicios Modelo](https://www.unimodelo.edu.mx/servicios), consultada el 30/09/2026 mediante navegador, pues el contenido se carga con JavaScript. Se revisó también el catálogo público de licenciaturas de Mérida; no se tomaron contactos de admisiones como contactos clínicos.

| Servicio publicado | Área en la aplicación | Destinatarios | Administración asignada en la aplicación |
| --- | --- | --- | --- |
| Clínica Dental | Odontología | Público general | Escuela de Odontología |
| Clínica de Fisioterapia | Fisioterapia | Público general | Escuela de Salud |
| Consultorio de Nutrición | Nutrición | Público general | Escuela de Salud |
| Readaptación Deportiva | Ciencias del deporte | Público general | Escuela de Salud |
| USC Casita | Atención comunitaria | Público general | Escuela de Salud |
| Unidad de Atención y Prevención de la Salud | Ficha universitaria sin especialidad asignada | Comunidad universitaria | Institucional; adscripción por confirmar |

La clasificación escolar sigue las áreas acordadas para la aplicación; no se presenta como dato de adscripción publicado por el directorio. La última unidad no se convierte en un consultorio de Psicología abierto al público.

Se guardan nombres, horarios, contactos, destinatarios, observaciones, URL, fecha y huella de la fuente. Dataset revisado: `backend/core/data/institutional_services_20260930.json`. Copia del texto consultado: `docs/fuentes-institucionales/servicios-2026-09-30.txt`.

**Discrepancias y límites:** Fisioterapia publica `999301900`, de nueve dígitos, extensión 2217. Se conserva como dato incompleto sin botón para llamar; el conmutador general se muestra por separado. La fuente no indica extensión para Dental, precios concretos, tratamientos ni domicilios específicos. Psicología no aparece como consulta independiente en ese directorio. No se rellenan estos vacíos con datos de otras instituciones, admisiones o inferencias.

El directorio se ve en portada, `/portal/directorio`, páginas de área y panel académico. Cada panel escolar muestra sus propias fichas; el directorio general es información pública. La Unidad de Atención y Prevención aparece en el directorio general con su público destinatario explícito.

Las seis filas operativas nuevas están pendientes de confirmación. No se crearon colaboradores ni se activaron citas. Se conserva el servicio ficticio original y todas sus referencias. Antes de operar, revisar sede, responsables, pertenencia y capacidad; después confirmar el servicio mediante la administración existente. La información pública institucional no equivale a haber habilitado atención clínica real.

Carga revisable, dentro del backend y con un usuario que posea mandato institucional:

```bash
python manage.py import_institutional_services --institution ID --actor CORREO
# Aplicación explícita del mismo plan:
python manage.py import_institutional_services --institution ID --actor CORREO --apply
```

La carga es idempotente y rechaza la reutilización de una ficha de otra institución/escuela. No cambia nombres operativos editados, confirmaciones ni estados de publicación previos al repetirla.
