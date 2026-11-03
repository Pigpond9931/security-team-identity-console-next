# CCTV: sesiones de hasta cuatro horas (1.5.3)

Las cuentas con permisos CCTV tienen un plazo absoluto de cuatro horas desde su inicio de sesión autenticado. Las cuentas sin CCTV conservan treinta minutos. El tráfico de vídeo no renueva indefinidamente ningún plazo.

1. Entra con una cuenta autorizada y abre el centro de vigilancia.
2. Crea el canal y abre el QR de vinculación en el teléfono o en otra laptop con cámara.
3. Compara el código y aprueba el dispositivo en la sesión que creó el vínculo.
4. Pulsa Transmitir cámara. Mantén abierta la página del teléfono, la pantalla encendida y alimentación suficiente.
5. El canal termina como máximo al cumplirse cuatro horas del inicio de sesión de su propietario. Si lo enlazas más tarde, queda menos tiempo; la pantalla del teléfono muestra los minutos restantes.
6. Para otra jornada, vuelve a iniciar sesión y enlaza de nuevo las cámaras.

El QR inicial sigue siendo de un solo uso y vence en cinco minutos. Los escáneres QR de acceso conservan su límite independiente de treinta minutos. Cerrar sesión, desvincular el canal, bloquear la cuenta o retirar sus permisos interrumpe el acceso. Los reinicios del servidor eliminan los canales en RAM.

La sesión técnica del teléfono y su cookie de publicación admiten cuatro horas, pero no dan acceso administrativo ni superan el vencimiento del canal. Se mantienen CSRF, cookies HttpOnly y comprobaciones de permisos durante la transmisión.

## Red de la universidad

Puedes distribuir teléfonos y otras laptops con cámara que abran la misma aplicación. Cada canal debe ser aprobado por quien lo creó; no hace falta instalar otro servidor en cada laptop. La distancia relevante es a los puntos de acceso Wi-Fi y su cobertura. Otra laptop no amplía esa cobertura por sí sola.

WebRTC intenta vídeo directo y utiliza la ruta HTTPS compatible cuando la red impide la conexión directa. Una red universitaria puede aislar clientes o limitar tráfico: realiza un ensayo desde las posiciones definitivas. Ampliar la duración de sesión no elimina cortes de Wi-Fi, suspensión del teléfono ni límites de batería.

## Validación

`tests/test_cctv_duration.py` comprueba con reloj simulado los límites de treinta minutos y cuatro horas, la limpieza de sesiones, QR de cinco minutos, uso único, cookies del teléfono, cierre de sesión y retirada de permisos. Los demás grupos de pruebas se ejecutan en procesos separados. Esto no sustituye un ensayo físico de cuatro horas con teléfonos y red reales.
