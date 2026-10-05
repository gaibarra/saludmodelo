# Identidad institucional — 0.39.2

Se utiliza el archivo original `frontend/public/images/Modelo.jpg`, conservando proporciones, colores y fondo blanco. Componente compartido InstitutionalLogo, tamaños compactos para navegación/modales y mayor para informes. Sin versiones inventadas ni alteración del escudo.

Cobertura: portada y portal público (servicios, directorio, cuenta de paciente), encabezado y pie del portal, acceso del personal/panel/plan, cabecera institucional compartida para módulos internos, modales de cuentas, informes académicos individuales/consolidados e informes semanales actuales/conservados/recibidos. Icono de pestaña y acceso móvil referencian el mismo recurso.

Los informes imprimibles incluyen el escudo como imagen real, con carga anticipada y estilo de impresión; se evita duplicar la cabecera global cuando el informe ya contiene su marca. Los demás módulos mantienen su cabecera institucional al imprimir. Se conservan título, servicio y escuela propietaria para no confundir la identidad institucional con permisos compartidos.

Cambio exclusivamente de interfaz. No altera registros, contenidos/hashes de informes conservados, exportaciones JSON, autorizaciones ni migraciones. Los documentos históricos y fuentes de entregables fuera de la aplicación no se reescriben.

Publicada 0.39.2 tras autorización expresa del usuario. Sólo frontend actualizado; backend y esquema 0046 permanecen intactos. HTTPS y carga visual autenticada del logo comprobados; el archivo publicado coincide exactamente con el original. Quince contenedores protegidos intactos.

Validación final: build/TypeScript, recorrido de 6 rutas públicas y 15 internas, modal de cuentas, carga real de imagen, PDF del informe académico y cuatro rutas móviles aprobados. Márgenes A4 e imagen del PDF revisados visualmente. Capturas: docs/capturas/logo-acceso-0.39.2.png, logo-portal-movil-0.39.2.png y logo-informe-0.39.2.pdf (datos sintéticos). Paquete listo: 0.39.2-20261001T195746Z.
