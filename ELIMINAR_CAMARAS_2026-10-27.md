# Eliminar y sustituir cámaras · versión 1.5.1

Entra con una cuenta que tenga administración de cámaras.

## Desde la configuración

1. Abre **Monitoreo CCTV → Configurar cámaras → Lista de cámaras**.
2. Localiza la cámara por su nombre, tipo y estado. La lista incluye canales IP y vínculos del navegador, incluso los pendientes de vincular.
3. Pulsa **Eliminar cámara**, revisa el nombre y confirma. **Cancelar** o Escape cierran el aviso sin eliminarla.
4. El canal desaparece y se libera su espacio. Puedes vincular otro teléfono/webcam o agregar un canal IP. La eliminación del canal IP se guarda de inmediato: no necesita pulsar **Guardar canales**.

La lista muestra el total ocupado y los espacios disponibles sobre ocho canales combinados. Una cámara sin señal puede estar temporalmente desconectada; el administrador elige qué quitar. La aplicación no elimina canales automáticamente por perder la señal.

## Desde Vigilancia

Selecciona una cámara y pulsa **Eliminar cámara** en la barra superior. El aviso identifica el canal antes de confirmar. Si la cámara estaba transmitiendo, su vista y sus espectadores se desconectan. El teléfono vinculado deja de publicar al recibir la revocación.

## Permisos y conservación

Administradores del sistema, DPO y titulares de `LIC-CCTV-ADMIN` pueden eliminar canales, incluidos los creados desde otra sesión. La confirmación del emparejamiento de un teléfono sigue reservada a la sesión creadora. Las cuentas que solo consultan CCTV no ven el botón y la API rechaza su solicitud de borrado.

La operación elimina el canal y su transmisión, libera el espacio y registra quién lo hizo en auditoría. No modifica identidades, licencias, MFA ni eventos de acceso. Para volver a usar una cámara de navegador se crea un vínculo nuevo. El destino IP aprobado se conserva para permitir configurar de nuevo esa dirección; las direcciones nuevas siguen necesitando aprobación global.

Si otra sesión modifica una cámara IP mientras está abierto el aviso, el servidor rechaza la confirmación desactualizada. Cierra el aviso, actualiza la lista y revisa el canal otra vez. Esto evita borrar otro dispositivo cuando cambian los identificadores al guardar una configuración.

Los canales nuevos sin guardar se descartan desde **Descartar canal** en su formulario. Aún no ocupan un espacio persistente. Los canales guardados se eliminan desde la lista o Vigilancia.

## Comprobación

Se verifican eliminación y sustitución, cupo combinado, permisos, auditoría, cierre del teléfono, parada de captura IP, protección de solicitudes, confirmaciones desactualizadas y diseño móvil. Las pruebas usan SQLite temporal, identidades ficticias y una cámara simulada. Los informes están en `tests/resultado-camera-removal-*.json`.

También se corrigió una carrera de señalización: un mensaje atrasado de un espectador que cerró su vista ya no se interpreta como revocación del teléfono emisor.

La instalación de esta versión requiere reiniciar el backend. Se conservan los canales IP guardados y los datos existentes. Las sesiones y cámaras temporales del navegador se vuelven a vincular después del reinicio; el enlace gratuito del túnel puede cambiar.
