# Iteración local Next · 4 de noviembre de 2026

## Objetivo y procedencia

Preparar una evolución independiente, revisable y privada; conservar el original y el avance local reciente; mejorar seguridad, claridad y experiencia. El ZIP externo esperado no se encontró. El trabajo no se atribuye al commit externo ni reemplaza su recuperación. El bundle original fue verificado antes de modificar esta copia.

## Arquitectura conservada

| Capa | Responsabilidad |
|---|---|
| React en `frontend/` | Formularios, navegación, QR, terminal y cámara del navegador; nunca decide autorizaciones por sí sola. |
| `server.py` | HTTP del mismo origen, sesiones, CSRF, cookies y etapas de autenticación. |
| `security.py` | Contraseñas, MFA, recuperación, alcance administrativo, sesiones y transacciones. |
| `features.py` | Zonas, licencias, gafetes, invitados y decisiones de acceso según datos vigentes. |
| `runtime_paths.py` / `.ps1` | Ubicación externa única para servidor, custodia y lanzadores. |
| SQLite / DPAPI / DACL | Estado consistente, protección de claves vinculada al usuario Windows y permisos privados. |
| Cámaras | WebRTC para vídeo directo; JPEG reciente en RAM como alternativa. Sin archivo DVR. |

Next usa 8876/8877 para evitar interferir con el original en 8765. El destino de Git es la copia privada; `upstream` conserva el original y tiene push deshabilitado. No se alteran las ramas, datos ni procesos del original.

## Decisiones de producto

La interfaz conserva Manrope e incorpora grafito, papel cálido y cobre. Los estados de éxito, advertencia y denegación mantienen texto e iconos; no dependen solo del color. Los accesos del centro de operaciones corresponden a permisos reales del servidor. El catálogo largo de licencias se puede desplegar, dejando visibles las tareas y los indicadores de identidad.

La preferencia de movimiento se aplica antes de React mediante un script externo compatible con CSP. Respeta la petición del dispositivo incluso si la persona no ha elegido reducirlo. El selector persiste entre recargas y se sincroniza entre pestañas.

El gafete muestra la diferencia entre **zona asignada** y **habilitación interna disponible**. Un QR válido no significa que todas las zonas estén habilitadas: la terminal comprueba permiso, licencia, vigencia, cuenta y aforo. Actualizarlo consulta el estado; no guarda el perfil, eleva privilegios ni acepta términos por otra persona. El vencimiento se presenta en Ciudad de México.

## Seguridad y rendimiento

Las lecturas de servicios usan una instantánea de solo lectura con `mode=ro` y `query_only`. Las mutaciones conservan `BEGIN IMMEDIATE`. La caducidad de invitados se calcula al consultar sin cambiar la base mediante GET; la decisión de acceso sigue comprobando la fecha real. Dos generaciones de gafete pueden procesarse simultáneamente sin reservar el bloqueo del escritor.

La corrección de cupo separa la antigua exclusión de visitantes del límite explícito de un perfil de cuatro personas. Mantiene las asignaciones existentes y rechaza reducir el cupo por debajo de las licencias asignadas. No amplía permisos ni asigna licencias automáticamente.

Los respaldos nuevos se niegan a escribir dentro del repositorio, a sobrescribir un destino o a crear una base inexistente por accidente. Utilizan la API de respaldo de SQLite, comprueban integridad y conservan claves/configuraciones privadas con un manifiesto verificable. La restauración ensayada usa datos ficticios y el mismo usuario Windows; no constituye una migración real.

La actualización de dependencias se hizo en Next. La instalación activa no recibe estos cambios hasta una revisión y decisión posterior. El importador RFID, documentos y seed mantienen su versión saneada para distribución. No se copian la lista real del salón ni sus tarjetas.

## Antes de sustituir la instalación activa

1. Recuperar el ZIP externo: verificar su SHA-256, comprobar el bundle y comparar su rama con esta.
2. Completar privacidad y autenticación GitHub; subir y verificar el historial de Next y ejecutar su CI.
3. Revisar el cambio de dependencias, custodia y configuración en otra instalación aislada.
4. Preparar un respaldo real externo y privado; ensayar la restauración bajo el mismo usuario/equipo Windows.
5. Acordar una ventana, detener únicamente los procesos propios y comparar datos, permisos, factores y resultados después del traslado.
6. Ensayar lector, teléfonos Android/iOS, QR, rechazos y cámaras en la red del salón. Conservar reversión hasta terminar.

No se ha realizado ninguno de los pasos que trasladan producción. El diseño de Base44 tampoco fue integrado: su código requiere otro plan y su vista previa no estaba autenticada.

## Próximas mejoras priorizadas

- Aplicar de forma controlada las dependencias corregidas a la instalación activa, después de respaldo y validación.
- Ensayo con aproximadamente 35 dispositivos y condiciones reales de la universidad; medir latencia, pérdidas y carga sin prometer el rendimiento de localhost.
- Establecer custodia independiente para la auditoría y un procedimiento verificable de eliminación al terminar el plazo.
- Separar gradualmente los componentes grandes de React y los servicios Python, conservando la cobertura de permisos.
- Confirmar el requisito que se llamó «RCIM» antes de diseñar SCIM o integración con otro proveedor de identidad.
