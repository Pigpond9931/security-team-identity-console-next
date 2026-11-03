# Terminal RFID · versión 1.4.1

Se revisó el archivo `control_acceso 1.py` facilitado por el propietario y se adaptaron sus mejoras de operación a la aplicación React/Python existente. El archivo de referencia no se ejecutó ni se importaron sus usuarios, tarjetas o estados de ejemplo.

## Botones de área

| Atajo | Botón | Zona física existente |
| --- | --- | --- |
| F1 | Access Control | Bóveda Principal Data Center |
| F2 | Identity Management | Sala de Servidores Críticos |
| F3 | Monitoring | Centro de Monitoreo CCTV |
| F4 | IAM | Acceso General |

La correspondencia conserva el mapa por área que ya usaba el proyecto. Cada botón muestra su zona física y queda deshabilitado si el operador no puede operar esa puerta. Elegir un área no concede permisos al portador: cada lectura verifica cuenta activa, bloqueo, MFA, términos, zona y licencia crítica correspondiente. Un rol global tampoco sustituye una licencia física.

Haz clic o pulsa F1–F4 y pasa la tarjeta. El cambio limpia un UID parcialmente escrito, detiene una captura QR local en curso y devuelve el foco al lector. Durante un aviso de resultado se conserva la zona de la decisión; puedes pasar la siguiente tarjeta como antes. Si tienes un teléfono vinculado y cambias de zona, pulsa Aplicar zona y acción al teléfono antes de continuar las lecturas móviles; el teléfono muestra la puerta que realmente está operando.

## Mejoras integradas

- Reloj con día, fecha y hora de Ciudad de México.
- Botones de área visibles con selección marcada, además del selector de puerta existente.
- Contadores de personas dentro del alcance del operador y de la zona seleccionada.
- Movimientos recientes (hasta 50), con persona, zona, RFID/QR, entrada/salida, resultado y motivo.
- Exportación CSV de los movimientos visibles, con fecha UTC y protección contra fórmulas en celdas. No descarga tokens QR, secretos MFA ni contraseñas.
- Aforo global configurable por administración global. Se guarda en SQLite; no se pierde al reiniciar.
- Se mantienen avisos automáticos a pantalla completa, sonido opcional, lectura RFID tipo teclado, normalización decimal/hexadecimal y de ceros iniciales, QR por cámara y móvil, y salida asistida.

## Aforo

En Terminal de Acceso, abre Configurar aforo de personas. Cero desactiva el límite; se admite un máximo entre 1 y 500. Se entrega desactivado porque el equipo aún no ha acordado un aforo real. No se copió el límite de tres personas del ejemplo.

El límite cuenta personas únicas presentes, incluidos visitantes, y se comprueba en la misma transacción que registra el movimiento. Una persona presente en varias zonas se cuenta una vez. Alcanzar el aforo deniega nuevas entradas sin aumentar los fallos de contraseña ni bloquear la cuenta. Registrar una salida no se impide por aforo lleno. Los permisos, vigencia y licencias siguen comprobándose; una salida asistida autorizada puede resolver una presencia que ya no puede cerrarse con la credencial.

El número de tarjetas y el cupo de licencias de bóveda son controles distintos del aforo; se conservan en un apartado separado.

## Decisiones que se conservaron del sistema actual

La presencia y la bitácora siguen en SQLite y se reconstruyen de eventos verificados. No se añadió el botón del ejemplo que borra estados: las salidas asistidas quedan registradas. Tampoco se importaron horarios ficticios, accesos universales del DPO, alias de tarjetas de ejemplo ni un bloqueo RFID de cinco minutos que pudiera confundirse con el bloqueo de autenticación. Esas políticas necesitan una definición específica del equipo antes de activarlas.

El ejemplo permite remitir eventos por HTTP o syslog sin confirmación. Se conserva nuestro mecanismo de auditoría HTTPS firmado, con cola y confirmación, cuyo receptor independiente sigue pendiente de configuración. La exportación manual CSV no sustituye ese receptor.

Se conservan usuarios, roles, contraseñas, autenticadores, recuperación, tarjetas, zonas, licencias, eventos y configuración CCTV. Esto sigue siendo un registro académico de decisiones; no controla una cerradura física ni detecta una salida si nadie registra el movimiento.

## Validación

Las pruebas nuevas comprueban correspondencia de áreas, permisos por operador, validación del aforo, entradas simultáneas para el último lugar, salida con aforo lleno y ausencia de bloqueo de cuenta por capacidad. Las pruebas de Chrome cubren F1–F4, foco y limpieza del lector, RFID con ceros iniciales, entrada/salida, CSV y diseño móvil. Un lector físico conectado y las tarjetas del equipo requieren una prueba presencial; la prueba automatizada emula su escritura de teclado.
