# Aviso «Peligrosa» en Chrome

La captura del propietario muestra que Chrome considera engañoso el enlace `discuss-chicago-songs-protection.trycloudflare.com` y recomienda revisar las contraseñas. El mismo cuadro indica que el certificado es válido. Un certificado válido acredita el cifrado y el dominio de la conexión; no descarta phishing ni elimina las clasificaciones de Safe Browsing.

La revisión realizada comprobó:

- HTML, JavaScript y CSS publicados idénticos a los archivos de la instalación, mediante SHA-256.
- Conexión HTTPS validada normalmente, sin ignorar certificados.
- Respuestas 404 al intentar descargar la base de datos y la clave MFA.
- Respuesta 401 al pedir datos administrativos sin iniciar sesión.
- El frontend consulta la API del propio origen. No integra un formulario de contraseña de Google/Microsoft ni envía las credenciales del proyecto a esos servicios.

Estas comprobaciones no son un análisis completo del equipo, sus extensiones o todas sus dependencias. No permiten afirmar que el aviso sea un falso positivo ni determinar qué regla concreta activó Chrome. La página pública de diagnóstico de Google no devolvió un resultado utilizable en esta sesión. El motivo exacto y una eventual reclasificación siguen pendientes.

Se añadió una identificación explícita del proyecto académico y una indicación de usar una contraseña exclusiva de SECURITY TEAM. Eso aclara al usuario qué credenciales solicita el formulario; no garantiza que Google quite el aviso.

Conserva Safe Browsing activado. Si utilizaste la misma contraseña que en Google, Microsoft u otro servicio, cámbiala en los servicios afectados y establece una distinta para el proyecto. No compartas contraseñas ni códigos del autenticador para solicitar ayuda.

La vía oficial para pedir revisión, si se confirma una detección incorrecta, es el [formulario de Google Safe Browsing](https://safebrowsing.google.com/safebrowsing/report_error/?url=https%3A%2F%2Fdiscuss-chicago-songs-protection.trycloudflare.com%2F). No se envió ningún reporte automáticamente. Texto preparado para revisión humana:

> Soy el responsable de SECURITY TEAM, una aplicación académica de gestión de identidades y acceso. El sitio autentica exclusivamente cuentas creadas para el proyecto mediante matrícula, contraseña propia y TOTP; no solicita las contraseñas de Google, Microsoft ni de la universidad. Chrome muestra una advertencia de sitio engañoso en la URL indicada. Solicito revisar la clasificación. El sitio sirve recursos del mismo origen y conserva protegidas sus APIs y sus archivos de datos.

El reinicio necesario para instalar una actualización de la aplicación cambia el enlace temporal de Quick Tunnel. Ese cambio no se considera una solución del aviso ni prueba que la clasificación anterior fuese incorrecta. Conviene conservar este informe y el enlace denunciado para el seguimiento.

Fuentes oficiales: [avisos de sitios no seguros de Chrome](https://support.google.com/chrome/answer/99020), [clasificación de contenido engañoso y revisión](https://developers.google.com/search/docs/monitor-debug/security/social-engineering).
