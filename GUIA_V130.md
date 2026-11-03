# SECURITY TEAM · Guía de la versión 1.3.0

Actualizada el 20 de octubre de 2026. Aplicación React + Python nativa de Windows.

**Actualización 1.3.1:** vinculación del teléfono como escáner, 8 canales CCTV y captura optimizada. Consulta [GUIA_TELEFONO_Y_CAMARAS.md](GUIA_TELEFONO_Y_CAMARAS.md).

## Abrir y compartir

Cloudflare Quick Tunnel quedó como método activo de publicación. Por elección del propietario, **no pide correo ni PIN externo**. Cada persona entra con matrícula, contraseña y autenticador de SECURITY TEAM; la aplicación verifica cuenta activa, bloqueo, términos y permisos.

- **ABRIR_CLOUDFLARE.cmd** abre el enlace que está ejecutándose.
- **COMPARTIR_CLOUDFLARE.cmd** inicia el servidor y Cloudflare, muestra la nueva dirección y abre el navegador. No ejecutes otra instancia simultánea.
- **DETENER_CLOUDFLARE.cmd** cierra únicamente los procesos registrados y comprobados de esta aplicación.
- **ENLACE_CLOUDFLARE.md** se actualiza automáticamente con la dirección al arrancar.
- Para usar solo la laptop: detén Cloudflare y ejecuta **INICIAR.cmd**.

No necesita Ubuntu, cuenta de Cloudflare, dominio comprado ni pago. La laptop debe estar encendida, conectada a Internet y con el proceso funcionando. Quick Tunnel cambia de dirección al reiniciarse y no ofrece garantía de disponibilidad. No se ha contratado ningún servicio.

Los correos dejan de ser un requisito de acceso en este modo. Se conservaron las 17 direcciones completas en configuración privada para uso futuro; no se utilizan como barrera de acceso actual. El texto incompleto `@gmail.com` se omitió y el correo repetido se deduplicó. No se crearon identidades ni se asignaron privilegios basándose solo en correos.

El acceso de administrador de ejemplo, **9900021**, conserva su rol de **Administrador del sistema**. **9900001** conserva el rol **DPO**. Utilicen sus credenciales y autenticadores actuales. No se restablecieron contraseñas ni factores. La base conserva sus 33 identidades; los compañeros que falten necesitan un alta con su matrícula y datos correctos.

## Qué probar en la demostración

### 1. Términos y privacidad

Después de completar contraseña, MFA y el resguardo de códigos de recuperación, aparece el acuerdo de seguridad. Se requiere marcar la casilla y aceptar la versión v1.0 antes de entrar. Se registra fecha, versión y vía en la auditoría. Directorio y Mi cuenta muestran el estado.

La aceptación es electrónica simple para el proyecto académico. El texto explica CCTV, uso personal de credenciales y supervisión del DPO; no afirma certificación legal ni grabación garantizada 24/7.

### 2. Zonas, tarjetas RFID y gafetes

En **Personas y permisos**, abre una identidad y revisa las zonas, licencias y tarjeta RFID. El lector USB funciona como teclado: enfoca UID, pasa la tarjeta y guarda el perfil. El Enter de la lectura no envía accidentalmente todo el formulario. Se normalizan UID decimal y hexadecimal y se rechazan duplicados equivalentes.

En **Mi cuenta** o en una identidad dentro de tu alcance, descarga la credencial PNG vertical o prepara su entrega al celular. El QR de acceso está firmado y se comprueba contra el estado actual de la base; no concede acceso administrativo. Una fotografía puede copiarse, por lo que el operador debe corroborar al titular.

Para zonas críticas se necesitan **zona autorizada y licencia correspondiente**. Tener una tarjeta registrada, un rol global o aceptar términos no asigna automáticamente una licencia. El Administrador del sistema puede administrar sus licencias desde su perfil en el directorio; no puede editar sus propios permisos de rol por esa vía.

Los gafetes de usuario vencen a las 8 horas; los de invitado al concluir su pase. Bloqueo, baja o cambio de versión de seguridad invalidan las credenciales del usuario según corresponda. Cambiar de dominio no modifica su firma.

### 3. Entrega móvil y renovación conjunta

El enlace de **entrega privada** pertenece a una sola persona. Desde la versión 1.4.0 se canjea una vez y vence en cinco minutos, o antes si termina la visita. El usuario debe autenticar su propia cuenta en ese navegador; el invitado necesita que su anfitrión confirme el código del teléfono. Después puede aceptar los términos y mostrar o descargar su gafete durante una sesión de quince minutos. En Invitados, Renovar entrega permite emitir otro enlace sin recrear la visita. El enlace y el QR de entrada tienen propósitos distintos.

Si cambia la dirección de Cloudflare:

1. Comparte el nuevo enlace general con el grupo.
2. En **Personas y permisos → Entregas móviles del equipo**, pulsa **Renovar entregas móviles**.
3. Descarga la lista privada CSV y entrega cada enlace únicamente a su titular. Las cuentas que necesitan MFA, contraseña inicial, activación o desbloqueo aparecen como pendientes.

