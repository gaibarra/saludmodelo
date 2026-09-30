# Salud y Odontología: escuelas independientes

Requisito comunicado por el usuario el 30/09/2026. Sustituye la interpretación de Odontología como servicio administrado por la Escuela de Salud. **Implementada, configurada y publicada en 0.35 el 30/09/2026.** Véanse `ENTREGA_0_35.md` y `CONFIGURAR_ESCUELAS.md` para alcance y límites.

## Estructura y experiencia de uso

Universidad Modelo contiene dos escuelas del mismo nivel: Escuela de Salud y Escuela de Odontología. Ninguna depende de la otra. La Clínica Dental es un servicio de Odontología; no equivale a la escuela completa. El campus y las sedes siguen describiendo ubicaciones físicas, no jerarquías académicas.

Cada escuela necesita su dashboard, identificación visual y administración de sus servicios, personal, ciclos, alumnos, supervisores, prácticas, rúbricas e informes. Una misma plataforma y un portal público común pueden atender a ambas escuelas sin compartir permisos administrativos. Tener acceso a pestañas de servicios como paciente no concede acceso a la gestión interna.

La Dirección de Salud podrá consultar y obtener información académica de prácticas de alumnos de Odontología durante el ciclo y en sus informes de cierre. Ese permiso será explícito y de sólo lectura: no convierte a Salud en superior jerárquico ni permite modificar datos o cerrar ciclos de Odontología. Los consolidados distinguirán siempre escuela propietaria, servicio y ciclo.

## Matriz de autoridad requerida

| Actor | Administración propia | Información académica de Odontología | Cambios y cierre de Odontología |
|---|---|---|---|
| Dirección de Salud | Escuela de Salud | Consulta de prácticas, avance, competencias e informes; obtención de informes autorizados | No |
| Dirección de Odontología | Escuela de Odontología | Consulta de su escuela | Sí, según sus funciones; la evaluación corresponde al supervisor asignado |
| Supervisores | Sus asignaciones vigentes | Sólo alumnos/prácticas asignados | Revisión y evaluación dentro de su asignación; sin autoridad general de Dirección |
| Alumnos | Sus entregas permitidas | Sólo sus propios registros e informes autorizados | Sin administración ni autoevaluación |
| Pacientes y público | Su propia cuenta/solicitudes | Sin acceso | No |

No se infiere acceso recíproco de Odontología a Salud. Tampoco se concede a Salud acceso transversal a pacientes, expedientes clínicos, gestión de citas, cuentas, nombramientos, presupuestos o configuraciones de Odontología. Consultar/exportar información académica debe comprobar el permiso vigente en el servidor, incluidas consultas directas por identificador.

## Cambio técnico necesario

El modelo anterior a 0.35 tenía institución, campus, sede y servicio, pero no una escuela como unidad de administración. `InstitutionMandate` concedía autoridad institucional y los módulos académicos utilizaban ese alcance. En 0.35 la autoridad escolar y la consulta compartida tienen controles independientes. Por tanto, cambiar nombres o añadir un filtro de pantalla no garantiza la independencia solicitada.

1. Incorporar escuelas bajo la Universidad, con claves y pertenencia explícitas de servicios y registros académicos. Conservar identificadores e historial; no convertir cada escuela en una universidad ficticia ni deducir pertenencia a partir de nombres de personas.
2. Introducir autoridad administrativa por escuela y consulta académica compartida como permisos distintos, con vigencia, revocación y trazabilidad. Una dirección escolar no debe recibir un mandato institucional global para poder trabajar.
3. Aplicar la separación en APIs, opciones/listados, administración, tareas, solicitudes, exportaciones, informes, cierres y procesos programados. Revisar también accesos heredados: no basta separar el módulo académico.
4. Preparar dashboards propios, selector de escuela para personas autorizadas y vista de consulta de Odontología para Salud, sin controles de edición ajenos.
5. Adaptar informes nuevos para identificar escuelas y alcance de consulta. No reescribir informes históricos ni invalidar sus huellas de integridad; documentar la pertenencia histórica sin alterar el corte original.
6. Ensayar una migración explícita de los datos de demo y probar aislamiento, acceso de lectura de Salud, denegación de escritura/exportaciones indebidas y revocación. Datos no clasificados deben quedar pendientes de asignación, sin heredar permisos de ambas escuelas.
7. Generar una nueva entrega y un nuevo paquete de redespliegue. La 0.34 preparada quedó superada y su activador la rechaza; sus respaldos e imágenes anteriores se conservan.

## Referencias organizativas y de atención aportadas por el usuario

- Dirección de la Escuela de Salud: Carla Amira Leon Pinto, según el contexto aportado para la reunión.
- Dirección de la licenciatura en Cirujano Dentista / Escuela de Odontología: **C.D. E.P. Mario Sosa Correa**, según la indicación del usuario. Referencia aportada: https://www.instagram.com/p/DKihE3xsCG7/
- Clínica Dental: atención al público por alumnos avanzados bajo supervisión de especialistas, a bajo costo, según información aportada.
- Teléfono: **999 930 1900**, extensión **2806**; alternativa **2210**.
- Horario aportado: lunes a viernes de **7:00 a 14:00** y **15:00 a 20:00**; sábado de **8:00 a 13:00**.
- Ubicación aportada: campus universitario, Antigua carretera a Cholul, 200 metros después del Periférico Oriente.
- Fuente institucional indicada: https://www.unimodelo.edu.mx/servicios

Se intentó consultar la página institucional y la publicación de Instagram, pero no se pudo recuperar contenido suficiente para verificar independientemente estos datos. Se conservan como información proporcionada por el usuario, pendiente de confirmación antes de publicarla como directorio vigente. Posteriormente, el usuario autorizó crear las cuentas nominales y sus nombramientos; quedaron configurados en el despliegue 0.35. El horario informado no implica disponibilidad de citas ni reserva automática.
