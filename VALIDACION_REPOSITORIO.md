# Validación de la copia para GitHub

Corte de publicación: 2 de noviembre de 2026. Versión funcional 1.5.2.

Pasaron 122 pruebas Python en 13 grupos independientes, más dos pruebas del instalador/primer administrador: 124 en total. Las cuatro de importación RFID se repitieron después de sustituir los UID de demostración. Todas usan SQLite temporal e identidades ficticias. También se compiló React desde las fuentes con las dependencias fijadas.

Los grupos cubren backend, versión funcional, endurecimiento, primer ingreso, terminal, referencia RFID, cámara de navegador, escáner de teléfono, cámara IP, administración/eliminación de cámaras, vigilancia y supervisor. Las dos pruebas nuevas comprueban la creación individual del administrador sin cargar demo, el rechazo de una base existente y la validación de la identidad antes de crearla.

La instalación activa de la laptop no fue modificada. No se realizaron lecturas físicas nuevas, transmisiones reales de teléfono ni pruebas de red pública durante esta preparación. Los guiones históricos de navegador se incluyen como fuentes y no se presentan como ejecuciones actuales.

El workflow de GitHub Actions ejecuta instalación, compilación y los 14 grupos en Windows. Su resultado remoto debe consultarse en Actions; haber preparado el YAML no significa que GitHub ya lo haya ejecutado.
