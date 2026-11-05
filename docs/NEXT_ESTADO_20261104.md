# Next: diseño, privacidad y copia independiente · 4 de noviembre de 2026

El acceso incorpora una escena animada original, controles de movimiento y una
paleta azul medianoche/platino. El centro legal presenta 21 cláusulas y seis
referencias oficiales, con versiones para consulta, impresión y firma local.

## Política v1.2

`terms_policy.py` es la fuente canónica. `tools/build_policy.py` genera las copias
HTML, JSON, Markdown y la instantánea del recibo; la compilación ejecuta ese paso.
La aceptación anterior permanece histórica y cada titular acepta la nueva versión
personalmente. La atestación presencial de invitados exige la versión mostrada;
el formulario se limpia después de cada alta. La firma local descargada no equivale
a una aceptación registrada por el servidor ni a una firma electrónica certificada.

Se incorporan Risk Management y Data Protection: evaluación de riesgos, responsable
de cada medida, riesgo residual, minimización, retención, incidentes y derechos ARCO.
Las referencias mexicanas y los marcos NIST están enlazados en el documento.
La ley aplicable depende de quién opere el sistema; no se atribuye responsabilidad
jurídica a la universidad. Faltan definir razón social/ente, domicilio y canal ARCO
permanente. El aviso se identifica como piloto pendiente de formalización y revisión
jurídica. El plazo interno propuesto de 30 días es una decisión del proyecto.
Teams/SharePoint no estaban conectados: no se consultaron las diapositivas.

## Copia privada autorizada

Se creó un respaldo de SQLite mediante apertura de solo lectura y un almacén
independiente, externo al repositorio, protegido por DACL/DPAPI de Windows.
Se conservaron 33 cuentas, 208 accesos, un invitado, cinco licencias de catálogo,
30 asignaciones y los historiales. Se verificó la conservación de hashes de
contraseña y de 28 factores MFA; su custodia fue rotada en la copia. La firma QR
también usa una clave independiente. Los pases y capacidades temporales anteriores
se revocaron exclusivamente en Next: deben emitirse de nuevo desde esta versión.
El colaborador indicado por el propietario recibió `system_admin` en Next.
La versión anterior mantiene su instalación, datos, permisos y procesos separados.
Los detalles de identidades, claves y respaldo permanecen en el almacén privado.

Next usa puertos configurables mediante `ST_CONSOLE_PORT` y `ST_PASS_PORT`;
la copia preparada utiliza 8880/8881. Cloudflare conserva la autenticación de la
aplicación y exige un administrador con contraseña privada, MFA y política vigente.
El túnel es temporal y cambia de URL al reiniciar. La preparación del lanzador no
acredita que exista un túnel activo ni que el sitio ya esté publicado.

## Evidencia y pendientes

- Compilación React y generación documental verificadas localmente.
- Los grupos de política, revisión de términos, acceso de cuatro personas y
  guarda de publicación pasaron con datos ficticios en procesos separados.
- La regresión completa encontró 12 grupos con fallos en esta sesión restringida;
  incluye conexiones HTTP rechazadas por Windows con `WinError 10013` y pruebas
  de cámara dependientes de ellas. No se declara que la suite completa pasó.
- El centro legal se revisó visualmente en escritorio y a 320 px: 21 cláusulas,
  seis referencias y sin desbordamiento horizontal. El navegador automatizado
  completo queda sujeto al resultado de CI sobre la revisión publicada.
- La aceptación v1.2 del administrador en la copia real y la publicación de
  Cloudflare deben comprobarse operativamente; no se aceptan términos por terceros.
- Las pruebas físicas de RFID, teléfonos, Wi-Fi y cámaras prolongadas siguen pendientes.

## Registro inicial de riesgos operativos

| Riesgo | Medida y evidencia requerida | Responsable propuesto | Estado |
|---|---|---|---|
| Responsable legal indefinido | Identificar operador, domicilio, canal ARCO y régimen aplicable | Dirección del proyecto | Pendiente |
| Confusión entre versiones | Almacenes, puertos y claves independientes; probar acceso por URL correcta | Administradores Next | Preparado; recorrido real pendiente |
| Enlaces heredados | Reemitir pases y QR en Next | Administradores Next | Pendiente de entrega |
| Exposición pública | Comprobar MFA, roles, términos y URL HTTPS antes de compartir | Administradores Next | Publicación pendiente |
| Conservación excesiva | Revisar y ejecutar retención justificada; registrar excepciones | Operador y contacto de privacidad | Procedimiento manual propuesto |
| Incidente o pérdida local | Respaldo privado completo; probar restauración y documentar respuesta | Operador | Ensayo de restauración de esta copia pendiente |

Estos controles reducen riesgos; no constituyen certificación de cumplimiento.
