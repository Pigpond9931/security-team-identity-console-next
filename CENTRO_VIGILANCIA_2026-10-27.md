# Centro de vigilancia · versión 1.5.0

## Cómo usarlo

Entra a **Monitoreo CCTV → Vigilancia** con tu cuenta habitual. Selecciona un canal en la lista para verlo en grande, o usa **Cámara anterior / Cámara siguiente** y las flechas del teclado. **Mosaico** muestra hasta cuatro canales; los botones de navegación cambian de grupo. El catálogo combina las cámaras del navegador y las cámaras IP.

**Ronda automática** recorre los canales cada 15 segundos en vista individual. Puedes detenerla con el mismo botón. **Pantalla completa** amplía el centro; vuelve a pulsar el botón o usa Escape para salir. En teléfonos que no ofrecen la API de pantalla completa se amplía dentro de la página. Cada imagen conserva nombre, estado, día, fecha y hora de Ciudad de México.

La pestaña **Configurar cámaras** permite vincular un teléfono o webcam, confirmar su código y configurar los canales IP. Después de vincularlo, vuelve a **Vigilancia**. El teléfono debe pulsar **Transmitir cámara**, conceder permiso y mantener su página abierta y la pantalla encendida.

## Acceso por permisos

Se conservan los permisos existentes; esta actualización no modifica cuentas, contraseñas, MFA, licencias ni zonas:

| Cuenta o permiso vigente | Vigilancia | Configuración |
| --- | --- | --- |
| Administrador del sistema / DPO | Sí | Sí; aprobación de destinos IP |
| Licencia `LIC-CCTV-ADMIN` | Sí | Sí; solicita aprobación de destinos IP |
| Guard, área Monitoring o licencia `LIC-CCTV-MON` | Sí | No |
| Cuenta sin permiso CCTV | No | No |

Los permisos son de CCTV completo, conforme al modelo vigente; no se añadieron restricciones por zona de cámara. El permiso de cámaras no concede administración de personas ni operación de la terminal RFID. La vinculación de una cámara del navegador pertenece a la sesión que la creó. Desde 1.5.1, cualquier administrador de cámaras puede eliminarla para liberar espacio; la aprobación de su emparejamiento permanece en la sesión creadora. Consulta [Eliminar y sustituir cámaras](ELIMINAR_CAMARAS_2026-10-27.md). El vídeo IP sigue requiriendo un destino exacto aprobado por administración global.

La API comprueba sesión, cuenta, términos y permiso antes de abrir una vista. Revalida la autorización durante la transmisión, aproximadamente cada segundo. Un identificador de espectador pertenece a una sesión y no funciona como enlace público. Al cerrar sesión o revocar el permiso se detiene la transmisión. La cámara del teléfono recibe únicamente una cookie HttpOnly para publicar su vídeo.

## Cambios de fluidez

- WebRTC sigue siendo la vía preferida: la cámara solicita hasta 30 fps, con prioridad de mantener fluidez cuando el navegador admite ese ajuste. La resolución solicitada es 960 × 540 o 1280 × 720, según el perfil. El dispositivo y la red determinan los valores reales.
- Si WebRTC falla, se abre una conexión MJPEG HTTPS continua. Se eliminan la descarga de cada imagen por separado, la espera fija entre descargas y el transporte JSON/base64 del teléfono nuevo.
- El teléfono genera JPEG binario de hasta 640 px, aproximadamente cada 42 ms, solo si algún espectador necesita el modo compatible. Puede tener dos envíos pendientes; descarta cuadros cuando se llena ese límite. El servidor rechaza cuadros fuera de orden y conserva únicamente el más reciente, sin cola por espectador.
- Los canales IP tienen objetivos de 24 fps en los perfiles fluido/equilibrado y 25 fps en detalle. La captura se comparte entre espectadores y evita recomprimir JPEG pequeños que ya cumplen el perfil. No puede crear cuadros que la cámara de origen no envía.
- Se eliminan las recargas forzadas de imágenes cada 28 segundos y el cierre del flujo IP cada 45 segundos. Solo se transmiten las vistas abiertas: una en individual y hasta cuatro en mosaico. La configuración no abre vídeo. Las vistas se suspenden al ocultar la pestaña y se reconectan al regresar, respetando una pausa manual.
- Se conservan ocho canales combinados, cuatro espectadores por cámara del navegador y 16 flujos de servidor simultáneos. Las colas de señalización, tamaños JPEG y solicitudes también permanecen limitados.

El reloj es una superposición de visualización. No hay grabación, audio ni reconocimiento facial. Las imágenes temporales están en RAM.

## Verificación y límites

La verificación utiliza SQLite temporal, identidades ficticias, Chrome con cámara simulada y un servidor MJPEG de prueba. Incluye conexión WebRTC, transmisión binaria continua, imágenes fuera de orden, revocación, controles HTTP/CSRF, navegación, liberación de espectadores, mosaico, ronda, pantalla completa y presentación móvil. Los informes están en `tests/resultado-cctv-*.json`.

La medida de fluidez local se guarda con su duración y número de cuadros en `tests/resultado-cctv-fluidez.json`; no representa la velocidad de un teléfono físico a través de Internet. Hace falta probar tu celular y tu red: Wi-Fi congestionado, aislamiento de dispositivos, ahorro de batería, múltiples espectadores y la subida de la laptop pueden limitar el resultado. Para IP Camera Lite, configura también el origen a 640 × 480 o 720p y 24–30 fps si el teléfono lo permite; si la red se satura, baja resolución o tasa en el origen.

El reinicio para instalar la actualización termina las sesiones y vinculaciones de cámaras temporales. Los usuarios inician sesión otra vez y los teléfonos se vinculan con un QR nuevo. El canal IP guardado y todas las identidades se conservan. El túnel gratuito puede generar otra URL al reiniciar.
