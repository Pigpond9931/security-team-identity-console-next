# Correcciones de SECURITY TEAM Studio 1.1.0

Aplicadas a la versión React + Python para Windows, puerto 8765. Las copias originales de Ubuntu/Streamlit no se modificaron. La contraseña inicial de las cuentas de demostración se conserva por instrucción expresa del propietario; tampoco se cambiaron automáticamente las contraseñas de la base existente.

| Hallazgo original | Estado en Studio | Control |
| --- | --- | --- |
| H01 · Contraseña inicial pública | Excluido por petición | Se conserva la demo; para compartir se exige configurar primero el DPO y se añade OAuth con correos permitidos. El riesgo de la contraseña compartida sigue existiendo para cuentas iniciales sin configurar. |
| H02 · Sesiones y retos no revocados | Corregido en los flujos implementados | Versión de seguridad, revalidación transaccional, caducidad, cookies opacas y revocación. Lecturas de panel y autorización comparten instantánea SQLite. |
| H03 · Sobrescritura de enrolamiento | Corregido | Alta de factor, consumo de OTP y versión dentro de una misma transacción. |
| H04 · Intentos MFA ilimitados | Corregido | Contador compartido para verificación y recuperación, bloqueo tras tres fallos y límite adicional de solicitudes. |
| H05 · Fallos concurrentes perdidos | Corregido | Incremento SQL relativo, transacción de escritura y revalidación del estado vigente. |
| H06 · Escrituras sin autorización | Corregido en la API | CRUD antiguo y reset de base retirados del módulo operativo; mutaciones en security.py con sesión vigente y permisos por rol/área. |
| H07 · Secretos en panel y custodia local | Corregido para el administrador de la aplicación y otros usuarios ordinarios de Windows | Proyección pública, cifrado Fernet, clave envuelta por DPAPI CurrentUser, DACL privada, rotación y respaldo conjunto. El operador del proceso sigue siendo confiable. |
| H08 · Reutilización de OTP | Corregido | Se consume el paso TOTP dentro de la transacción, incluido el primer código de enrolamiento. |
| H09 · Mensajes de bloqueo reveladores | Corregido en las respuestas | Mensaje genérico y bcrypt para la verificación; no se promete igualdad absoluta de tiempos. |
| H10 · Contraseñas truncadas | Corregido | Rechazo explícito de más de 72 bytes UTF-8. |
| H11 · Accesos antes de MFA | Corregido | El contador consulta AUTH_SUCCESS, emitido después de completar MFA. |
| H12 · Baja conserva factor y RFID | Corregido | Baja transaccional revoca factor, RFID y sesiones; la reactivación requiere prueba privada del titular antes de un nuevo factor. |
| H13 · Seed recrea cuentas renombradas | Corregido | Marcador persistente, base existente preservada y carga inicial atómica. |
| H14 · REPLACE altera auditoría | Corregido para SQL ordinario; copia externa pendiente de servicio | Triggers contra UPDATE, DELETE y REPLACE; cola transaccional y cliente HTTPS firmado preparados. No hay receptor externo configurado ni garantía frente al operador que controla los archivos. |

## Refuerzos de esta actualización

En 1.2.0 se separó Administrador del sistema del DPO. Ambos consultan todas las áreas, pero el DPO no controla cuentas del administrador del sistema ni puede asignar ese rol. Las sesiones se revocan al cambiar permisos. Detalles en `ADMINISTRACION.md`.

El administrador puede solicitar una renovación de MFA, pero el titular debe presentar su factor vigente o un código privado. Restablecer contraseña y solicitar MFA no permite al administrador registrar su propio factor sobre una identidad ya enrolada. La baja y reactivación tampoco permiten omitir esa prueba.

Se entregan ocho códigos aleatorios privados, almacenados solo como hashes, después de verificar MFA. Son de un uso; regenerarlos exige contraseña y un OTP nuevo, revoca los códigos anteriores y las sesiones previas. La recuperación con código no inicia una sesión por sí sola: exige registrar y verificar el nuevo autenticador.

Se añadieron mantenimiento offline del operador, bloqueo del almacén mientras el servidor está en uso, respaldo consistente con clave protegida y recuperación asistida con confirmación interactiva y auditoría. Perder una clave no genera automáticamente una sustituta incompatible.

## Evidencia

- `tests/resultados-backend.txt`: pruebas con SQLite y criptografía reales, incluida lectura de la DACL de Windows, rotación, pérdida de clave, concurrencia, recuperación, separación de roles, permisos y HTTP.
- `tests/resultado-navegador.json`: acceso, códigos privados, alta, edición, RFID, bloqueo, auditoría, logout y recuperación completa con Chrome y API real en una base temporal.
- `tests/resultado-admin-sistema.json`: el mismo recorrido con el rol Administrador del sistema y comprobación de etiquetas y opciones de asignación.
- Pruebas de entrega externa: firma, confirmación y reintento con receptor simulado. Aún no hay prueba con un receptor independiente real.
- Pruebas de ngrok: agente oficial firmado, validación de política local, rechazo de listas vacías y prueba HTTP de dominio/origen exactos y cookie Secure. El túnel real fue configurado después de esta revisión; su configuración y límites de verificación constan en `ENLACE_COMPARTIDO.md`.

Los resultados verifican los casos ejecutados y no equivalen a una certificación exhaustiva de seguridad ni hacen segura una contraseña inicial compartida. La separación de auditoría frente al operador requiere el receptor independiente y su política de retención; ngrok no sustituye ese servicio.
