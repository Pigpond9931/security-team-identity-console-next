# Integración selectiva de IA A · 4 de noviembre de 2026

## Procedencia y alcance

Base: `66f69a410c84c5672d647aa57991e97165fa382d`. Entrega recibida desde
`/home/Chileserran0/entrega-ai-a-next/entrega-ai-a-next-20261104.zip` en Ubuntu/WSL.
SHA-256: `bcddffa08a7c23583629b622eafd0d4409182c974d8e8ed5c78fafb0b9a608b2`.
Contiene un diff acumulado y cuatro parches; no es una copia completa del proyecto
ni acredita por sí mismo los SHA de los commits del autor. El diff se comprobó
contra la base antes de aplicarlo selectivamente en `review/ia-a-next-20261104`.

El [informe original](REVISION_IA_A_20261104.md) conserva las afirmaciones del autor.
Sus resultados Linux no sustituyen las verificaciones Windows de esta integración.
La segunda propuesta sigue pendiente. El ZIP antiguo de SHA `55fe85bb…` y commit
`8c667079…` tampoco se recuperó; son pendientes distintos.

## Decisiones sobre el código recibido

| Propuesta | Decisión |
|---|---|
| Autorizar antes de bcrypt en alta, restablecimiento y cambio de contraseña | Adoptada. Se conserva la segunda comprobación dentro de la escritura. |
| GET de pase público sin reservar escritor SQLite | Adoptada. Pruebas HTTP de preview, recibo y descarga; aceptar términos sigue siendo escritura. |
| Cupo y reciclaje de sesiones anónimas ociosas; presupuesto de nuevas sesiones | Adoptada. No se desalojan sesiones autenticadas ni desafíos MFA por este reciclaje. |
| Presupuestos de enlaces públicos | Adoptados con las correcciones descritas abajo. |
| Supervisor de prueba con carpeta temporal | Adoptado con entorno limitado a la importación, sin heredar una carpeta real. |
| Backend POSIX reversible y omisiones de pruebas Windows | No adoptados. Next continúa dirigido a Windows; DPAPI/DACL y pruebas nativas se conservan. |
| Manifiesto del autor | No adoptado. Se genera uno que corresponde a los archivos realmente integrados. |
| Cambios en interfaz o dependencias | La entrega no los propone; no se añaden lenguajes ni dependencias. |

## Defectos corregidos durante la revisión

1. **Cruce de ventanas de límites.** El parche usaba el mismo diccionario para
   ventanas de un segundo y de un minuto. Su purga global permitía que un cuadro de
   cámara borrara contadores de autenticación o vinculación de más de un segundo.
   `FRAME_RATE` mantiene separados los cuadros. Una regresión intercala ambos
   tráficos con reloj controlado y exige que el límite de acceso siga bloqueado.
2. **Consultas privadas en el cupo público.** El parche limitaba también RPC
   privados de espectadores, todos bajo la clave de token ausente. Se limita
   exclusivamente el conjunto PUBLIC de cada servicio, conservando sus controles
   de sesión, CSRF y permisos. Una regresión consulta repetidamente todas las rutas
   privadas y comprueba que no consumen los contadores públicos.
3. **Vídeo alternativo y red compartida.** Tanto `upload-frame` como `upload`
   consumen el presupuesto de cuadros. Se mantienen 45/s por token y 400/s global,
   con 240/s por IP. El resto de llamadas públicas permite 600/min por token,
   4096/min por IP y 8192/min global; claim conserva 12/60/300 por minuto. Ensayos
   deterministas cubren ocho publicadores a 25 cuadros/s y las consultas de 35
   escáneres más ocho cámaras bajo una IP. Estos presupuestos no garantizan la
   capacidad física del servidor ni de Wi-Fi.
4. **CI Windows previo.** La ejecución `41832762124` falló en cuatro comparaciones
   de `test_runtime_paths`: el fixture guardaba una ruta abreviada `RUNNER~1`,
   mientras el resolutor devolvía `runneradmin`. Se normaliza la raíz del fixture
   con `resolve()`, sin relajar guardas de almacenamiento. Una prueba nativa
   adicional entrega un alias obtenido mediante `GetShortPathNameW`.
5. **Sesiones anónimas con tareas iniciadas.** Una cámara vinculada, un escáner o
   un pase de invitado pueden seguir en stage login. El reciclaje propuesto los
   confundía con sesiones ociosas; también podía descartar una activación vigente.
   Se excluyen del reciclaje las capacidades y activaciones vigentes, además de
   autenticación y MFA. La vigencia se marca al emitir la capacidad desde el
   servidor, sin guardar tokens adicionales ni prolongar el límite de sesión.

## Validación de la integración

| Comprobación | Resultado local |
|---|---|
| Regresión completa Windows, Python 3.12 | 197 pruebas en 25 grupos, 0 fallos y 0 omisiones. |
| Refinamiento final del reciclaje de sesiones | 16 pruebas de hardening repetidas después del ajuste, todas correctas. |
| Navegador tras el ajuste final | Chrome: 16 comprobaciones, 0 errores JS y 0 infracciones axe en seis pantallas. |
| Compilación de React | Correcta; sin cambios en los archivos compilados. |
| Direcciones de cámara | Ocho comprobaciones correctas. |
| Manifiesto de fuentes | 204 entradas verificadas. |

Todas las pruebas usan almacenes temporales y cuentas ficticias. El recorrido de
navegador utiliza Chrome instalado: Chromium de Playwright no estaba instalado
localmente. El workflow Windows conserva la instalación y ejecución de Chromium.
La regresión completa empezó antes del último refinamiento de sesiones; el grupo
afectado y el navegador se repitieron sobre el código final. El CI de la rama
verificará la revisión completa desde un checkout limpio; no se presupone su éxito.

## Pendientes operativos

Recibir la propuesta IA B y comparar su código contra la misma base. Las pruebas
físicas de RFID, teléfonos, Wi-Fi escolar y cámaras durante cuatro horas siguen
pendientes. La instalación anterior, sus procesos, sus datos y sus claves no se
modificaron. No se desplegó ni se migró producción.
