# Escuelas independientes — versión 0.35

Salud y Odontología son unidades del mismo nivel dentro de la Universidad. Esta versión incorpora propiedad escolar, dashboards separados y administración de cuentas, servicios y colaboradores por escuela. La Dirección de Salud puede consultar prácticas e informes de Odontología mediante una autorización académica de lectura, sin administrarla.

## Uso en lenguaje sencillo

1. Ingresar con la cuenta y completar MFA cuando corresponda. Abrir **Escuelas** en el menú.
2. La Dirección de Odontología encuentra el dashboard de su escuela: alumnos, ciclos, informes y prácticas por estado. Desde su administración puede crear cuentas, registrar/confirmar servicios y asignar colaboradores o supervisores con fechas de vigencia.
3. En **Prácticas académicas → Configurar núcleo académico**, elegir la escuela para registrar alumnos, ciclos y rotaciones. Las cuentas deben pertenecer a esa escuela. No se admite una rotación que mezcle el alumno, ciclo y servicio de escuelas distintas.
4. En **Competencias e informes**, cada dirección configura rúbricas y conserva/cierra informes de sus propios ciclos. Los supervisores conservan su función de evaluar a los alumnos asignados; una dirección no se convierte automáticamente en evaluadora.
5. Para habilitar la consulta de Salud, la Dirección de Odontología abre **Compartir información académica**, elige la Escuela de Salud, indica vigencia y motivo y confirma. La autorización incluye prácticas, avance, competencias e informes académicos, también durante el ciclo.
6. Dirección de Salud encontrará Odontología señalada como **Sólo consulta académica**. Puede consultar e imprimir/guardar los informes disponibles. No puede editar, anular prácticas, administrar cuentas, cambiar rúbricas, generar cortes en nombre de Odontología ni cerrar o reabrir sus ciclos.
7. Odontología puede revocar el permiso con un motivo. La siguiente petición al servidor pierde el acceso, incluso al abrir directamente una dirección de informe. Revocar no retira archivos que la persona ya hubiera descargado ni información previamente mostrada en su navegador.

No hay consulta recíproca automática. Las autorizaciones no incluyen expedientes clínicos, pacientes, citas, cuentas ni presupuestos de la otra escuela. El portal público sigue reuniendo los seis servicios y ahora identifica a ambas escuelas como pares.

## Protección de permisos e historial

- Se incorporaron escuela, pertenencia de cuentas, nombramiento de Dirección escolar y autorización de consulta académica entre escuelas, con vigencia y revocación.
- Servicios, alumnos y ciclos tienen escuela propietaria. Los registros anteriores permanecen sin clasificar hasta que un operador aplique un plan explícito.
- Una cuenta con nombramiento escolar deja de utilizar mandatos institucionales amplios heredados. Sus roles de servicio se limitan a sus escuelas actualmente administradas; al vencer o revocarse el nombramiento no reaparece la autoridad global anterior. Para tareas realmente universitarias se conserva una cuenta institucional separada.
- Los controles se aplican en el servidor. Los accesos comunes del gestor utilizan el alcance escolar; la autorización académica compartida no entra en esos permisos administrativos.
- Los informes nuevos identifican la escuela. Los informes anteriores conservan el contenido y huella originales; la escuela asignada posteriormente se presenta como contexto actual, sin reescribir el corte.
- Consulta del dashboard compartido e informes compartidos registrada en auditoría. Las altas, clasificación y concesión/revocación de acceso también conservan actor y motivo.
- MFA obligatorio para Dirección escolar cuando está habilitada la política de MFA privilegiado.

## Configuración y migración

La migración `0042_school_boundaries` agrega la estructura; no inventa cuentas, directores, pertenencias ni autorizaciones. No identifica escuelas comparando nombres de personas ni convierte cada escuela en una universidad separada.

El comando `configure_schools --plan RUTA` valida un plan dentro de una transacción que se revierte. `--apply` confirma la clasificación explícita. Exige cuentas institucionales existentes y activas, otro aprobador, miembros e identificadores enumerados. Rechaza asignaciones repetidas, registros de otra institución, traslados de propiedad y rotaciones mezcladas. No crea automáticamente permisos compartidos. Véase [guía de configuración](CONFIGURAR_ESCUELAS.md).

La clasificación de un ciclo incrementa su revisión: un borrador previo debe regenerarse antes de cerrar. Los cortes históricos y cierres ya conservados no se reescriben.

## Verificación y publicación

- Compilación 0.35 y TypeScript correctos.
- Tres recorridos de navegador con API/base propias: separación escolar y revocación; núcleo académico; evaluación, PDF, cierre y reapertura.
- Restauración de la copia previa y migración hasta 0042 por socket Unix privado: 2.650 registros originales de 39 tablas conservados.
- **337 pruebas backend aprobadas**, incluidos aislamiento escolar, revocación, clasificación transaccional, migraciones y regresiones del gestor. Checks, migraciones pendientes y OpenAPI sin advertencias. Se aisló la caché de la prueba CSRF para no heredar intentos de acceso de otras pruebas; el limitador de producción no se desactivó.
- Imágenes 0.35 construidas y verificadas sin red/base activa: backend correcto y ocho rutas de interfaz, con identificación de Odontología. Los 16 contenedores activos conservan identidad, inicio, imágenes, puertos y montajes.

**Publicada el 30/09/2026 por autorización expresa del usuario.** Migraciones 0039–0042 aplicadas, cuentas institucionales de Carla, Mario y Gonzalo creadas, escuelas clasificadas y consulta de Salud a Odontología configurada. Ver `deploy/demo/REDEPLOY_0_35.md`. No quedan migraciones pendientes; cada titular debe completar su inscripción MFA personal. El paquete 0.34 sigue superado y no debe reutilizarse.

## Límites que se conservan

La administración escolar cubre cuentas nuevas, servicios, colaboradores y seguimiento académico propio. La creación de escuelas y nombramientos de sus directores corresponde al operador con plan revisado. La vinculación de una cuenta existente a otra escuela no se ofrece como alta automática desde la interfaz.

El calendario general, presupuesto/capacidad institucional y recuperación excepcional institucional permanecen reservados a la administración universitaria; no se delegan globalmente a ninguna escuela. Si se requiere distribuir también esas competencias por escuela, se necesita otro incremento específico. No se permite a Salud utilizarlas para administrar Odontología.

Continúan pendientes los criterios institucionales de acreditación, sustitución de supervisores, correcciones académicas versionadas, archivos académicos privados, actividades colectivas e integración clínica/escolar. La creación de cuentas nominales fue autorizada posteriormente por el usuario y se realizó en el despliegue. Los datos de contacto público de la clínica siguen pendientes de confirmación independiente. Registro de pacientes e IA externa permanecen desactivados en la preparación de demostración.
