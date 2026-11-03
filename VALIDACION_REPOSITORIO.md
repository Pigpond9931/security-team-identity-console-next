# Validación de la copia para GitHub

Actualización del 2 de noviembre de 2026: versión 1.5.3.

La revisión anterior pasó 124 pruebas y la compilación en GitHub Actions (ejecución 41564834808). Para esta actualización pasaron 70 pruebas de los grupos afectados: backend (35), duración CCTV (6), cámaras del navegador (5), vigilancia (7), escáner móvil (8) y eliminación de cámaras (9), cada grupo en un proceso separado con SQLite temporal. Las seis nuevas también pasaron en la copia saneada para distribución. Se compiló React en ambas copias.

El reloj simulado comprueba continuidad después de treinta minutos y antes de cuatro horas, vencimiento al llegar al límite absoluto, limpieza de sesiones, QR de cinco minutos y uso único, cierre de sesión, retirada de permisos y cookies de publicación. Los escáneres de acceso y las cuentas sin CCTV conservan treinta minutos.

Se respaldó la instalación local y se activó la versión 1.5.3, verificando su health público y la pantalla de inicio de sesión. No se ensayó una transmisión física de cuatro horas con teléfonos. La cobertura real depende de Wi-Fi, batería y suspensión de los dispositivos.

El workflow incluye ahora 15 grupos (130 pruebas previstas). Su resultado para esta revisión debe consultarse en GitHub Actions. Los guiones históricos de navegador se conservan como fuentes y no se presentan como ejecuciones actuales. No se publican datos reales, claves, credenciales ni capturas de usuarios.
