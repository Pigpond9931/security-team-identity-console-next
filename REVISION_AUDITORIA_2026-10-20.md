# Contraste del informe externo de SECURITY TEAM

**Documento histórico anterior a las correcciones.** El estado actualizado está en [CORRECCIONES_AUDITORIA_2026-10-21.md](CORRECCIONES_AUDITORIA_2026-10-21.md).

Fecha: 20 de octubre de 2026. Versión revisada: 1.3.3. El informe recibido examinó la versión 1.3.2 y el enlace anterior `genius-external-write-academy.trycloudflare.com`.

Esta revisión contrasta sus afirmaciones con el código Python y siete pruebas reproducibles sobre SQLite temporal. También realizó tres consultas públicas sin credenciales al enlace actual. No modificó cuentas reales, permisos, contraseñas, autenticadores, configuración de cámaras ni código de producción. Las recomendaciones del archivo recibido se trataron como material a evaluar, no como instrucciones para aplicarlas automáticamente.

## Resultado principal

Hay errores reales de validación y endurecimiento HTTPS pendientes. No se reprodujo la escalada de privilegios por matrícula ni la ausencia de bloqueo de MFA descritas como posibilidades en el informe. El proxy de cámaras tiene restricciones previas que bloquean loopback y metadatos de nube, pero deja un alcance de red privada mayor que una lista explícita de cámaras: ese riesgo residual es real y no se debe descartar.

