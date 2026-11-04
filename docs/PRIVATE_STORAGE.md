# Almacén privado de Next

Implementación local nueva, 4 de noviembre de 2026. No se ha recuperado el ZIP de la iteración externa; este documento describe exclusivamente el código de esta copia.

El valor predeterminado es `%LOCALAPPDATA%\SecurityTeam\IdentityConsoleNext`. `ST_DATA_DIR` permite una carpeta absoluta dedicada fuera del repositorio. Servidor, SQLite, claves MFA/QR, configuración de publicación, supervisor y lanzadores PowerShell comparten el resolutor Python. No se acepta una ruta interna, una ruta relativa, la raíz de un disco, un directorio que contenga el repositorio ni una ruta con enlaces/junctions. El resolutor no crea archivos. La protección DPAPI y la DACL del almacén siguen siendo necesarias.

Si el antiguo `data/` del proyecto contiene algo, el inicio se detiene incluso si se ha indicado una ubicación externa. Así se evita iniciar por equivocación una base vacía y aparentar que desaparecieron las cuentas. No hay traslado automático ni regeneración de claves para ocultar errores. Los ensayos usan carpetas temporales externas al proyecto.

Una carpeta externa poblada también se rechaza antes de cambiar sus permisos o abrir SQLite, salvo que contenga el marcador válido `.identity-console-store.json`. El marcador identifica esta aplicación y su formato; no contiene secretos. Se crea al preparar una carpeta nueva y privada. Una carpeta con únicamente el archivo regular `.server.lock` del arranque inicial se considera nueva. Configuración, supervisor y publicadores pasan por la misma guardia antes de cambiar DACL.

No se adopta automáticamente una instalación antigua sin marcador. Debe respaldarse y revisarse su migración expresamente; no añadas el marcador a una carpeta de uso general para evitar la comprobación. Un marcador es una protección frente a una selección accidental, no una prueba criptográfica de propiedad frente a alguien con control de la cuenta Windows.

## Arranque limpio aislado

1. Instala dependencias con `INSTALAR.cmd` o crea `.venv` e instala `requirements.lock.txt`.
2. Abre PowerShell en esta copia. Para una demostración aislada define `$env:ST_DATA_DIR='C:\una-carpeta-privada-nueva\IdentityConsoleNext'` con una ruta propia, absoluta y externa. No utilices el almacén de la aplicación activa.
3. Ejecuta `.\.venv\Scripts\python.exe bootstrap_admin.py`. Crea únicamente el primer administrador de una base vacía; entrega una contraseña individual una sola vez.
4. Ejecuta `.\.venv\Scripts\python.exe server.py --port 8876` y abre `http://127.0.0.1:8876`. No uses 8765 mientras la aplicación original siga funcionando.
5. El resto del acceso conserva contraseña privada, MFA, recuperación y aceptación de políticas. No se publicará por Internet durante la revisión de Next.

## Traslado futuro de datos reales

Este trabajo **no ha migrado datos reales**. Antes de hacerlo deben identificarse la instalación activa, el mismo usuario Windows y los procesos propios; detenerlos mediante el procedimiento del proyecto; realizar una copia externa con DACL privada y SQLite consistente; conservar juntos DB, claves DPAPI, configuración y recibos que sean necesarios; verificar integridad y que las claves existentes descifran los factores; y ensayar la restauración aislada.

DPAPI CurrentUser puede impedir descifrar con otro usuario/equipo. Un arranque exitoso no demuestra una migración correcta. Hace falta comparar cuentas, factores, roles, zonas, licencias, registros y resultados de acceso sin imprimir sus valores privados. No deben copiarse bases de producción al repositorio, Base44 o una herramienta de diseño.

El cambio de carpeta no es una rotación ni elimina secretos publicados anteriormente. Si se confirma una exposición, se necesita contenerla y acordar rotación/limpieza sin reescribir el historial ni interrumpir servicios por sorpresa.

## Reversión

La aplicación original y su carpeta siguen independientes. Detén solo el servidor de prueba de Next y vuelve a utilizar la instalación anterior. No copies una base nueva vacía encima de una existente. Los commits de Next permiten revisar o revertir código; los respaldos de datos y claves se restauran como conjunto, con servidor detenido y comprobación posterior.
