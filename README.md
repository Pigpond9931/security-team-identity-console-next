# SECURITY TEAM Identity Console

Código completo de la aplicación académica para Windows: React, Python y SQLite. Versión funcional 1.5.3. Reúne Identity Management, IAM, terminal RFID/QR, invitados, licencias internas, auditoría y vigilancia con teléfonos.

Este repositorio es independiente del Portal de cumplimiento. No incluye las cuentas, contraseñas, secretos MFA, tarjetas reales, sesiones, bases de datos ni copias privadas de la laptop. Las 33 identidades del seed son ficticias y solo se cargan en pruebas o al solicitar una demo. No hay contraseña compartida utilizable por defecto en una nueva instalación.

## Instalación nueva en Windows

Requisitos: Windows 10/11 x64 y Python 3.12 disponible mediante `py -3.12`. Para desarrollar la interfaz también necesitas Node.js 22 o posterior; para utilizarla no hace falta Node, porque `web/` incluye la compilación.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe bootstrap_admin.py
.\INICIAR.cmd
```

También puedes preparar Python con `INSTALAR.cmd`. Bootstrap pide matrícula y nombre, crea el primer administrador del sistema y muestra una contraseña temporal individual una sola vez. Se niega a modificar una base existente. Abre `http://127.0.0.1:8765`, elige contraseña privada, configura MFA, guarda recuperación y acepta los términos. Después crea las demás cuentas desde Personas y permisos.

No hace falta recibir un QR administrativo para el primer ingreso. El QR del autenticador sigue siendo privado y necesario para registrar el segundo factor. Lee [PRIMER_INGRESO_INDIVIDUAL.md](PRIMER_INGRESO_INDIVIDUAL.md).

## Instalación existente

Este código no incluye una migración automática de los datos de tu laptop a GitHub. Conserva la instalación activa y sus respaldos por separado. No copies `data/` o `backups/` al repositorio. Antes de actualizar una instalación con datos, detén sus procesos, respalda mediante `maintenance.py` y valida la restauración en un entorno aislado. DPAPI vincula secretos al usuario/equipo Windows.

## Compartir por Internet con Cloudflare

1. Completa primero el acceso del administrador global en modo local.
2. Ejecuta `./INSTALAR_CLOUDFLARED.ps1` para descargar el binario oficial fijado y verificar SHA-256, o instala tu binario oficial compatible en `tools/cloudflared.exe`. El ejecutable no se almacena en Git.
3. Ejecuta `.\.venv\Scripts\python.exe CONFIGURAR_CLOUDFLARE.py`. Prepara el login propio de la app, sin lista de correos ni PIN.
4. Usa `COMPARTIR_CLOUDFLARE.cmd`, consulta `ENLACE_CLOUDFLARE.md` o `ABRIR_CLOUDFLARE.cmd` y entrega el enlace actual.
5. Detén con `DETENER_CLOUDFLARE.cmd`. No inicies otra instancia sobre el mismo puerto.

El enlace es temporal. La laptop debe permanecer encendida, sin suspenderse y con Internet. Cloudflare no aloja la base ni sustituye el login. No se promete un dominio fijo, disponibilidad permanente o una copia externa de auditoría.

## Funciones

- Cuentas, roles globales y administradores de área con alcance controlado.
- Contraseña temporal individual, un uso, 24 horas; configuración inicial limitada a cinco minutos.
- Contraseña privada, autenticador TOTP, bloqueo por fallos y recuperación privada.
- Separación entre rol, área, permiso de zona y licencia académica interna.
- Terminal RFID/QR con F1-F4, resultado permitido/denegado, entrada/salida, aforo e historial.
- Invitados, entrega móvil limitada y confirmación del anfitrión.
- Centro de vigilancia, vinculación de teléfonos, cámaras IP aprobadas y eliminación de canales.
- Hasta ocho canales combinados; sesiones CCTV de hasta cuatro horas, QR de enlace de cinco minutos y límites de espectadores. Consulta [CCTV_SESIONES_4H.md](CCTV_SESIONES_4H.md).
- Auditoría, análisis de amenazas por reglas y respaldo/rotación local de claves.

La consola sustituye Microsoft 365/OneLogin y los teléfonos sustituyen DVR con el permiso del profesor confirmado por el responsable del proyecto. El lector RFID comercial también fue aprobado. No se implementan SSO externo general, cerradura física, grabación permanente, audio ni reconocimiento facial. La retención y la auditoría bajo custodia independiente siguen siendo decisiones operativas.

## Desarrollo y pruebas

```powershell
npm ci
npm run build
.\.venv\Scripts\python.exe tests/run_regression.py
```

`package.json` fija versiones directas; `package-lock.json` se genera para usar `npm ci`. Las pruebas Python utilizan identidades ficticias y SQLite temporal. Las pruebas de navegador `.cjs` se conservan como fuentes históricas y necesitan un entorno Playwright; no se presentan como una ejecución actual ni todos esos guiones representan el flujo 1.5.2. Para la cobertura y los resultados actuales consulta [VALIDACION_REPOSITORIO.md](VALIDACION_REPOSITORIO.md).

Para comprobar el lector y el video debes realizar además un ensayo real con dispositivos y red del lugar. Una captura de una pantalla vacía no demuestra señal de cámara. Las guías antiguas se conservan como historial; para primer ingreso prevalece el procedimiento individual de 1.5.2 y este README para instalación.

## Estructura

```text
frontend/                 React, componentes, estilos y HTML
web/                      interfaz compilada y fuentes tipográficas
tests/                    pruebas Python y fuentes de pruebas de navegador
LICENSES/                 licencia de las fuentes tipográficas incluidas
server.py                 HTTP, sesiones, CSRF y estados de autenticación
db_manager.py             esquema y seed ficticio opcional
security.py               autenticación, recuperación y autorización
initial_passwords.py      primer ingreso individual
features.py               recursos, invitados, terminal y CCTV
rfid_cards.py             normalización y asociaciones de tarjetas
browser_cameras.py        cámara de navegador y señalización
camera_hub.py             procesamiento y retransmisión de fuentes IP
hardening.py              autorizaciones temporales y destinos aprobados
maintenance.py            respaldo y rotación de claves
bootstrap_admin.py        primer administrador de una base nueva
supervise_cloudflare.py   supervisión del túnel
```

## Cambios de distribución respecto a la laptop

La lógica funcional de la laptop se conserva y la versión 1.5.3 amplía las sesiones CCTV a cuatro horas. Esta copia usa identidades ficticias, omite importación automática de bases vecinas, no carga ejemplos por defecto y añade bootstrap e instalación de una instancia nueva. El importador RFID es solo un ejemplo ficticio y conserva la separación final de zonas IM/IAM; nunca se ejecuta al iniciar. Nada de esto modifica los datos o procesos de la instalación activa.

No se adjuntan reportes con datos personales ni capturas de sesiones reales. Los documentos académicos y sus originales quedan en la carpeta local de entregas del propietario. Este repositorio conserva la documentación técnica textual, saneada para distribución.
