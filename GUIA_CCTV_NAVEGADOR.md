# CCTV y acceso rápido · actualizado a 1.5.1

Consulta también [Centro de vigilancia](CENTRO_VIGILANCIA_2026-10-27.md) y [Eliminar y sustituir cámaras](ELIMINAR_CAMARAS_2026-10-27.md).

## Abrir tu gafete

Inicia sesión con tu matrícula, contraseña y autenticador. Pulsa **Mi QR** en la barra superior o **Mi QR de acceso** al principio del menú. Cada persona ve su propio gafete; el permiso para consultar gafetes de otras personas no cambia. Las cuentas sin tareas de administración llegan directamente a esta sección.

Puedes descargar la credencial PNG y mostrarla en el teléfono. La terminal comprueba la vigencia, el estado de la cuenta y sus permisos al leerla; la fotografía del QR no sustituye esa comprobación.

## Usar un celular o una webcam como CCTV

1. Desde una sesión de administración, entra a **Monitoreo CCTV → Configurar cámaras → Vincular una cámara nueva**.
2. Escribe el nombre y selecciona la zona. Pulsa **Generar QR de cámara**.
3. Escanea ese QR con el teléfono, o abre el enlace en otra laptop con webcam. Compara el código y pulsa **Confirmar cámara CCTV** en la consola.
4. En el dispositivo que tiene la cámara, pulsa **Transmitir cámara** y concede el permiso del navegador. Para este modo no necesitas IP Camera Lite ni escribir la IP del teléfono.
5. Mantén la página del teléfono abierta y la pantalla encendida. Para terminar, pulsa **Detener transmisión** o **Desvincular este dispositivo**.

En iPhone/iPad utiliza Safari o Chrome con HTTPS; en Android, un navegador con permiso de cámara. Si cambias de cámara o de calidad, pulsa otra vez **Transmitir cámara**. Si un espectador conserva una vista antigua, puede pulsar **Reconectar vista**. Una pestaña de monitoreo que pasa a segundo plano pausa sus vistas y las reconecta al regresar, salvo las pausadas manualmente.

El QR se consume una sola vez y vence en cinco minutos. La cámara aprobada queda limitada a la sesión que la creó, con máximo de 30 minutos desde el inicio de esa sesión. Cerrar sesión, bloquear la cuenta, quitar sus permisos, revocar el vínculo o reiniciar el servidor impide continuar. Los navegadores comprueban los permisos cada segundo y cierran el vídeo al recibir la revocación. El teléfono no recibe una sesión administrativa ni puede leer el directorio. Los permisos del escáner QR y de CCTV son independientes.

## Imagen e información visible

- Conexión directa WebRTC: vídeo del navegador, hasta 30 fps solicitados, sin convertir cada cuadro con Python. El perfil fluido solicita 960 × 540; el de detalle, hasta 1280 × 720. La cámara y la red determinan la resolución y los fps reales.
- Alternativa compatible HTTPS: se activa si la conexión directa falla o el espectador no dispone de WebRTC. El teléfono envía JPEG binario de hasta 640 px de ancho hacia una transmisión MJPEG continua; solicita alrededor de 24 cuadros por segundo, con dos envíos pendientes como máximo y descarte de cuadros atrasados. La tasa real depende de la red y del dispositivo. Se conserva solamente el último cuadro en RAM y no se acumula una cola de vídeo.
- La conexión directa usa STUN de Cloudflare para encontrar la ruta entre dispositivos; ese servicio recibe datos de conectividad, no el vídeo. No se ha contratado un servidor TURN. Si la red bloquea WebRTC, el modo HTTPS utiliza el mismo túnel de la aplicación.
- Hasta ocho canales combinando navegador e IP Camera Lite, en grupos de cuatro vistas. Cada cámara del navegador permite cuatro espectadores, con 16 conexiones de espectadores como máximo entre estos canales. Tener más espectadores consume más subida en el teléfono.
- La imagen muestra nombre, zona, fecha, día, hora de Ciudad de México y estado. El reloj se ajusta con la hora del servidor; la laptop debe tener su hora sincronizada. Es una superposición de visualización, no una grabación ni una marca de evidencia forense.
- Si los cuadros dejan de llegar, aparece **Sin señal**; si pausas una vista, aparece **Pausado**. No se solicita audio ni se graba vídeo.

Las cámaras IP se ven junto a las del navegador en **Vigilancia** y se configuran en **Configurar cámaras → Cámaras con IP Camera Lite / dirección local**. Mantienen la validación de direcciones locales y también muestran el reloj. Su ubicación aparece sin asignar cuando no existe ese dato.

La prueba automática usa dos navegadores Chrome y una cámara simulada: comprueba vídeo WebRTC, alternativa HTTPS, revocación, ausencia de sesión administrativa en el teléfono y diseño móvil. Falta comprobar la cámara física del teléfono del usuario con este modo nuevo. El informe previo de IP Camera Lite corresponde a una prueba distinta.
