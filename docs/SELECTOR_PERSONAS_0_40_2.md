# Búsqueda de personas al asignar funciones — 0.40.2

Solicitud del 13/10/2026: agregar búsqueda y orden alfabético a Persona en «Asignar función de colaborador» de Escuelas.

Se incorpora un buscador por nombre/apellidos, con palabras en cualquier orden e ignorando mayúsculas y acentos. Las opciones se ordenan por el nombre completo mostrado con comparación española; el ID desempata nombres iguales. Se muestra el número de resultados o el estado sin coincidencias. Cambiar la búsqueda limpia la selección para impedir enviar una persona oculta; cambiar de escuela también reinicia búsqueda y selección. Se mantiene el select nativo obligatorio, navegación por teclado y el mismo identificador de usuario enviado a la API.

Se utilizan exclusivamente las personas de la escuela seleccionada devueltas por la API existente. Sin cambios de cuentas, funciones, base de datos, permisos o contratos de API. Compilación de producción y TypeScript aprobados. Paquete sólo frontend; no requiere migraciones ni reiniciar backend o base.

Estado: publicado el 13/10/2026 tras autorización expresa. Paquete `deploy/demo/runtime/releases/0.40.2-20261013T162117Z`. Sólo frontend reemplazado; 17 contenedores protegidos intactos. Verificación HTTPS autenticada en ambas escuelas: 54 personas en Salud y 57 en Odontología, orden alfabético, búsqueda por palabras y acentos, estado sin resultados y limpieza de selección. Cero asignaciones enviadas. Evidencias privadas: `selector-verification.json`, `selector-personas.png` y `activate-verified.json` dentro del paquete.
