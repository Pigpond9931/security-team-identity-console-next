# Compartir SECURITY TEAM con ngrok en Windows

El agente oficial está instalado en `tools/ngrok.exe`. Se verificó la firma Authenticode de **ngrok, Inc.**. El propietario creó su cuenta y autorizó la configuración y el túnel restringido a su correo. Consulta [ENLACE_COMPARTIDO.md](ENLACE_COMPARTIDO.md) para el enlace y estado de la instalación actual.

## Preparación de tu cuenta

1. [Crea tu cuenta de ngrok](https://dashboard.ngrok.com/signup) y completa la verificación que te solicite.
2. En tu panel, busca **Domains** y copia el dominio asignado. Usa su dirección completa `https://...`.
3. Abre [Your Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken). No envíes ese token por el chat ni lo pegues en el código.
4. Haz doble clic en **CONFIGURAR_NGROK.cmd**. Introduce el dominio, los correos de Google que podrán entrar (separados por comas) y el token cuando se solicite. El token no se muestra y se guarda protegido por DPAPI para tu usuario de Windows.

## Antes de compartir

Entra como DPO en la aplicación local, completa su configuración de contraseña y MFA y guarda sus códigos de recuperación. La contraseña inicial de la demo se conserva por petición del propietario. El asistente se niega a compartir mientras no exista un DPO activo con MFA y configuración inicial completada.

Después detén la instancia local con **DETENER.cmd** o con Ctrl+C en su consola. Ejecuta **COMPARTIR_NGROK.cmd**. Ese asistente inicia la aplicación y el túnel con la política de acceso. Mantén abierta la consola; Ctrl+C termina ambos procesos. Si se ejecuta en segundo plano, **DETENER_NGROK.cmd** cierra el agente registrado de esta aplicación y permite que el asistente termine su servidor.

Quienes reciban el enlace deberán pasar primero por Google usando uno de los correos autorizados; después entrarán con su matrícula, contraseña y MFA de SECURITY TEAM. El inicio con Google en el túnel no sustituye ni asigna roles en la aplicación.

Si ngrok rechaza el token, el dominio o la política OAuth, el asistente se detiene. No desactiva la autenticación como alternativa. La instalación actual confirmó el endpoint con política y la redirección pública a Google. La prueba interactiva completa con correo permitido, correo rechazado, login, MFA y cierre de sesión desde el enlace público sigue pendiente del acceso del propietario.

## Controles preparados

- Política OAuth de Google con lista explícita de correos; una lista vacía es rechazada.
- Solo se acepta el dominio HTTPS exacto configurado; no se habilitan comodines de ngrok ni CORS abierto.
- Cookies `HttpOnly`, `SameSite=Strict` y `Secure` para el dominio público; comprobación de origen y CSRF en las escrituras.
- La aplicación sigue escuchando solo en `127.0.0.1`; el acceso externo pasa por ngrok.
- Inspección de cuerpos de solicitudes desactivada en el agente para evitar almacenar contraseñas, QR o códigos MFA en su inspector.
- El token de ngrok se entrega al agente por su entorno; no se pasa como argumento ni se incorpora a la entrega de código.

## Auditoría y alcance

Ngrok proporciona el túnel y los controles de acceso de su servicio. No configura por sí mismo un archivo independiente y protegido de los eventos de identidad de esta aplicación. Se preparó una cola duradera para un receptor HTTPS externo; por ahora no existe receptor configurado y no se están enviando esos eventos fuera de la laptop.

El operador del equipo y del proceso sigue siendo una autoridad confiable: quien controla Windows puede modificar el programa, la base o el uso de sus claves. DPAPI, los permisos de archivo y los controles del panel no garantizan protección frente a ese operador. Usa la compartición como demostración restringida.

Referencias oficiales: [instalación de ngrok en Windows](https://ngrok.com/download/windows), [OAuth y restricciones por correo](https://github.com/ngrok/ngrok-docs/blob/main/getting-started/_secure-your-app.mdx), [configuración del agente](https://ngrok.com/docs/gateway/agent/config/v3).
