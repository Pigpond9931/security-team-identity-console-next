# Cámara del teléfono y CCTV · versión 1.3.1

Para CCTV desde el navegador y el acceso directo al gafete, consulta [GUIA_CCTV_NAVEGADOR.md](GUIA_CCTV_NAVEGADOR.md).

## Usar el celular como lector de gafetes en una laptop sin webcam

1. Inicia sesión en la laptop y abre **Terminal de Acceso**. Elige la puerta y entrada/salida.
2. Pulsa **Vincular teléfono como escáner**. Escanea el QR con la cámara normal del celular, o envíate su enlace de vinculación.
3. Compara el código de seis cifras que muestran teléfono y laptop. En la laptop pulsa **Confirmar teléfono**.
4. En el celular pulsa **Encender cámara del teléfono** y permite usar la cámara. Apunta al gafete QR de otra persona.
5. El veredicto aparece en el teléfono y en la laptop, cuya pantalla se actualiza cada 1.5 segundos. Puedes activar el sonido y la pantalla de kiosco en la laptop.
6. Después de cada lectura pulsa **Leer siguiente gafete**. Esto evita que un mismo gafete registre entrada y salida accidentalmente mientras permanece frente a la cámara.

**Para esta función no necesitas IP Camera Lite, webcam en la laptop ni escribir una IP.** El análisis se hace en JavaScript en el navegador del teléfono; solo se envía el contenido leído del QR para comprobar permisos. El vídeo permanece en el teléfono. Basta que teléfono y servidor tengan conexión al enlace HTTPS; no requieren estar en la misma red local para escanear.

Las laptops con webcam conservan **Encender cámara QR** y el selector de cámaras. También se puede capturar/cargar una foto del QR desde el teléfono como alternativa.

El enlace de vinculación es de un solo uso y vence en cinco minutos. Se requiere aprobación en la laptop. El vínculo aprobado dura como máximo 30 minutos y termina antes si vence o se cierra la sesión del operador, se bloquea/desactiva su cuenta, pierde permisos o se pulsa **Desvincular teléfono**. No entrega al teléfono la contraseña ni una sesión administrativa. Cambiar puerta o acción en la laptop requiere pulsar **Aplicar zona y acción al teléfono**.

Mantén la página del escáner abierta y la pantalla del teléfono encendida. Si denegaste la cámara, cambia el permiso del sitio en Safari/Chrome y vuelve a abrir la página. Al reiniciar el servidor o cambiar el enlace de Cloudflare hay que volver a vincular el teléfono.

## Cámaras de monitoreo CCTV

Se amplió el máximo de **4 a 8 canales**. Se muestran cuatro por grupo para mantener el panel ligero; usa **Siguientes cámaras** para ver los demás. Los nombres, direcciones y perfiles se conservan en el servidor.

- **Mayor fluidez:** hasta 640 px, objetivo de hasta 12 fps.
- **Equilibrado:** hasta 960 px, objetivo de hasta 15 fps.
- **Más detalle:** hasta 1280 px, objetivo de hasta 20 fps.

Estas cifras son límites de salida, no una garantía de cuadros por segundo. La consola muestra los fps observados y la edad del último cuadro. El teléfono de origen, Wi-Fi y conexión de Internet determinan el resultado real. Configura también IP Camera Lite a una resolución/frecuencia razonables: para empezar, 640×480 o 720p y 15–20 fps.

El servidor mantiene una captura compartida por canal y un solo cuadro reciente. Selecciona el cuadro completo más nuevo de cada bloque recibido, evita recomprimir JPEG pequeños que ya sirven y acota el trabajo de codificación simultáneo. No acumula una cola creciente de vídeo. La comprobación local con JPEG sintético está en `tests/resultado-optimacion-camaras.json`; no representa una medición de latencia de la red.

Puedes **Pausar vídeo** en cada canal. El vídeo también se pausa cuando la pestaña queda oculta. Hay un máximo de 16 vistas de vídeo concurrentes en el servidor, con capacidad reservada para accesos, escáneres y administración. Cada espectador activo consume una vista por cámara; múltiples espectadores comparten la captura de origen.

Para CCTV con IP Camera Lite, teléfono y laptop servidor sí necesitan una red que permita comunicación entre ellos. Mantén el servidor HTTP de esa app activo. El formulario acepta IP, puerto y ruta (`/video`), o separa una dirección completa pegada en IP/ruta. La configuración admite únicamente IP privadas y puertos de vídeo autorizados; no se abrieron direcciones arbitrarias ni servicios de Internet.

Para usar un mismo teléfono como lector de gafetes, abre el **escáner web**. Para dejarlo como cámara CCTV, abre **IP Camera Lite**. Cambiar de app puede interrumpir la cámara anterior, especialmente en iPhone; para mantener ambas funciones simultáneamente utiliza teléfonos distintos.

## Implementación y validación

Nuevos archivos: `phone_links.py` y `frontend/phone-scanner.jsx`. Se actualizaron terminal, CCTV, captura de vídeo, servidor HTTP y políticas de publicación. El enlace conserva las comprobaciones de CSRF, Origin y Host. La lectura delegada solo acepta QR y la puerta/acción configuradas por el operador, comprobando su permiso actual en cada petición. Los tokens y la sesión del operador no aparecen en los registros.

Endpoints POST del operador: `/api/scanner/create`, `/status`, `/approve`, `/configure`, `/revoke`. Endpoints públicos limitados por capacidad: `/api/scanner/claim`, `/poll`, `/read`, `/disconnect`, bajo el mismo prefijo `/api/scanner`. Vista móvil: `/scanner`.

Validación: 35 pruebas existentes, 20 de v1.3, 8 de vinculación/permisos y 5 de cámara. El recorrido real de React/API/SQLite se comprobó con dos contextos de navegador independientes: confirmación, cámara simulada, lectura de gafete, sincronización, ausencia de sesión administrativa en el teléfono y desvinculación. La prueba física del escáner en tu iPhone/Android debe completarse permitiendo la cámara y leyendo un gafete real. Se conservan los usuarios, factores, contraseñas, zonas y canales existentes.