No hace falta reconstruir cuentas ni permisos. Las imágenes de gafetes descargadas siguen sujetas a su vigencia y autorización. El botón usa automáticamente la dirección actual del servidor. No envía correos ni mensajes de WhatsApp por sí solo.

El archivo conjunto contiene enlaces privados: no debe publicarse en el grupo. El DPO no puede incluir cuentas de Administrador del sistema. Un administrador no acepta términos silenciosamente por los demás.

### 4. Terminal de acceso

Elige zona y movimiento; usa RFID + Enter, cámara QR o una imagen del QR. El lector QR incluido funciona sin depender de BarcodeDetector; permite Android y iPhone/iPad con un navegador compatible, HTTPS y permiso de cámara. El navegador puede recordar la cámara elegida durante la sesión.

Abre Terminal en un teléfono con una cuenta autorizada para operar y también en la laptop. El resultado se actualiza cada 1.5 segundos. Activa el sonido mediante el botón del navegador y usa **Pantalla de kiosco** para proyectar el veredicto grande. La pantalla muestra nombre, identificación, rol, origen, zona, método, entrada/salida y motivo de rechazo.

Los tonos son generados por Web Audio: dos ascendentes para autorizado y dos graves para denegado. **Presencia actual** permite una salida asistida con auditoría; no convierte una matrícula en un UID RFID. Los controles registran movimientos, sin accionar una cerradura física.

El cupo inicial de bóveda es de 5 y puede ajustarse; controla las licencias de bóveda. Registrar un UID adicional no concede por sí solo acceso a esa zona.

### 5. Invitados

Crea un pase de 2, 4, 8 o 24 horas, con zona y motivo. Deja los términos pendientes para que el titular los acepte desde su celular. Marca aceptación presencial solo si acaba de leerlos y aceptarlos ante ti; esa vía queda auditada.

Abre el pase móvil, acepta términos, presenta su QR en Terminal y luego revoca el pase: la siguiente validación debe ser denegada. El vencimiento se comprueba en cada validación aunque no esté abierto el listado de invitados.

### 6. Licencias y amenazas

El catálogo contiene 4 licencias académicas simuladas, inicialmente de 5, 10, 10 y 40 asientos. No representa suscripciones reales de Microsoft. El Dashboard muestra ocupación; el directorio permite asignar y revocar según alcance. El último asiento se protege con transacciones; cupo agotado devuelve HTTP 409. La baja lógica libera asignaciones y genera auditoría.

**Análisis de Amenazas** ofrece TH-01 a TH-05: fallos/bloqueos, cobertura MFA y términos, accesos físicos rechazados, cambios privilegiados y credenciales críticas en cuentas bloqueadas. Incluye evidencia, severidad, recomendación y falsos positivos. Se muestran solo hallazgos presentes, dentro del alcance del operador y de la ventana consultada.

Si vence el reto MFA de cinco minutos, se informa la caducidad y se vuelve al acceso con contraseña; no se presenta como TOTP incorrecto.

## Configurar IP Camera Lite fácilmente

1. Conecta el teléfono y la laptop servidor a una red que permita comunicación entre ambos. Enciende el servidor **HTTP MJPEG/JPEG** de la aplicación del teléfono. En iPhone/iPad permite el acceso a la red local.
2. En **Monitoreo CCTV → Agregar canal**, escribe un nombre y la **IP actual del teléfono**, puerto y ruta del vídeo. Los botones Android e iPhone/iPad son ejemplos editables; verifica los datos que muestra tu versión de IP Camera Lite.
3. Pulsa **Probar conexión**, elige calidad y pulsa **Guardar canales**. Se admiten hasta ocho canales, en grupos de cuatro vistas.
4. Al cambiar de lugar, sustituye la IP por la que muestra el teléfono y vuelve a probar/guardar. No necesitas editar código. La web no puede conocer automáticamente esa IP sin que el teléfono la comunique.

| Perfil | Salida máxima | Límite de cuadros |
|---|---|---|
| Mayor fluidez | 640 px | hasta 12 fps |
| Equilibrado | 960 px | hasta 15 fps |
| Más detalle | 1280 px | hasta 20 fps |

El servidor mantiene **una captura compartida por canal y un solo cuadro reciente**, sin una cola creciente de vídeo. Redimensiona/comprime JPEG y limita la frecuencia de salida. Los espectadores comparten la captura; se reintenta la conexión si falla. No se garantiza una cifra de latencia: depende del teléfono, la red y el número de espectadores.

Comienza en el teléfono con 640×480 o 720p y 10–15 fps. Bajar solo la calidad en la consola reduce la salida al navegador, pero no reduce lo que el teléfono transmite a la laptop. Evita 1080p/4K si la red está saturada. Mantén el servidor de la cámara activo en el teléfono.

Una red universitaria puede aislar dispositivos aunque usen el mismo Wi-Fi. Si ocurre, ngrok o Cloudflare no solucionan ese aislamiento: utiliza una red donde teléfono y laptop puedan comunicarse. Las rutas RTSP y las páginas de control HTML no son MJPEG/JPEG; copia la ruta HTTP de vídeo o imagen.

