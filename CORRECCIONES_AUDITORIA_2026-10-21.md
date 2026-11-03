# Correcciones de auditoría · SECURITY TEAM 1.4.0

Se corrigieron los hallazgos confirmados del informe del 20 de octubre, conservando cuentas, roles, contraseñas, autenticadores, recuperación, licencias y configuración de cámaras. La revisión anterior permanece como evidencia histórica en `REVISION_AUDITORIA_2026-10-20.md`.

## Controles aplicados

| Referencia | Implementación y alcance |
| --- | --- |
| A1 · Proxy de cámaras | Además de IPv4 privada literal, puertos limitados, ausencia de redirecciones y límites de lectura, se exige aprobar la URL exacta (esquema, IP, puerto y ruta). El operador CCTV solicita; un administrador global aprueba o revoca. Una ruta o IP distinta requiere nueva aprobación. Las direcciones ya configuradas se conservan como destinos aprobados durante la migración. |
| A2 · Autorización | Se conservaron y probaron las validaciones del servidor por rol, titular y área. Una cuenta ordinaria no obtiene QR ajenos ni administra usuarios. El permiso CCTV no concede administración de identidades. El IDOR propuesto no se había reproducido. |
| A3 · MFA | Se conserva el bloqueo atómico por cuenta tras tres fallos, incluso entre retos y sesiones distintas, y la revocación por versión de seguridad. Los ocho códigos de recuperación privados siguen siendo de un uso. No se sustituyó ningún autenticador. |
| M1 y M2 · Entradas | Login comprueba tipos y tamaños; JSON inválido recibe un error genérico 400. Las entradas malformadas probadas no producen 500 ni revelan el parser. |
| M3 y M4 · Transporte | HSTS de un año en respuestas públicas HTTPS, incluidos HTML, recursos y errores; redirección 308 de HTTP a HTTPS mediante el conector local configurado. HTTP en loopback sigue disponible para operación local. |
| M5 · Metadatos | La sesión anónima solo expone etapa, CSRF y usuario nulo. Roles y áreas se entregan tras autenticación. |
| M6 · Navegador | CSP sin `unsafe-inline`, `object-src 'none'`, protección contra marcos y actualización de recursos HTTP en el origen público. Permissions-Policy permite cámara del mismo origen y deshabilita micrófono, geolocalización, USB Web API y pagos. El lector RFID que actúa como teclado sigue funcionando. |
| M7 · Entregas móviles | Enlaces de cinco minutos y un canje, sin credencial en la previsualización. El usuario debe autenticar su propia cuenta; el invitado compara un código con su anfitrión, quien autoriza el dispositivo. Después se habilitan los términos y el QR. La sesión del pase dura quince minutos y queda ligada al navegador mediante cookie HttpOnly y a la sesión del servidor. |
| M8 · Vinculación móvil | Escáner y cámara usan cookies HttpOnly separadas por propósito y ruta, Secure en el enlace HTTPS. El token no se devuelve a JavaScript ni se guarda en sessionStorage. Se mantienen confirmación en la laptop, CSRF, revocación y dependencia de los permisos vigentes del operador. |
| L14 · Cabeceras | Se centralizaron las políticas y se evita duplicar X-Robots-Tag en el servidor de origen. Quick Tunnel añade sus propias cabeceras X-Robots-Tag repetidas en el borde; esa duplicación externa permanece y no relaja la política local de no indexar. No se publican mapas de fuentes, archivos de datos ni claves. |

La contraseña inicial se conserva por indicación del propietario. Para evitar que conocerla permita apropiarse de una cuenta sin inscribir, ahora el primer registro exige también una activación privada de cinco minutos emitida por un administrador global tras verificar al titular. Las cuentas que ya tienen autenticador conservan su acceso habitual.

El límite de autenticación distingue cuenta, sesión, cliente y presupuesto global. Solo se acepta CF-Connecting-IP del conector Cloudflare configurado que llega por loopback al host público autorizado. Las cabeceras de clientes directos no cambian su identidad de red. Las sesiones y los presupuestos tienen límites de memoria. Esto no sustituye un servicio dedicado contra denegación de servicio ni constituye una prueba de carga para producción.

## Uso de los cambios

