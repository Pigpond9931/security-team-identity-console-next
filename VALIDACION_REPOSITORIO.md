# Validación de la copia para GitHub

3 de noviembre de 2026. Versión 1.5.4.

Pasaron las 142 pruebas Python de los 17 grupos en la copia saneada, cada grupo en un proceso separado con SQLite temporal e identidades ficticias. El runner cubre autenticación, roles, permisos, endurecimiento, contraseña inicial individual y grupal, RFID, cuatro personas autorizadas, visitantes, cámaras, CCTV de cuatro horas, supervisor e instalación nueva. React se compiló correctamente en la instalación y en la copia de distribución.

Las ocho pruebas nuevas del registro grupal comprueban hashes diferentes para una clave común, conservación de cuentas configuradas o privilegiadas, consumo por cuenta, reemisión, caducidad, permisos del emisor, cambio personal/MFA/términos en HTTP y desbloqueo con conservación de factores y auditoría. La concesión de privilegios durante un alta grupal pendiente exige emisión individual.

Las cuatro pruebas del perfil F1 comprueban cuatro tarjetas permitidas, quinta y desconocida denegadas, salida, conservación de otras áreas y credenciales, límite de cuatro licencias, selección válida y rechazo de invitados como quinta identidad.

Se corrigió un fixture de la prueba de capacidad de sesiones: ahora incluye issued_at, como las sesiones reales. La ejecución anterior de GitHub falló porque sus sesiones sintéticas no tenían fecha de emisión y se limpiaban como vencidas; no se debilitó la limpieza real.

Se revisaron visualmente el panel grupal y el botón destacado Desbloquear cuenta en localhost con identidades ficticias, sin ejecutar esos cambios desde el navegador. La instalación activa se respaldó, conserva sus 33 personas y MFA existentes, y sirve la versión 1.5.4. La emisión real se guarda cifrada con DPAPI y no forma parte del repositorio. El perfil real de F1 tiene cuatro titulares preparados; las demás áreas mantienen sus permisos.

Los plazos CCTV se prueban con reloj simulado. No se presenta una transmisión física de cuatro horas ni una lectura real nueva como realizadas en esta actualización. Los guiones históricos de navegador se conservan como fuentes. El resultado remoto de esta revisión debe consultarse en GitHub Actions.
