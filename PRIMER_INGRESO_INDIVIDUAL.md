# Primer ingreso con contraseña individual

## Administración

1. Abre **Personas y permisos** y selecciona a la persona que aún no ha configurado su cuenta.
2. En **Perfil y permisos**, busca **Primer ingreso sin enlace ni QR**.
3. Verifica al titular y pulsa **Generar contraseña temporal individual**.
4. Entrega únicamente a esa persona su matrícula y contraseña temporal por un canal privado.
5. Pulsa **Ocultar contraseña** o cierra el perfil. El valor no se puede consultar después.

La contraseña es distinta para cada emisión, se guarda como hash, vence en 24
horas y se consume al iniciar la configuración. Generar otra revoca la anterior.
La sesión de configuración dispone de cinco minutos para cambiar contraseña y
registrar MFA. Si se cancela o vence ese paso, genera otra contraseña temporal.

Los usuarios ya configurados conservan sus contraseñas y autenticadores. Esta
operación rechaza cuentas que ya registraron MFA; para ellas sigue disponible
**Restablecer contraseña**, conservando el segundo factor y la recuperación.

Crear un usuario devuelve una contraseña individual lista para el primer ingreso.
Restablecer la contraseña de una cuenta activa, desbloqueada y nunca inscrita
también habilita el primer ingreso; se aplica el alcance de permisos existente.
No se generaron ni distribuyeron contraseñas masivas durante esta actualización.

## Titular

1. Abre el enlace actual de SECURITY TEAM.
2. Introduce tu matrícula y la contraseña temporal individual recibida.
3. Crea una contraseña privada diferente de la temporal.
4. Configura tu autenticador y confirma el código actual.
5. Guarda tus códigos de recuperación y acepta los términos del proyecto.

Ya no necesitas recibir un enlace o QR de activación del administrador. El QR
del autenticador se muestra únicamente en tu propia pantalla durante el paso 4;
no es el QR que antes tenía que entregarte la administración. Los QR de acceso,
cámaras y escáneres conservan sus propósitos originales.

La contraseña inicial compartida anterior no permite inscribir una cuenta sin
autorización individual. Las activaciones privadas ya emitidas mantienen su
caducidad corta por compatibilidad, pero no se generan en el panel nuevo.

## Verificación

Las pruebas cubren primer ingreso HTTP completo sin enlace, caducidad, consumo
concurrente de un uso, reemisión, permisos administrativos, cuentas ya inscritas,
MFA, términos y ausencia de contraseñas en auditoría. La validación de Chrome
usa una base temporal, comprueba escritorio y móvil y oculta las contraseñas
antes de las capturas. La migración agrega una tabla de autorizaciones sin
restablecer usuarios, tarjetas, roles, licencias, factores ni códigos existentes.

## Alternativa de registro grupal

Desde 1.5.4 existe una emisión común temporal para cuentas pendientes sin privilegios, habilitada expresamente por administración global. Consulta PRIMER_INGRESO_GRUPAL.md; la contraseña individual sigue siendo obligatoria para identidades privilegiadas.
