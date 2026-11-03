# Aviso automático de la terminal

La actualización visual del 27/10/2026 organiza la página en **Operación**, **Actividad** y **Configuración**. Consulta [la guía actualizada](TERMINAL_VISUAL_2026-10-27.md). En Operación, elige **Gafete QR** para abrir sus herramientas; los movimientos y salidas asistidas están en Actividad.

Desde la versión 1.4.1 puedes seleccionar un área con los botones F1–F4; consulta [INTEGRACION_RFID_2026-10-26.md](INTEGRACION_RFID_2026-10-26.md) para la correspondencia, el aforo y la bitácora CSV. Abre **Terminal de Acceso** y elige la zona y la acción. Al verificar un QR o pasar una tarjeta RFID y Enter, la decisión aparece automáticamente sobre toda la ventana de la aplicación:

- **Acceso permitido**, con un escudo de confirmación y fondo verde oscuro.
- **Acceso denegado**, con un escudo de rechazo y fondo rojo oscuro.
- Nombre, identificación, zona, entrada o salida, hora de Ciudad de México y motivo de la decisión.

El resultado utiliza texto e iconos además del color. Se cierra después de cuatro segundos, con **Siguiente lectura**, Escape o Enter. Al cerrar vuelve el foco al lector RFID. Si pasas otra tarjeta mientras se muestra el aviso, el lector USB tipo teclado puede enviar su código y Enter sin cerrarlo primero; se verifica esa nueva credencial y se sustituye el aviso por su resultado.

El QR puede leerse desde la webcam, desde una imagen o desde el teléfono vinculado como escáner. Una lectura recibida desde el teléfono aparece en la terminal mediante sincronización cada segundo. Las tarjetas se siguen comprobando en el servidor: este aviso no concede permisos por sí mismo.

No necesitas activar **Pantalla de kiosco** ni abrir otra pestaña. El modo kiosco sigue disponible para dejar una pantalla dedicada. El aviso ocupa la ventana de la página, sin solicitar el modo de pantalla completa del navegador.

Al volver a entrar a la terminal se conserva la última decisión como historial; no se anuncia otra vez como una lectura nueva. La consulta periódica tampoco repite el aviso ni el sonido para el mismo evento. Si falla una solicitud, se muestra el error y no se inventa una decisión de acceso.

El sonido conserva su opción de activación independiente. La consola registra decisiones, pero no acciona una cerradura física.

Validación: navegador Chrome con API y SQLite temporales, QR permitido y denegado, RFID emulado mientras el aviso permanece abierto, lectura desde el teléfono vinculado, diseño móvil, cierre automático, Escape y devolución del foco al lector. El lector físico no se conectó durante estas pruebas. Esta actualización modifica el frontend; no cambia cuentas, MFA, datos ni el enlace del túnel.
