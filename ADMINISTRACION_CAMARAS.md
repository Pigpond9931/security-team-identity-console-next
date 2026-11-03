# Administración de cámaras

El permiso interno **LIC-CCTV-ADMIN · Administración de cámaras** habilita la configuración CCTV sin convertir al titular en administrador global. Se gestiona desde el catálogo de permisos/licencias del directorio por un Administrador del sistema o el DPO. Los administradores de área y los propios titulares no pueden concederlo ni retirarlo.

Permite consultar CCTV, configurar nombres y direcciones de canales IP, probar conexiones con las mismas restricciones de red privada que antes, consultar las direcciones locales del servidor para configurar cámaras y crear/confirmar sus vínculos de cámara del navegador. Desde 1.5.1 también permite eliminar canales IP y de navegador de otras sesiones para liberar espacios. La aprobación de un emparejamiento sigue reservada a la sesión creadora. Consulta [Eliminar y sustituir cámaras](ELIMINAR_CAMARAS_2026-10-27.md).

No concede administración de usuarios, roles, contraseñas, autenticadores, cupos RFID ni permisos de acceso físico. Conserva el rol y el área de la cuenta; si existen otros permisos previos, estos no se retiran. En el encabezado y la barra lateral aparece **Administrador de cámaras** para identificar este permiso. La cuenta base puede seguir figurando como Usuario en su perfil.

Las comprobaciones se realizan en el servidor. El permiso de visualización **LIC-CCTV-MON** por sí solo no permite editar cámaras. Al retirar LIC-CCTV-ADMIN se rechazan las nuevas modificaciones y se revocan las cámaras del navegador cuyo propietario ya no tenga administración CCTV. Contraseña, MFA y términos siguen siendo obligatorios.

Asignación autorizada por el propietario:

| Persona | Matrícula |
| --- | --- |
| Persona de ejemplo de Monitoring | 9900014 |
| Persona de ejemplo de Monitoring | 9900017 |
| Persona de ejemplo de Monitoring | 9900012 |

La asignación no cambia sus contraseñas ni sus autenticadores. Los administradores globales existentes y el DPO conservan su rol. Al reiniciar el servidor para instalar este cambio termina la sesión activa y el enlace temporal de Quick Tunnel cambia; consulta ENLACE_CLOUDFLARE.md o ABRIR_CLOUDFLARE.cmd para abrir la dirección vigente.
