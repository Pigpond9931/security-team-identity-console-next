# Registro grupal con contraseña común temporal (1.5.4)

Administración global puede abrir Personas y permisos → Primer ingreso grupal, confirmar el registro supervisado y generar una misma contraseña para las cuentas pendientes elegibles. Se muestra una vez y vence en 24 horas. Generar otra sustituye la temporal de quienes sigan pendientes.

Cada titular usa su matrícula, crea una contraseña personal distinta, registra su autenticador, guarda sus códigos de recuperación y acepta los términos. La temporal se consume por separado en cada cuenta. Si cancela o vence la configuración de cinco minutos, el administrador puede emitir una temporal individual o generar otro grupo para los pendientes.

Se omiten cuentas configuradas, inactivas, bloqueadas, administradores, Guard y titulares de permisos privilegiados de cámaras/servidores/centro de datos. Esas identidades requieren contraseña individual. Conceder una licencia privilegiada a una cuenta con alta grupal pendiente exige emitir primero una temporal individual.

La clave común facilita el registro, pero cualquiera que conozca esa clave y una matrícula habilitada podría intentar registrar esa cuenta. Usarla durante la sesión supervisada del grupo reduce esa exposición; no es una contraseña compartida permanente ni debe publicarse en GitHub.

## Desbloquear una cuenta

Personas y permisos → Bloqueadas → abrir la persona → Desbloquear cuenta → Confirmar cambio. El botón también está en la pestaña Seguridad del perfil. Se reinician los intentos fallidos y se conserva la contraseña, MFA y RFID. Se revocan las sesiones anteriores y se registra la operación en auditoría. Los administradores de área solo pueden actuar sobre usuarios de su área; DPO no administra cuentas system_admin. Desbloquear no activa una cuenta desactivada ni genera una contraseña nueva.
