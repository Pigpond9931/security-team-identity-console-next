# Administrador del sistema y DPO

Actualización 1.5.2: primer ingreso con contraseña temporal individual, sin entregar QR ni enlace. Consulta [PRIMER_INGRESO_INDIVIDUAL.md](PRIMER_INGRESO_INDIVIDUAL.md). Los procedimientos antiguos de activación se conservan solo como historial.

La versión 1.2.0 incorpora el rol `system_admin`, visible como **Administrador del sistema**, separado del rol **DPO**.

| Rol | Alcance |
| --- | --- |
| Administrador del sistema | Todas las áreas, directorio, actividad y gestión de cuentas. Puede administrar al DPO y asignar otros administradores del sistema. |
| DPO | Gestión global de identidades y consulta de actividad. No puede modificar, bloquear, restablecer credenciales ni solicitar renovación de MFA de un administrador del sistema; tampoco puede asignar ese rol. |
| Administrador de área | Usuarios ordinarios de su área. No puede asignar roles ni ampliar su alcance. |
| Usuario | Su propia cuenta; monitoreo limitado si tiene el permiso Guard. |

Ambos roles globales carecen de área. El servidor verifica los permisos en cada operación y revoca las sesiones cuando cambia el rol. Las funciones administrativas no muestran contraseñas, secretos MFA ni códigos privados de recuperación. Se conserva una cuenta activa y desbloqueada de cada rol global existente; los administradores no pueden modificar sus propios permisos desde el directorio.

## Mantenimiento desde Windows

El código, el proceso Python, ngrok y las copias de seguridad se mantienen desde Windows. El rol dentro de la aplicación permite administrar sus datos y permisos; no ejecuta código ni comandos del sistema desde el navegador.

Con el servidor detenido, el operador local puede asignar el rol a una cuenta existente:

```powershell
.\.venv\Scripts\python.exe maintenance.py assign-system-admin MATRICULA
```

El comando conserva la contraseña, autenticador, RFID y códigos de recuperación. Registra el cambio y exige volver a iniciar sesión. Si la cuenta era el único DPO activo y desbloqueado, rechaza el cambio. Se recomienda efectuar primero un respaldo con `maintenance.py backup RUTA_NUEVA`.

La autorización de Google para ngrok y el rol dentro de SECURITY TEAM son controles independientes. Cambiar el rol no modifica la lista de correos autorizados ni el dominio.

## Verificación

Las pruebas de backend comprueban alcance global, separación del DPO, rechazo de escaladas, preservación de roles ante cambios concurrentes y asignación local sin sustituir credenciales. Las pruebas de Chrome usan bases temporales y verifican login, MFA, CRUD, auditoría y recuperación tanto con DPO como con Administrador del sistema. La imagen `design/08-admin-sistema.png` usa identidades ficticias.