La prueba local de webcam solo abre la cámara del dispositivo que usa la web. No convierte por sí sola ese equipo en un canal remoto compartido.

El 20 de octubre se configuró y verificó una cámara real de iPhone / IP Camera Lite mediante HTTP MJPEG, recibiendo cuadros optimizados de 640 × 480. El servidor HTTP de la app debe permanecer activo y el teléfono accesible por la red. También se probó la captura con un servidor simulado. La prueba física del lector RFID sigue pendiente. El formulario reconoce una dirección completa pegada en IP o ruta y separa automáticamente sus campos.

## Archivos y API

Cambios principales: `db_manager.py` (migraciones), `security.py` (identidad y permisos), `features.py` (servicios v1.3), `camera_hub.py` (captura compartida), `server.py` (API), `frontend/app.jsx`, `frontend/features.jsx`, `frontend/styles.css`, `web/` compilado, lanzadores Cloudflare, respaldos y pruebas. Se conserva `share_ngrok.py` como alternativa compatible; su túnel está detenido.

| Operación | Endpoint |
|---|---|
| Consultar/aceptar acuerdo | `GET /api/terms`, `POST /api/auth/accept-terms` |
| Gafete, PNG y entrega individual | `GET /api/users/qr-badge`, `GET /api/users/qr-badge.png`, `POST /api/users/mobile-pass` |
| Renovar entregas conjuntas | `POST /api/mobile-passes/renew` |
| Pase móvil con capacidad firmada | `GET /api/public-pass`, `POST /api/public-pass/accept-terms`, vista `/pass` |
| Zonas del usuario | `GET/POST /api/users/zones` |
| Catálogo y asignaciones | `GET /api/licenses`, `GET /api/users/licenses` |
| Asignar/revocar | `POST /api/users/assign-license`, `POST /api/users/revoke-license` |
| Terminal y salida asistida | `POST /api/access/verify`, `POST /api/access/checkout` |
| Sincronización y presencia | `GET /api/access/latest`, `/api/access/events`, `/api/access/presence` |
| Cupo RFID/bóveda | `GET/POST /api/access/settings` |
| Invitados | `GET /api/visitors`, `POST /api/visitors/create`, `/api/visitors/revoke` |
| Hallazgos | `GET /api/threats` |
| Cámaras | `GET/POST /api/cctv/channels`, `GET /api/cctv/network`, `POST /api/cctv/test`, `GET /api/cctv/stream` |

Todas las mutaciones exigen CSRF, Origin y Host válidos. Las APIs administrativas requieren autenticación completa, términos y permisos; el pase público solo acepta su capacidad firmada vigente. Los QR no contienen contraseñas ni factores MFA. La firma garantiza integridad, no cifra los identificadores del payload.

## Validación y preservación

- 35 pruebas existentes, 20 de integración v1.3/Cloudflare y 5 de captura de cámara: **60/60** correctas.
- Recorridos en Chrome con API y SQLite temporales como Administrador del sistema y DPO; aceptación móvil, QR por imagen con jsQR, PNG, sincronización entre pestañas, audio, revocación, renovación CSV y configuración CCTV.
- QA visual con datos ficticios: móvil de 390 px sin desbordamiento del documento, paleta independiente del modo oscuro, movimiento reducido y 12 pares de contraste del diseño existente.
- Migración real: 33 usuarios; columnas preexistentes, hashes, factores, roles, UID, códigos de recuperación y bytes de `.mfa-key` preservados. El token de ngrok se conservó al ampliar la lista por autorización posterior del propietario.
- Respaldos privados antes de migrar; nueva clave HMAC de QR bajo DPAPI. No se reinició la base ni se reemplazaron factores.

Los reportes están en `tests/resultado-migracion-v130.json`, `tests/resultado-admin-sistema.json`, `tests/resultado-navegador.json` y `tests/resultado-cloudflare-publico.json`. Las imágenes de `design/` usan datos ficticios o el formulario público vacío.

La auditoría local es de solo anexado desde la aplicación y conserva la cola de envío. **Sigue pendiente un receptor independiente**; un túnel no sustituye esa copia. La consola no graba vídeo. Quien controla el usuario de Windows puede modificar el programa y el almacenamiento; DPAPI y los triggers no neutralizan a ese operador.

Para respaldar, detén el servidor y ejecuta `maintenance.py backup DESTINO_NUEVO` con el Python de `.venv`. Conserva base, `.mfa-key`, `.qr-key` y configuraciones DPAPI juntas. El respaldo exige el mismo usuario y equipo de Windows. El ZIP de código excluye datos, respaldos, claves, entornos, dependencias instaladas y ejecutables del túnel.

## Referencias de Cloudflare

[Quick Tunnels y enlaces temporales](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) · [cloudflared oficial](https://github.com/cloudflare/cloudflared/releases) · [Túnel con dominio estable](https://developers.cloudflare.com/tunnel/get-started/).

La publicación actual usa Quick Tunnel y autenticación propia de la aplicación. No usa el plan de identidades de Cloudflare Access, ni necesita registrar los correos de los alumnos en Cloudflare.
