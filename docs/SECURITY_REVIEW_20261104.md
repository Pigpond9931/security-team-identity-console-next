# Revisión de seguridad · Next · 4 de noviembre de 2026

Esta revisión combina inspección, escaneo de fuentes/historial y pruebas de Windows con datos ficticios. No es una certificación ni una auditoría exhaustiva. Las correcciones descritas se prepararon en la copia Next; no se migró ni se actualizó la instalación activa.

## Hallazgos y tratamiento

| Prioridad | Hallazgo | Tratamiento en Next |
|---|---|---|
| Alta | Los datos y claves podían ubicarse dentro de la carpeta de código; una configuración equivocada podía crear otra base vacía. | Resolutor externo compartido por Python/PowerShell, rechazo de rutas internas/enlazadas y parada si existe `data/` antiguo con contenido. Sin traslado automático. |
| Alta | La auditoría de requisitos detectó avisos en Pillow 12.3.0 y cryptography 48.0.1. | Actualizados a Pillow 13.0.0 y cryptography 50.0.2. Los ocho wheels Windows se verificaron contra SHA-256 publicado en PyPI; lock con hashes. El análisis posterior se guarda con la validación. |
| Alta | El decodificador de cámaras podía intentar formatos ajenos al contrato JPEG/MJPEG. | Se limita `Image.open` al formato JPEG antes de decodificar. Se conservan límites de tamaño y resolución; PNG y EPS se rechazan en pruebas. |
| Media | Un GET de consulta reservaba el bloqueo de escritura de SQLite; algunos GET también caducaban invitados mediante UPDATE. | Lecturas con instantánea `mode=ro` y `query_only`; caducidad calculada en la respuesta. Las escrituras siguen en transacción explícita. Una prueba concurrente verifica dos generaciones de gafete. |
| Media | El cupo de una instalación podía quedar forzado a cuatro por un indicador heredado que también excluía invitados. | Límite explícito separado. Se conserva un perfil de cuatro si se configura como tal; se respetan otros cupos existentes y no se permite reducir por debajo de las asignaciones. |
| Media | Un administrador del sistema nuevo podía quedar bloqueado para publicar porque ciertos lanzadores exigían específicamente DPO. | Guardia común para un administrador global activo, con MFA, contraseña personal y políticas vigentes. Se prueba que un usuario normal no es suficiente. |
| Media | El respaldo podía crear SQLite vacío al señalar una base inexistente y no tenía manifiesto. | Lectura de origen `mode=ro`, integridad de origen/destino, claves/configuración privada y manifiesto; se rechazan destinos internos o existentes. Restauración ensayada con fixtures, sin reemplazar claves. |
| Media | El gafete enseñaba zonas asignadas sin distinguir una licencia interna faltante. | Estado por zona y vencimiento CDMX; no cambia permisos. El verificador de la terminal sigue siendo la autoridad y deniega al revocar la licencia. |
| Media | CI heredaba acciones con Node 20 y referencias por etiqueta. | Acciones oficiales actuales con Node 24, fijadas a commits consultados en sus repositorios; permisos de solo lectura y sin persistir credenciales del checkout. |
| Baja | Etiquetas de QR/terminal y algunos botones tenían contraste insuficiente; áreas con nombre accesible incompleto. | Ajustes de contraste y nombres derivados del texto visible. Validación automatizada y visual documentada por pantalla. |

