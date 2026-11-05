# SECURITY TEAM · Identity Console Next

**1.6.0-next.1 · evaluación local para Windows.** React, Python y SQLite; gestión de identidades, roles y áreas, MFA, RFID/QR, invitados, auditoría y vigilancia con teléfonos. La instalación existente se conserva por separado. El repositorio distribuye solo código y documentación. Por solicitud del propietario se preparó un almacén privado independiente con los datos anteriores; ese almacén, sus claves y sus constancias están fuera de Git.

El código y el historial completo están subidos a [security-team-identity-console-next](https://github.com/Pigpond9931/security-team-identity-console-next), público temporalmente por autorización del propietario para revisión externa. El original y el portal siguen separados y privados. La CI remota se consulta en la pestaña Actions; los resultados locales y los límites del avance externo se documentan abajo.

El piloto ya se comprobó mediante HTTPS en Cloudflare, con contraseña, MFA y términos v1.2. La URL temporal y los lanzadores del almacén privado se entregan por separado. Consulta el [estado del diseño, política v1.2 y copia independiente](docs/NEXT_ESTADO_20261104.md). Consulta la [integración selectiva de IA A y validación Windows](docs/INTEGRACION_IA_A_20261104.md). La [revisión posterior de 185 pruebas](docs/POST_REVIEW_20261104.md) y los demás informes anteriores se conservan como evidencia de su etapa.

## Procedencia

El original termina en `e58fa9a620b834e6284c679d1dd771bd7cc79750`. Esta rama conserva sus cinco commits y añade el código local saneado más reciente. El ZIP externo mencionado por el propietario no estaba disponible: **no se ha recuperado el commit `8c667079ae43a3046a4dd8c4fab83bfa2db5b24c`**. Véase [PROVENANCE](docs/PROVENANCE.md). Esta iteración es trabajo local provisional que deberá compararse con aquel avance cuando llegue.

La propuesta de Base44 sigue independiente. Su código está bloqueado por el plan y su vista previa exige iniciar sesión. No se importaron sus módulos ni se contrataron servicios.

## Instalar una copia limpia

Requisitos: Windows 10/11 x64 y CPython 3.12 x64. Node.js 22 o posterior se necesita para desarrollar la interfaz; `web/` ya contiene una compilación. El lock de Python incluye hashes de wheels para Windows x64/CPython 3.12; no es un lock universal para otros sistemas o arquitecturas.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe bootstrap_admin.py
.\INICIAR.cmd
```

También existe `INSTALAR.cmd`. Bootstrap solo crea el primer administrador en una base nueva, pide su identidad y muestra una contraseña individual temporal una vez. No sirve para reemplazar cuentas de una instalación existente. Completa contraseña privada, autenticador, recuperación y políticas desde el navegador.

Next abre **http://127.0.0.1:8876**. El original utiliza otro puerto y almacén. No publiques Next durante su evaluación ni lo conectes a los datos reales para probarlo.

## Almacén privado

El valor predeterminado es `%LOCALAPPDATA%\SecurityTeam\IdentityConsoleNext`. Para un ensayo utiliza una carpeta nueva, absoluta y externa:

```powershell
$env:ST_DATA_DIR='C:\MiCarpetaPrivada\IdentityConsoleNextPrueba'
.\.venv\Scripts\python.exe bootstrap_admin.py
.\INICIAR.cmd
```

Se rechazan rutas dentro del repositorio, relativas, raíces, directorios que lo contengan y rutas enlazadas. Un `data/` antiguo con contenido detiene el inicio para no abrir por error otra base vacía. El código no migra datos automáticamente. DPAPI CurrentUser y las ACL privadas de Windows siguen protegiendo el almacén. Consulta [almacenamiento, traslado futuro y reversión](docs/PRIVATE_STORAGE.md).

## Qué incluye esta iteración

- Diseño con grafito, papel cálido y cobre; centro de operaciones con accesos a las funciones autorizadas. Movimiento reducido según el dispositivo, con preferencia persistente.
- Consulta y actualización del gafete por persona, también desde el directorio administrativo. Muestra zonas, habilitaciones internas pendientes y vencimiento en Ciudad de México.
- Separación entre rol administrativo, zona física y licencia interna. Un rol administrativo no sustituye la licencia de una zona. La terminal siempre vuelve a validar el estado vigente.
- Consultas GET en transacciones SQLite de solo lectura, sin reservar el bloqueo de escritura. Una consulta no puede ejecutar una mutación por accidente.
- Cuadros y señalización de vídeo en RAM sin reservar el escritor SQLite; eventos de creación, aprobación y revocación siguen auditados. Cola TCP acotada para conexiones simultáneas, con los límites de solicitudes y espectadores conservados.
- Cupos existentes respetados; el perfil histórico de cuatro personas solo bloquea su límite cuando fue configurado explícitamente.
- Respaldos externos con comprobación de integridad, archivos privados y manifiesto SHA-256; ensayo de restauración con datos ficticios y las mismas claves.
- Publicación condicionada a un administrador global activo, con MFA y políticas vigentes, tanto para DPO como para administrador del sistema.
- Actualización de Pillow y cryptography; cámaras limitadas al decodificador JPEG. Dependencias Python con hashes; acciones CI fijadas a commits oficiales con runtime Node 24 y escaneo de secretos.

## Pruebas

```powershell
npm ci --ignore-scripts
npm run build
.\.venv\Scripts\python.exe tests/run_regression.py
node tests/test_camera_url.cjs
```

Para el recorrido de navegador, instala Chromium de Playwright y usa una base temporal creada por el propio ensayo:

```powershell
npx playwright install chromium
$env:ST_TEST_BROWSER_CHANNEL='chromium'
.\.venv\Scripts\python.exe tests/browser_next.py
```

Si ya tienes Google Chrome puedes omitir esa variable; el ensayo usa `chrome` por defecto. Las dependencias de Playwright y axe-core están fijadas en `package-lock.json`. El ensayo no necesita iniciar sesión en la aplicación real, utiliza una cámara sintética y genera resultados fuera del repositorio, en `../qa-browser/`.

Los resultados vigentes, omisiones y límites se encuentran en [VALIDACION](docs/VALIDACION_20261104.md). No equivalen a una prueba física de tarjetas, teléfonos, red escolar o transmisión de cuatro horas. CI está preparado; no se informa como ejecutado remotamente antes de subir la copia.

## Funciones y límites

La aplicación conserva contraseña privada, TOTP, recuperación individual, bloqueos, roles por área, invitados, verificación RFID/QR, aforo y registro de decisiones. Las licencias son habilitaciones internas del proyecto, no suscripciones comerciales.

CCTV permite hasta ocho canales combinados, cuatro espectadores por canal y dieciséis vistas simultáneas. Las sesiones de vigilancia tienen un máximo absoluto de cuatro horas; el QR de vinculación dura cinco minutos. Hay WebRTC y una alternativa HTTP(S) de cuadros JPEG recientes. No hay grabación permanente, audio, reconocimiento facial ni activación de una cerradura física.

La consola y los teléfonos sustituyen OneLogin/Microsoft y DVR según la autorización académica comunicada por el propietario. No se implementan federación SSO externa ni SCIM. El lector comercial recibe UIDs; el software no programa físicamente las tarjetas ni convierte ese UID en una prueba criptográfica de posesión.

Las políticas v1.1 se conservaron. Indican conservación hasta treinta días después de la última práctica, con revisión/eliminación manual; no existe borrado automático. La firma de la tablet no registra automáticamente una aceptación en la base. La auditoría es local salvo que se configure y verifique un receptor independiente.

## Documentación para continuar

- [Resumen de implementación y decisiones](docs/ITERATION_02_LOCAL.md).
- [Revisión de seguridad y pendientes](docs/SECURITY_REVIEW_20261104.md).
- [Validaciones y sus límites](docs/VALIDACION_20261104.md).
- [Ensayo local de 35 clientes y límites de sus mediciones](docs/BENCHMARK_LOCAL.md).
- [Capturas de Next con datos ficticios](docs/GALERIA_NEXT.md).
- [GitHub: privacidad, autenticación y subida pendiente](docs/GITHUB_HANDOFF.md).
- [Almacén, respaldo y reversión](docs/PRIVATE_STORAGE.md).

Las guías heredadas 1.5.x se conservan como historia del proyecto. Para esta copia prevalecen este README y los documentos de la iteración local. No ejecutes un procedimiento heredado sobre la instalación real sin comprobar su alcance.

La compilación conserva los [avisos y licencias de las bibliotecas y fuentes distribuidas](web/assets/third-party-notices.txt): React, React DOM, scheduler, Lucide, jsQR y Manrope. Las licencias internas de acceso del proyecto se administran por separado en la consola.