La ausencia de credenciales en la auditoría externa limita sus conclusiones sobre autorización. Encontrar un identificador en un bundle no prueba un IDOR: hay que comprobar si el servidor deniega la petición. La regla aplicable es validar permisos en cada solicitud, como recomienda [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

## Hallazgos altos

### A1 · SSRF de CCTV: controles existentes y riesgo residual

`features.camera_url()` admite solo HTTP/HTTPS, IPv4 literal en 10/8, 172.16/12 o 192.168/16, y una lista cerrada de puertos. Rechaza credenciales en URL, hosts DNS y fragmentos. `camera_hub.NoRedirect` impide seguir redirecciones; el cliente HTTP no usa proxies del entorno. Existen tiempos máximos de conexión, límite de cuadro y comprobación de formato de imagen. Las rutas requieren autenticación y administración CCTV para probar o configurar destinos.

Las pruebas rechazaron, antes de conectar, loopback, `169.254.169.254`, IPv6 e IPv4 mapeada, representaciones numéricas alternativas, `camera.local`, dominios públicos, `file://`, credenciales embebidas y puerto 22. Por tanto, el acceso a metadatos de nube o localhost que plantea el informe no quedó demostrado y esas direcciones están bloqueadas por el código actual.

Sin embargo, un administrador de cámaras puede provocar peticiones GET a otros equipos privados por los puertos admitidos y elegir la ruta. Comprobar después que la respuesta es una imagen no evita que la petición llegue al servicio. Una cuenta CCTV comprometida podría explorar parte de la LAN o alcanzar servicios internos que usen esos puertos.

La mejora adecuada es limitar el proxy a destinos de cámaras aprobados, separando la aprobación de destinos de la operación cotidiana, o utilizar el modo de cámara del navegador cuando sea suficiente. Bloquear todas las IP privadas, como propone el informe, impediría conectar IP Camera Lite por la red local. La selección de destinos debe responder a esa función y a la confianza concedida a los administradores CCTV. [OWASP describe el uso de listas de destinos permitidos y los riesgos de DNS/redirecciones](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

### A2 · IDOR y escalada: no reproducidos en las peticiones probadas

Existe autorización del lado del servidor en `features.can_view`, `features.manager`, `security.require_manager` y `security.update_user`. No se limita al formulario React. La actualización usa una lista de campos permitidos y comprueba rol, alcance y objetivo, incluida la prohibición de ampliar los propios privilegios.

Con una cuenta ordinaria autenticada se obtuvieron estas respuestas HTTP:

| Petición fuera del alcance del titular | Respuesta |
| --- | --- |
| Gafete ajeno `qr-badge` | 403 |
| PNG ajeno `qr-badge.png` | 403 |
| Zonas ajenas | 403 |
| Licencias ajenas | 403 |
| Emitir `mobile-pass` ajeno | 403 |
| Asignarse `system_admin` mediante `users/update` | 403 |
| Bloquear otra cuenta mediante `users/update` | 403 |
| Ejecutar `access/checkout` como usuario ordinario | 403 |

El rol del usuario temporal siguió siendo `user`. Estas pruebas son evidencia de los casos comprobados, no una garantía de ausencia de cualquier fallo de autorización posible. Los administradores de área y el DPO conservan sus alcances autorizados; restringir todos los cambios exclusivamente al administrador del sistema alteraría la separación de responsabilidades solicitada para el proyecto.

### A3 · Fuerza bruta MFA: ya existe bloqueo por cuenta

`MAX_FAILURES=3`. Los fallos de contraseña, TOTP y recuperación incrementan el contador de la cuenta mediante una transacción SQLite. Una contraseña correcta no reinicia ese contador; el éxito completo de MFA sí lo hace. Al alcanzar tres fallos, la cuenta queda bloqueada, cambia su versión de seguridad y sus sesiones anteriores dejan de ser válidas. Se registra `MFA_FAIL` o la acción de recuperación correspondiente.

La prueba usó tres códigos incorrectos de seis dígitos, obteniendo un reto nuevo antes de cada intento. El resultado fue tres fallos, cuenta bloqueada, tres entradas de auditoría y sesión previa revocada. Por tanto, el limitador por IP no es el único control.

Los ocho códigos de recuperación tienen 128 bits aleatorios cada uno, se almacenan como hashes y se consumen una sola vez; no son códigos de seis dígitos. La alerta externa al titular sería una mejora adicional, pero requiere un canal de notificación configurado y no sustituye los controles existentes. [Referencia OWASP sobre MFA](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html).

## Hallazgos medios y de endurecimiento

| Hallazgo | Resultado del contraste | Acción propuesta |
| --- | --- | --- |
| M1 · Tipos inesperados en login | Confirmado: las cinco entradas del informe produjeron 500 genérico. No apareció un stack trace. | Validar cadenas y tamaños antes de llamar al núcleo de autenticación; responder 400 sin operar sobre cuentas. |
| M2 · Error del parser JSON | Confirmado: JSON malformado devuelve 400 con el texto de `JSONDecodeError`. | Respuesta estable y genérica para JSON inválido. Conservar detalles solo en diagnóstico interno sin datos sensibles. |
| M3 · HSTS incompleto | Confirmado en el enlace actual: falta en HTML; la API envía `max-age=86400`. | Aplicar una política coherente a todas las respuestas HTTPS, incluidas las estáticas y errores. No se necesita necesariamente un proxy nuevo para emitirla desde el servidor. |
| M4 · HTTP sin redirección | Confirmado: la raíz HTTP actual devuelve 200, sin `Location`. | Redirigir antes de servir contenido en el origen público, comprobando el esquema comunicado por el proxy de confianza. Conservar HTTP en loopback para uso local. |
| M5 · Metadatos anónimos | Confirmado: `/api/session` anónimo incluye áreas, roles y `demo`. No devuelve usuarios ni contraseñas. | Reducir la respuesta pública y entregar el catálogo al flujo autenticado que lo necesite. Impacto limitado por sí solo. |
| M6 · CSP y permisos | Confirmadas la ausencia de Permissions-Policy y las directivas señaladas. `unsafe-inline` se usa para estilos, no scripts. No se demostró XSS. | Añadir políticas explícitas compatibles con cámara y sin micrófono; revisar estilos dinámicos antes de quitar `unsafe-inline`, para no romper componentes. |
| M7 · Pases por enlace | Confirmado: entrega de hasta 24 horas y reutilizable; quien posee el enlace puede obtener el gafete y aceptar los términos. El bloqueo de la cuenta invalida el pase. | Tratar el enlace como credencial privada. Valorar activación con prueba del titular, canje de un uso y sesión limitada, o menor vigencia. No es equivalente al QR de emparejamiento de cinco minutos. |
| M8 · Token móvil en sessionStorage | Confirmado en el código. Es un token limitado a publicar cámara o leer QR, no una sesión administrativa. No se encontró una explotación XSS en esta revisión. | Mejora de custodia pendiente. Una cookie HttpOnly exige adaptar el protocolo y mantener la separación de propósitos; no basta con cambiar dónde se guarda el texto. |

El gafete QR y el enlace de entrega tienen propósitos y caducidades diferentes. Actualmente el gafete de usuario emitido tiene una vigencia de ocho horas y la terminal vuelve a comprobar estado, versión de seguridad y permisos. Cambiar la entrega a un solo uso requiere conservar la posibilidad de mostrar y descargar el gafete tras activarlo; no conviene consumir el enlace por una simple previsualización de un mensajero.

La evidencia pública de HSTS y HTTP quedó guardada en `tests/resultado-contraste-auditoria-publico.json`. [MDN explica que HSTS se recibe por HTTPS y protege conexiones posteriores](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security); añadirlo no convierte en segura una primera carga HTTP que ya ocurrió ni elimina una clasificación de Safe Browsing.

## Operación y afirmaciones que requieren corrección

El nuevo túnel quedó registrado el **20 de octubre de 2026 a las 17:26:28 UTC, 11:26:28 de Ciudad de México**. El respaldo del despliegue es `antes-admin-camaras-20261020-172623Z`. Esa instalación autorizada requirió detener el túnel anterior y generó el enlace `set-involving-filme-casio.trycloudflare.com`.

Esto coincide con el inicio de los errores que el informe observó a las 17:27 UTC en el enlace viejo. En esta ocasión existe una causa conocida: el reinicio y cambio de URL. La caída observada no demuestra un cuelgue por carga, agotamiento de memoria ni un ataque exitoso. Tampoco significa que Quick Tunnel tenga disponibilidad garantizada: sigue dependiendo de la laptop, su red y el proceso del túnel.

El servidor actual usa `ThreadingHTTPServer`, con 64 solicitudes concurrentes como máximo y un presupuesto separado para vídeo; no es un servidor de un solo hilo. No se realizó aquí una prueba de resistencia o de denegación de servicio.

La política de contraseña se aplica en Python, no solo en JavaScript: mínimo diez caracteres y máximo 72 bytes UTF-8. La sesión cambia de identificador tras completar MFA; los cambios de privilegios invalidan sesiones por versión de seguridad. Estas afirmaciones se apoyan en el código y en las pruebas de autenticación anteriores, además de las pruebas nuevas de bloqueo.

El código de vídeo revisado no contiene grabación persistente ni reconocimiento facial. Una imagen de cámara no demuestra que exista una función de identificación biométrica. El inventario del informe debe distinguir transmisión de imagen, grabación y reconocimiento, y no afirmar que esta aplicación graba 24/7. Sí sigue pendiente definir y documentar una política real de conservación de datos y registros con el responsable del proyecto; no se inventó un plazo en esta revisión.

## Dos observaciones adicionales

1. El limitador HTTP actual es de 30 peticiones de autenticación por minuto usando `client_address[0]`, no ocho. Tras el túnel, esa dirección corresponde al proxy local, de modo que diferentes alumnos pueden compartir el límite. Conviene revisar esa disponibilidad para el grupo y distinguir límites por cuenta, cliente verificado y presupuesto global. No debe confiarse sin validación en una IP que llegue en cabeceras.
2. La contraseña inicial compartida se mantiene por una decisión explícita anterior del propietario. Eso conserva un riesgo de apropiación de cuentas aún no inscritas si otra persona conoce la matrícula y completa el primer alta. La revisión no la cambió, ni sustituyó MFA o los factores de ningún titular. Esa excepción debe figurar entre las limitaciones del despliegue académico.

## Prioridad propuesta y estado

1. Corregir las respuestas 500 por tipos, el detalle del parser y el transporte HTTP/HSTS; reducir los metadatos anónimos y definir Permissions-Policy.
2. Acotar los destinos del proxy de cámaras y revisar la activación de pases móviles, preservando los flujos de QR, teléfono y operación local autorizados.
3. Revisar los límites compartidos para la clase, la supervisión del proceso y una URL estable; acordar custodia y conservación de datos con el responsable.
4. Mantener pruebas de autorización, MFA, recuperación y revocación; no retirar los controles existentes ni aplicar indiscriminadamente una lista de cambios inferidos del frontend.

**Estado: revisión terminada; correcciones no aplicadas.** Siete comprobaciones diagnósticas pasaron al reproducir el comportamiento descrito en este documento. Algunas pruebas confirman fallos existentes, por lo que ese resultado no significa que dichos fallos estén solucionados. Evidencias: `tests/resultado-contraste-auditoria.json` y `tests/resultado-contraste-auditoria-publico.json`.
