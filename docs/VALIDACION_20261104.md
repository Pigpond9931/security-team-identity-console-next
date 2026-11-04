# Validación de Next · 4 de noviembre de 2026

**1.6.0-next.1, evaluación local.** Los resultados corresponden al código de esta copia y a instalaciones temporales externas. No se reutilizó como prueba el resultado anunciado por la iteración externa que falta. No se ejecutó una migración ni una prueba con datos de producción.

## Resultado comprobado

| Comprobación | Resultado y alcance |
|---|---|
| Regresiones Python nativas | **177 descubiertas: 176 pasaron, 1 omitida, 0 fallos**, en 25 grupos aislados. Windows y DPAPI reales; SQLite y personas ficticias. |
| Navegador | 16 comprobaciones en Google Chrome y las mismas 16 en Chromium de Playwright, con backend Python real aislado. Cero errores JavaScript observados. |
| Accesibilidad | axe-core, seis pantallas por navegador, reglas WCAG 2.0/2.1 A/AA: cero violaciones detectadas. No es certificación ni reemplaza un ensayo con lector de pantalla. |
| Diseño adaptable | Escritorio 1440 px, tablet 768 px, móvil 390 y 320 px; gafete sin desbordamiento horizontal. Terminal móvil y centro de vigilancia revisados. |
| Compilación limpia | `npm ci --ignore-scripts` y `node build.mjs` completados. La compilación también funciona al invocarse desde otra carpeta. |
| Dependencias | npm: cero avisos conocidos en producción y desarrollo; pip-audit con OSV: cero en las ocho dependencias Python fijadas. `pip check` correcto. Son resultados de la fecha, no garantía de ausencia de vulnerabilidades. |
| URLs de cámara | Ocho comprobaciones: pegado de URL completa, reparación del campo ruta y conservación de controles del servidor. |
| PowerShell y CI | Todos los lanzadores `.ps1` de la raíz pasan el análisis sintáctico. Los dos workflows pasan actionlint 1.7.12. No se ejecutaron Actions remotas porque no se ha podido subir la copia. |
| Custodia y recuperación | Ensayo real de DACL privada, claves DPAPI y respaldo/restauración en un proceso nuevo bajo el mismo usuario Windows. Datos ficticios. |
| Concurrencia | 35 clientes HTTP de prueba, terminal y cámara sintética; sin errores en las muestras. El detalle de latencias, medianas que aumentaron y límites está en [BENCHMARK_LOCAL](BENCHMARK_LOCAL.md). No se midió carga de autenticación ni Wi-Fi. |
| Compatibilidad de actualización | Fernet de cryptography 48.0.1 descifrado por 50.0.2 y viceversa; JPEG de Pillow 12.3.0 leído por 13.0.0. El archivo DPAPI ficticio se conservó byte a byte. No prueba reversión de esquema de SQLite. |

La omisión corresponde a crear junctions reales: el entorno restringido de Windows denegó su creación. Se probaron rutas internas, relativas, vacías, raíces, ascendientes, archivos, recorrido normalizado y `data/` antiguo, pero **debe repetirse el caso real de junction fuera del sandbox**.

## Cobertura nativa por grupo

| Grupo | Pasaron | Omitidas |
|---|---:|---:|
| `test_backend` | 35 | 0 |
| `test_v130` | 20 | 0 |
| `test_hardening` | 8 | 0 |
| `test_initial_passwords` | 7 | 0 |
| `test_terminal_rfid` | 6 | 0 |
| `test_rfid_reference_import` | 4 | 0 |
| `test_browser_cameras` | 5 | 0 |
| `test_phone_links` | 8 | 0 |
| `test_camera` | 7 | 0 |
| `test_camera_admin` | 5 | 0 |
| `test_camera_removal` | 9 | 0 |
| `test_surveillance` | 7 | 0 |
| `test_supervisor` | 2 | 0 |
| `test_bootstrap` | 2 | 0 |
| `test_cctv_duration` | 6 | 0 |
| `test_group_onboarding` | 8 | 0 |
| `test_four_person_access` | 4 | 0 |
| `test_terms_revision` | 3 | 0 |
| `test_runtime_paths` | 10 | 1 |
| `test_access_capacity` | 3 | 0 |
| `test_publication_guard` | 3 | 0 |
| `test_private_backup` | 3 | 0 |
| `test_read_transactions` | 5 | 0 |
| `test_qr_readiness` | 2 | 0 |
| `test_camera_read_transactions` | 4 | 0 |

