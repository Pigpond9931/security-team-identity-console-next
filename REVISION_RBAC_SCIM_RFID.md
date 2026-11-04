# Revisión de funciones: SECURITY TEAM

Fecha: 3 de noviembre de 2026. Aplicación 1.5.4 con ajuste de audio de la terminal.

## Resultado

| Función | Estado | Alcance real |
|---|---|---|
| RBAC | Implementado | Roles de administrador del sistema, DPO, responsable de área y usuario; validación en el servidor y alcance por área. Las zonas y licencias añaden condiciones. |
| RCIM | Término pendiente de identificar | No hay un módulo o protocolo con ese nombre en el código revisado. No se acredita cumplimiento de un requisito sin identificarlo. |
| SCIM, si ese era el término | No implementado | La API interna no es un conector SCIM 2.0. No hay aprovisionamiento estándar desde otro proveedor de identidad. |
| Crear usuarios | Implementado | Administración global crea identidades y entrega una contraseña temporal individual. El titular configura contraseña y MFA. |
| Modificar usuarios y permisos | Implementado | Edición de perfil, rol y área conforme al alcance del administrador; asignación o revocación de zonas y licencias internas. |
| Borrar usuarios | Baja lógica | «Desactivar identidad» inhabilita la cuenta y revoca sesiones, MFA y RFID; conserva el registro y la auditoría. No es un borrado físico de todos los datos. |
| Registrar tarjetas | Implementado | Se vincula el UID recibido por el lector a la cuenta. Los datos y permisos residen en SQLite. |
| Cambiar o revocar acceso a una tarjeta | Implementado | La siguiente lectura consulta el estado y permisos actuales. No se modifica la tarjeta física. Un bloqueo o baja niega nuevos accesos. |
| Programar físicamente tarjetas | No implementado | La integración actual utiliza el lector como teclado USB para recibir el UID. No tiene comandos de escritura. Si las tarjetas son EM4100 genuinas, son de solo lectura y vienen programadas de fábrica. Los UID registrados no identifican por sí solos el modelo del chip. |

## Dónde demostrarlo

1. **Personas y permisos → Crear identidad**: crear una cuenta ficticia de demostración, con matrícula única.
2. Abrir una persona: editar perfil, rol o área si el alcance del administrador lo permite.
3. En la misma ficha, asignar zonas y licencias. Un responsable de área no administra personas de otra área ni puede elevarse a administrador global.
4. **Seguridad → Desactivar identidad**: demostrar la baja sobre una cuenta ficticia preparada, conservando la bitácora. No utilizar cuentas de compañeros para una demostración destructiva.
5. Para una tarjeta: registrar su UID en el perfil, usar una zona permitida y pasarla por el lector en la terminal. Cambiar el permiso o bloquear la cuenta y volver a leerla para observar la nueva decisión.

Las decisiones de acceso se registran en la aplicación; no se acciona una cerradura física. La revocación del servidor no cambia los bits del chip ni impide que otro sistema independiente acepte la tarjeta. La visualización en otra terminal se actualiza con el sondeo de eventos, mientras la autorización se evalúa en cada solicitud.

## Sonido actualizado

- Las alertas están habilitadas por defecto al entrar a la terminal, también tras recargar.
- Se retiró el interruptor de silencio de la terminal. El botón sirve para activar o probar el audio.
- Permitido: dos tonos ascendentes. Denegado: tres pulsos más largos, claramente distintos.
- Se aumentó la amplitud digital de 0,25 a 0,8 y se prolongaron los tonos con una fase sostenida. Esto no equivale a un nivel acústico garantizado: depende de las bocinas y del volumen del sistema.
- El audio se prepara con la primera interacción por teclado o puntero y se intenta recuperar al volver a la pestaña. El navegador puede exigir esa interacción para permitir reproducción.
- Si el navegador aún no permite audio, se muestra «Activar sonido». Cuando está listo aparece «Sonido activo · Probar».
- El equipo encendido, la pestaña abierta y el volumen del sistema son necesarios. El código no puede forzar audio en una pestaña silenciada, con el dispositivo suspendido o sin salida de sonido.
- Al salir de la terminal se cierran los recursos de audio.
- Una lectura denegada muestra «Intento de entrada denegado» o «Intento de salida denegado», evitando presentarla como un movimiento autorizado.

## Verificación

Se ejecutaron 35 pruebas de backend y 20 de funciones sobre bases temporales: creación, controles de rol y área, cambios de seguridad, baja y revocación de sesiones, licencias, RFID, QR y auditoría. Las 55 pasaron.

También se probó en Chrome una terminal con identidades ficticias y un AudioContext real: tono de prueba, RFID permitido y desconocido, señales distintas y no nulas, activación tras recarga, vista de 390 px sin desbordamiento, cierre del audio al salir y ausencia de errores JavaScript. Esta prueba verifica la señal digital, no sustituye escuchar las bocinas en el salón.

La comprobación no grabó tarjetas físicas ni ejecutó pruebas sobre las cuentas reales del salón. No se añadió SCIM ni se cambió la asignación de roles, zonas, licencias o tarjetas reales.

## Referencias técnicas

- RBAC y ciclo de vida local: `security.py`, `server.py`.
- Zonas, licencias y lectura de credenciales: `features.py`, `rfid_cards.py`.
- Audio: `frontend/terminal-sound.jsx` y su uso en `frontend/features.jsx`.
- SCIM: [RFC 7644](https://www.rfc-editor.org/info/rfc7644/).
- Restricciones de reproducción: [MDN: Web Audio API best practices](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices).
- Tarjetas de solo lectura: [EM Microelectronic: EM4200 y compatibilidad con EM4100/4102](https://www.emmicroelectronic.com/product/lf-animal-access-ics/em4200).