Las fuentes oficiales de [Pillow 13.0.0](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html), [cryptography 50.0.2](https://pypi.org/project/cryptography/50.0.2/), [SQLite query_only](https://www.sqlite.org/pragma.html#pragma_query_only) y [retiro de Node 20 en Actions](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/) sustentan la selección de actualizaciones y controles. Los commits exactos de acciones están en `action-pins.json`.

## Autenticación y autorización conservadas

- La autorización se comprueba en Python con el usuario y permisos vigentes. Ocultar una pestaña en React no concede ni revoca acceso.
- Se mantienen contraseña privada, TOTP con prevención de reutilización, bloqueos por fallos, recuperación individual, revocación por versión de seguridad y comprobación de políticas vigentes.
- DPO no puede conceder el rol de administrador del sistema. Los administradores de área conservan su alcance; cambiar permisos propios no es una vía de elevación.
- Roles, áreas, habilitaciones internas y aforo son conceptos distintos. El QR solo identifica una credencial firmada: la terminal vuelve a comprobar las condiciones actuales.
- Las sesiones habituales tienen límite de treinta minutos; las de vigilancia, cuatro horas absolutas. Los QR de enlace de dispositivos duran cinco minutos y no conceden acceso al directorio.
- Se conservan CSRF y origen exacto para POST, cookies HttpOnly/SameSite, Secure en publicación HTTPS, CSP sin `unsafe-inline`, límites de JSON y rutas estáticas dentro de `web/`.
- Los destinos IP requieren aprobación global exacta, direcciones privadas y puertos admitidos; no se aceptan credenciales embebidas ni redirecciones HTTP.

## Secretos, historial y datos reales

Se revisaron la lista distribuible y las referencias del historial original de cinco commits. Gitleaks se ejecuta con redacción de valores. La única excepción añadida es el identificador literal de una migración en `hardening.py`, limitado a ese archivo y a la regla genérica: no se desactivó el escaneo de claves ni se excluyó toda una carpeta.

Los guiones históricos de navegador contenían la contraseña inicial compartida usada antiguamente por la instalación. En el árbol actual de Next se sustituyó por una credencial inequívoca de pruebas. El historial se conserva según la instrucción del propietario; la clave operativa compartida ya tenía vencimiento el 4 de noviembre y no se renovó. Si se reutilizó ese valor en otro servicio, corresponde cambiarlo allí. No se imprimen sus caracteres en este informe y no se presenta la conservación del historial como una eliminación de aquella exposición.

Next no contiene las cuentas reales del salón, sus UIDs, bases, claves, sesiones, enlaces operativos ni documentos firmados. Conserva el seed ficticio opcional y la plantilla de políticas en blanco. Los responsables nombrados en el aviso existente forman parte de su contenido previamente autorizado, no de una exportación del directorio.

La instalación real se examinó mediante inventario de solo lectura: integridad SQLite, formato cifrado de factores, presencia de archivos DPAPI y DACL privada. No se descifraron claves reales, no se copiaron datos y no se detuvieron procesos. Ese inventario privado permanece fuera de este repositorio. Las pruebas de restauración se hicieron exclusivamente con datos ficticios bajo el mismo usuario Windows.

El repositorio del portal se mantiene privado e independiente. Su revisión se limitó a metadatos del árbol y visibilidad: la descarga fue rechazada por el navegador. No se afirma haber escaneado su contenido o historial ni haber saneado ese proyecto.

## Pendientes y límites

1. Completar la confirmación de identidad de GitHub para dejar privado el original y habilitar la subida al nuevo repositorio privado. No se reescribió historial, no se forzó ningún push y no se modificaron colaboradores.
2. Recibir y verificar el ZIP externo antes de integrar el commit informado. Esta rama no sustituye ese archivo faltante.
3. Validar las actualizaciones de seguridad en un clon aislado de la instalación real y acordar su despliegue con respaldo/reversión. La aplicación activa conserva sus dependencias anteriores; no se declara corregida por haber corregido Next.
4. Probar junctions fuera del sandbox, dispositivos RFID reales, teléfonos Android/iOS y la red escolar. Las transmisiones de prueba usan cámara sintética; una prueba local corta no demuestra cuatro horas ni capacidad para todo el salón.
5. Proveer custodia independiente de auditoría. Un administrador con control del equipo puede alterar los archivos locales; la firma de QR y DPAPI no resuelven por sí solas ese riesgo.
6. Ejecutar revisión/eliminación manual al terminar el plazo de políticas. No hay borrado automático ni firma electrónica avanzada; una constancia de tablet no implica aceptación automática en la base.

La baja posibilidad de hallar un secreto con un escáner no equivale a demostrar su ausencia. El lector de UID y una fotografía de QR tampoco ofrecen protección criptográfica contra copia. Estos límites se conservan explícitos en la documentación del proyecto.