El runner es `tests/run_regression.py`; lanza cada grupo en un proceso separado. Los ensayos adicionales impiden una escritura accidental mediante GET o una consulta de cámara, permiten dos generaciones simultáneas de gafete, respetan un cupo existente de doce y deniegan el acceso tras revocar una habilitación. El vídeo frecuente no reserva el escritor de SQLite y las operaciones de ciclo de vida conservan la auditoría. No se reducen requisitos de MFA, políticas ni alcance administrativo.

## Recorrido de navegador

`tests/browser_next.py` crea su base en una carpeta temporal externa, comprueba esa separación y nunca usa la instalación activa. `tests/browser_next.cjs` realiza contraseña temporal individual, cambio a privada, alta del autenticador, guardado de recuperación, aceptación de políticas vigentes, directorio, consulta del gafete y actualización. No captura las pantallas que enseñan secretos de inscripción o recuperación.

Se verifican movimiento reducido antes de cargar React, persistencia de la preferencia, contraste del botón principal, cierre con Escape, estado de habilitación pendiente y tamaños de pantalla. El centro de vigilancia utiliza una cámara sintética de Chrome/Chromium; se observa vídeo decodificado, no se considera suficiente una tarjeta vacía.

El teléfono de prueba reclama y confirma una vinculación real, recibe una capacidad limitada y no puede consultar el directorio administrativo. Se prueban WebRTC, cuadros JPEG por HTTP(S), pausa/reanudación, revocación, mosaico, cambio individual, ronda de quince segundos y liberación de espectadores al cambiar de sección.

## Medición limitada de vídeo

En Chromium local se observaron 51 cuadros WebRTC decodificados en 2.5 segundos y 54 cuadros JPEG aceptados por el backend en aproximadamente 2.51 segundos. Son **20.4 fps** y **21.5 fps** en esa muestra sintética. No miden una cámara física, el túnel, la distancia del salón, estabilidad durante cuatro horas ni carga de treinta y cinco teléfonos. No se promete esa velocidad en la universidad.

## Ejecutarlo otra vez

En una copia Windows x64 con CPython 3.12, desde la raíz:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
npm ci --ignore-scripts
npm run build
.\.venv\Scripts\python.exe tests/run_regression.py
node tests/test_camera_url.cjs
npx playwright install chromium
$env:ST_TEST_BROWSER_CHANNEL='chromium'
.\.venv\Scripts\python.exe tests/browser_next.py
```

No definas `ST_TEST_MODE=1` en una instalación de uso real. Los propios fixtures lo configuran en sus procesos. Los resultados del navegador se guardan fuera de la copia (`../qa-browser/`, o una carpeta indicada con `ST_QA_OUTPUT`). En este sandbox se usó además una carpeta temporal permitida mediante `TEMP` y `TMP`; no es un requisito del Windows habitual.

Para comprobar la entrega sin arrancar la aplicación: `python tools/source_manifest.py`. Verifica contenido SHA-256, normalizando CRLF a LF en los formatos de texto enumerados; no se incluye a sí mismo. Es un control de integridad, no una firma ni un escáner de secretos. El SHA-256 exterior del ZIP y el bundle se entregan aparte.

## Evidencias y límites

Los JSON saneados de esta ejecución están en [validation/](validation/). Las capturas están en [galería](GALERIA_NEXT.md); contienen únicamente personas y cámaras ficticias. El inventario privado de producción y los archivos temporales con secretos de prueba no se incorporan al repositorio.

Antes de sustituir la instalación activa faltan: recuperar el ZIP externo, resolver acceso/privacidad GitHub y ejecutar CI remoto; ensayar junctions, lector físico y teléfonos Android/iOS; probar red escolar y aforo; y acordar el respaldo/restauración y despliegue. La instalación real conserva sus dependencias anteriores hasta una decisión específica. La conservación manual de políticas y la custodia independiente de auditoría continúan como pendientes operativos.