1. **Primer ingreso:** entra como administrador global, abre Personas y permisos, edita al titular y genera su activación privada en Acceso. Entrega el enlace o muestra su QR solo a esa persona. Ella lo abre en su navegador, inicia sesión y registra contraseña privada y autenticador. También puede pegar el enlace en el campo de activación que aparece después de la contraseña inicial. No compartas activaciones en el grupo.
2. **Usuario ya inscrito:** matrícula, contraseña privada y autenticador, como antes. Mi QR muestra directamente su credencial.
3. **Invitado:** crea la visita, entrega su enlace privado, compara presencialmente el código del teléfono y pulsa Confirmar teléfono del invitado. Después el invitado acepta los términos. Usa Renovar entrega si caduca; no hace falta recrear la visita. Preparar otra entrega invalida los enlaces anteriores pendientes de ese titular.
4. **Cámara IP:** solicita su URL exacta en Destinos de cámaras IP aprobados; un administrador global la aprueba antes de probar o guardar el canal. Un administrador CCTV no puede aprobar nuevos destinos por sí mismo. La cámara del navegador mantiene su emparejamiento por QR.
5. **Compartir:** COMPARTIR_CLOUDFLARE.cmd inicia servidor y supervisor. ABRIR_CLOUDFLARE.cmd abre la dirección registrada. DETENER_CLOUDFLARE.cmd detiene el túnel y cancela la recuperación automática. El supervisor comprueba salud local y pública, reintenta con espera progresiva y no sustituye disponibilidad de energía o Internet. No se instaló inicio automático de Windows.
6. **Recuperación local excepcional:** el operador Windows puede usar `maintenance.py recover-account MATRICULA` en una terminal interactiva con el servicio detenido, tras verificar identidad. Entrega credencial temporal y activación nuevas. `activate-account MATRICULA` emite únicamente una activación para una cuenta aún sin inscribir; no elimina factores existentes.

La actualización retira los enlaces de entrega antiguos reutilizables. Los QR ya descargados conservan su vigencia original, pues las claves y las versiones de seguridad se preservan. Se requiere volver a iniciar sesión y vincular teléfonos después del reinicio del servidor.

## Privacidad y pendientes externos

El aviso se puede leer antes de iniciar sesión y desde los términos. Identifica datos de identidad, permisos, visitantes y movimientos almacenados en SQLite en la laptop. Explica que las cámaras transmiten imágenes, con cuadros temporales en memoria, sin grabación persistente, audio ni reconocimiento facial.

El propietario confirmó que **el plazo de conservación aún no está definido**. No se inventó una duración ni se borraron visitantes, eventos o auditorías. El responsable y el DPO deben acordar el plazo y el procedimiento antes de activar una eliminación automática. Las caducidades de sesiones, enlaces y credenciales son controles de acceso; no son una política de conservación de registros.

El propietario confirmó que **no tiene dominio propio**. El enlace Cloudflare sigue siendo temporal y puede cambiar al recuperar el túnel. La aplicación no ofrece disponibilidad continua si la laptop está apagada, suspendida o desconectada. Un dominio fijo o alojamiento estable sigue pendiente de una decisión posterior.

El aviso «Peligrosa» de Chrome no se declara solucionado: endurecer la aplicación no elimina por sí solo una clasificación de Safe Browsing. No se desactivó la protección del navegador. Consulta `AVISO_CHROME.md` para el estado y el procedimiento de revisión.

La copia de auditoría fuera de la laptop requiere configurar un receptor independiente. El transporte Cloudflare no constituye ese receptor. Los controles locales y la cola de entrega existentes no ofrecen protección frente a un operador que controle íntegramente Windows y sus archivos.

## Evidencia

`tests/resultado-hardening-python.json` reúne 88 pruebas Python aprobadas sobre bases temporales. `tests/resultado-admin-sistema.json` documenta Chrome con API real temporal, incluidos escáner, recuperación, cámara WebRTC simulada, alternativa HTTPS, pases y avisos de acceso. `tests/resultado-hardening-despliegue.json` y `tests/resultado-hardening-publico.json` registran preservación y comprobación del servicio publicado cuando termina el despliegue. `tests/resultado-recuperacion-tunel.json` registra una recuperación real del proceso hijo y el cambio de URL. La revisión visual comprobó doce combinaciones de color con contraste superior a 4.5:1, tema oscuro del sistema y diseño móvil. Las cámaras físicas, la carga sostenida y una revisión externa autenticada siguen fuera de estas pruebas.
