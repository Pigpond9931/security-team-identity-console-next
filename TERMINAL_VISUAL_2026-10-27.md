# Terminal de acceso · actualización visual del 27 de octubre de 2026

Abre **Terminal de Acceso**. La operación diaria, la consulta y los ajustes tienen pestañas separadas dentro de la misma página.

## Operación

1. Selecciona el área con sus botones o con F1–F4. Se conservan las zonas y permisos actuales; las áreas fuera de tu alcance aparecen deshabilitadas.
2. Elige **Tarjeta RFID**, **Gafete QR** o **Teléfono**. El lector RFID permanece disponible en los tres métodos. Pulsa **Preparar lector USB** si el foco está en otro control.
3. Pasa la tarjeta y Enter, escanea el gafete con la webcam, carga una imagen o vincula el teléfono como escáner. Para pegar un código, abre **Gafete QR → Introducir contenido QR**.
4. Cada lectura muestra el aviso automático de acceso permitido o denegado. La tarjeta de última decisión conserva identidad, zona, entrada o salida, motivo y hora de Ciudad de México. Una decisión anterior no se vuelve a anunciar al abrir la terminal.

Debajo del lector, **Opciones de zona y movimiento** permite elegir la puerta y forzar entrada o salida. El modo inicial sigue siendo entrada/salida automática. Si el teléfono ya estaba vinculado y cambias la zona o la acción, pulsa **Aplicar zona y acción al teléfono** en su panel.

El estado **Lector preparado** indica que el campo tiene el foco: no confirma la detección física del periférico. **Terminal conectada** indica que la última consulta al servidor tuvo éxito. El aviso de resultado depende de la comprobación del servidor.

Los indicadores muestran presencia dentro del alcance del operador, presencia de la zona y aforo global. El reloj muestra fecha y hora CDMX. El sonido es opcional. **Pantalla de kiosco** conserva la vista dedicada al resultado; no es necesario activarla para recibir los avisos.

## Actividad

Consulta los últimos 50 movimientos y la presencia actual dentro de tu alcance. Puedes exportar los movimientos CSV o registrar una salida asistida, con las mismas verificaciones del servidor. La exportación conserva la fecha UTC; la página muestra CDMX.

## Configuración

La pestaña aparece únicamente cuando la API concede administración global. Contiene el aforo de personas y el cupo de tarjetas/licencias de bóveda. Esos controles conservan sus validaciones y auditoría; no conceden permisos por registrar una tarjeta. Los responsables de área y guardias mantienen su operación autorizada sin obtener estos ajustes.

## Uso de cámaras y comprobaciones

Cambiar de método, de zona, de pestaña o entrar a kiosco apaga la webcam local. Cambiar entre Operación y Actividad conserva el vínculo del teléfono; la vinculación sigue limitada a la sesión y plazo originales. El teléfono debe mantener su página abierta y usar su propio botón para encender o apagar la cámara.

La distribución se adapta a escritorio y móvil. La animación del lector respeta la preferencia de reducir movimiento. El resultado usa iconos y texto además del color; las pestañas admiten flechas, Inicio y Fin.

Verificación con API real, SQLite temporal, cuentas ficticias y Chrome: lectura QR y RFID emulado, entrada/salida, avisos consecutivos, foco, atajos, aforo, CSV, escáner móvil, webcam simulada, kiosco, permisos de un responsable de área y diseño móvil. También se ejecutaron las seis pruebas del backend de terminal. El lector RFID y la webcam físicos no se conectaron para esta revisión.

Esta actualización cambia la interfaz sobre el backend 1.5.0. Se publica sin reiniciar el servidor, cambiar el enlace ni modificar cuentas, permisos, MFA, canales o registros. Recarga la página con **Ctrl+F5** para obtenerla. Como cualquier recarga completa, volverá a solicitar que enciendas las vistas locales del navegador; no se revocan los vínculos del servidor.
