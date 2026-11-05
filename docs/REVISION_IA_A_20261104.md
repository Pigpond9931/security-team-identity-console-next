# Revisión IA A — endurecimiento de Next (2026-11-04)

> Informe original recibido en el ZIP IA A. Sus resultados son declaraciones del
> autor sobre Linux; no describen íntegramente los cambios adoptados. La revisión,
> correcciones y validación Windows de esta integración están en
> [INTEGRACION_IA_A_20261104.md](INTEGRACION_IA_A_20261104.md). La comparación final
> del autor llama «IA B» al avance antiguo faltante; no acredita haber recibido la
> segunda propuesta que espera el propietario. El workflow usa Chromium, no Chrome.

## 1. Identificación y alcance

| Dato | Valor |
|---|---|
| Repositorio | `https://github.com/Pigpond9931/security-team-identity-console-next` |
| Commit base | `66f69a410c84c5672d647aa57991e97165fa382d` |
| Rama de trabajo | `ai-a/next-hardening` |
| Fecha de ensayos | 2026-11-04 |
| Entorno de ensayo | Linux, CPython 3.14, Node 22.23.3, Playwright 1.64.1 con Chromium local |
| Datos | SQLite temporal y cuentas ficticias; ninguna instalación real |
| Producción | No se desplegó, migró ni modificó ninguna instalación |

El objetivo fue localizar defectos comprobables en el código real, corregir primero
los de mayor impacto sin debilitar controles, añadir pruebas adversariales y dejar
explícitas las verificaciones que solo pueden hacerse en Windows.

No se dispone del commit externo `8c667079ae43a3046a4dd8c4fab83bfa2db5b24c` ni del
ZIP con SHA-256 `55fe85bb4930b849f2c6be2be723943afe775888207caee583063de5ba772d79`.
Por tanto no se evaluó ni se atribuyó ningún resultado a ese trabajo.

## 2. Matriz requisito / evidencia

| Requisito | Evidencia en este trabajo | Estado |
|---|---|---|
| Partir del código real y fijar commit | Clon, `git rev-parse HEAD` = `66f69a4…`, rama `ai-a/next-hardening` | Cumplido |
| Leer README, revisión previa, validación, workflows y pruebas | Lectura de `README.md`, `docs/POST_REVIEW_20261104.md`, `docs/VALIDACION_20261104.md`, `PRIVATE_STORAGE.md`, `.github/workflows/ci.yml`, `tests/run_regression.py`, entre otros | Cumplido |
| Corregir P0/P1 comprobados | Dos P1 corregidos: límites de enlaces públicos y agotamiento de sesiones anónimas | Cumplido |
| Corregir P2 de mayor beneficio | Autorización antes de bcrypt y lecturas de pase sin bloqueo de escritor | Cumplido |
| No debilitar MFA, custodia ni privacidad | No se tocaron flujos MFA, DPAPI, DACL, cifrado ni auditoría; los cambios solo añaden límites y lectura | Cumplido |
| Datos ficticios y sin producción | `ST_DATA_DIR` temporal en todas las pruebas; `production_data_used: false` en evidencias | Cumplido |
| Probar en Linux sin fingir DPAPI | Backend POSIX marcado `posix-test-only`; pruebas Windows omitidas con motivo explícito | Cumplido |
| Documentar límites Windows/DPAPI/DACL | Sección 9 de este documento | Cumplido |
| Entregar código, pruebas, decisiones, riesgos y pendientes | Este documento y los commits de la rama | Cumplido |

## 3. Hallazgos y correcciones

### H1 — P1: enlaces públicos de escáner y cámara sin presupuesto de solicitudes

**Evidencia.** En `server.py`, el bloque que atiende
`phone_links.PUBLIC` y `browser_cameras.PUBLIC` se ejecutaba antes del control
`hardening.rate_check`. Un cliente podía enviar intentos repetidos de `claim`,
`poll`, `read`, `signal`, `disconnect` o `upload` sin límite por IP, por token ni
global. Los tokens son largos y aleatorios, pero el coste de sesión, base de datos y
procesamiento de imagen era ilimitado.

**Cambio.** `server.py` incorpora `public_capability_allowed()` y presupuestos antes
de `service.dispatch`:

| Operación | Por token | Por IP | Global |
|---|---:|---:|---:|
| `claim` | 12/min | 60/min | 300/min |
| `poll`, `read`, `signal`, `upload`, `disconnect` | 600/min | 1200/min | 4096/min |
| `upload-frame` (24–25 fps) | 45/s | 90/s | 400/s |

El token se guarda solo como SHA-256 truncado (`hardening.capability_key`), nunca en
claro. La ventana de un segundo se añadió a `hardening.rate_check(..., window=...)`
para no romper la publicación de vídeo. Una solicitud rechazada recibe `429`.

**Prueba.** `tests/test_hardening.py::test_public_claim_endpoints_limit_attempts_before_validation`
envía solicitudes reales por HTTP a ambos `claim`; las primeras 60 por IP no reciben
429 y la siguiente sí. `test_per_second_budget_for_video_frames_is_separate` cubre la
ventana por segundo y la purga de contadores.

### H2 — P1: agotamiento de sesiones anónimas

**Evidencia.** `make_session()` solo eliminaba sesiones caducadas y aplicaba un tope
de 4096. `GET /api/session` crea una sesión sin cookie y devuelve el CSRF; repetir la
petición permitía llenar las 4096 posiciones. Como no se desalojaban sesiones
autenticadas, las nuevas quedaban bloqueadas con 503.

**Cambio.** `server.py` separa dos cupos:

- 512 sesiones anónimas ociosas (`stage='login'`, sin `auth` y sin `challenge`).
- 4096 sesiones totales, que sigue protegiendo a las autenticadas y a los desafíos
  MFA en curso.

Al llegar al cupo ocioso se recicla por antigüedad el 25 % de esas sesiones. Además,
la creación de sesiones nuevas se limita a 120/min por IP y 2048/min global; al
superarlo se responde `429`, no `503`.

**Prueba.** `test_idle_sessions_are_recycled_before_authenticated_ones` llena el cupo
ocioso, conserva una sesión autenticada y comprueba que la nueva sesión entra.
`test_new_session_flood_is_rate_limited` realiza 120 `GET /api/session` correctos y
verifica el `429` del siguiente. `test_session_capacity_preserves_existing_sessions`
se mantiene: con 4096 sesiones autenticadas no se desaloja ninguna.

### H3 — P2: bcrypt antes de comprobar autorización

**Evidencia.** `reset_password()` y `create_user()` calculaban el hash temporal antes
de `require_manager()` / `session_user()`. `change_password()` calculaba el hash de la
contraseña nueva antes de comprobar que la sesión siguiera vigente. Un cliente sin
permiso podía provocar trabajo de bcrypt (coste 12) con solo conocer un id o enviar
una sesión inválida.

**Cambio.** `security.py` hace una comprobación de autorización en conexión de lectura
antes del hash y la repite dentro de la transacción de escritura para evitar carreras
de rol. No se cambió la política de contraseñas, MFA ni auditoría.

**Prueba.** `test_backend.py::test_36_authorization_precedes_password_hashing` sustituye
`hash_password` por una excepción y confirma que las tres rutas deniegan antes de
llegar al hash. Los flujos autorizados siguen pasando en `test_backend`,
`test_initial_passwords` y `test_v130`.

### H4 — P2: lectura de pase público con transacción de escritura

**Evidencia.** `GET /api/public-pass` usaba `secure.write_transaction()` para
`preview` y `read`, aunque en ese método no aceptan términos ni escriben. Reservaba el
escritor de SQLite para una lectura y podía producir `503` bajo carga.

**Cambio.** `server.py` usa `secure.read_transaction()`. `pass_exchange.read()` sin
`accept_terms` y `preview()` son de solo lectura; la aceptación de términos sigue
usando escritura en `POST`.

**Prueba.** `test_read_transactions.py::test_public_pass_get_preview_never_reserves_the_writer`
hace la petición HTTP real con `write_transaction` sustituido por una excepción y
obtiene `200`.

### H5 — Calidad de ensayos: Linux no debe simular Windows

**Evidencia.** Antes de los cambios, en Linux fallaban `test_supervisor`
(`LOCALAPPDATA`), `test_bootstrap` y `test_private_backup` (DPAPI real en
subprocesos). Presentar esos fallos como problemas del producto o silenciarlos con
un backend falso sería engañoso.

**Cambio.**

- `windows_store.py` añade un backend POSIX reversible **solo** con
  `ST_TEST_MODE=1` y `os.name != 'nt'`. Se identifica como `posix-test-only`; en
  Windows `custody_backend()` sigue devolviendo `dpapi-current-user` y el modo de
  prueba no altera DPAPI.
- `test_supervisor` usa una carpeta temporal externa al importar el módulo.
- `test_bootstrap` y la prueba entre procesos de `test_private_backup` se omiten en
  Linux con motivo explícito: requieren DPAPI/DACL reales.
- Los artefactos del navegador indican `posix-test-only (sin DPAPI real; ensayo Linux)`
  en lugar de afirmar que se usó DPAPI.

## 4. Archivos modificados

| Archivo | Cambio |
|---|---|
| `server.py` | Límites de enlaces públicos, cupo de sesiones ociosas, límite de sesiones nuevas, `GET /api/public-pass` en lectura |
| `hardening.py` | Ventana configurable en `rate_check` y `capability_key` opaco |
| `security.py` | Autorización antes de bcrypt y comprobación de sesión antes de cambiar contraseña |
| `windows_store.py` | Backend POSIX de ensayo, marcado explícito; sin efecto en Windows |
| `tests/test_hardening.py` | Pruebas de límites públicos, ventana por segundo y sesiones |
| `tests/test_backend.py` | Prueba de autorización antes de bcrypt |
| `tests/test_read_transactions.py` | Prueba de pase público sin escritor |
| `tests/test_supervisor.py` | Entorno temporal de importación en Linux |
| `tests/test_bootstrap.py` | Omisión explícita fuera de Windows |
| `tests/test_private_backup.py` | Omisión explícita de la custodia entre procesos fuera de Windows |
| `tests/browser_next.py`, `tests/browser_next.cjs` | Backend real declarado en el artefacto de QA |
| `docs/REVISION_IA_A_20261104.md` | Este informe |

## 5. Pruebas ejecutadas y resultados

### 5.1 Regresión completa en Linux

```bash
cd tests
python3 run_regression.py
```

Resultado: **25 grupos, 191 pruebas, 0 fallos, 5 omitidas**. Los grupos omitidos son
`test_bootstrap` (2), `test_runtime_paths` (2, junctions) y `test_private_backup` (1,
custodia entre procesos). La ejecución anterior a los cambios dejaba 3 grupos con
fallos exclusivamente Windows; ahora esos casos están separados de la regresión
portátil.

### 5.2 Navegador real aislado

```bash
ST_TEST_BROWSER_CHANNEL=chromium python3 tests/browser_next.py
```

Resultado: `ok: true`, 16 comprobaciones funcionales, 0 errores de página, 0
violaciones WCAG 2.1 AA en 6 pantallas. El artefacto declara
`backend: posix-test-only (sin DPAPI real; ensayo Linux)` y
`productionDataUsed: false`. En CI Windows se usa Chrome y el backend declara DPAPI.

### 5.3 Carga local acotada

```bash
python3 tests/benchmark_local_clients.py
```

| Escenario | Solicitudes | Estados | p50 | p95 | Duración |
|---|---:|---|---:|---:|---:|
| 35 clientes, lectura en ráfaga | 105 | 200 = 105 | 203.5 ms | 585.0 ms | 1.02 s |
| 35 lectores + terminal + 1 cámara | 411 | 200 = 411 | 176.8 ms | 244.9 ms | 5.05 s |

En el segundo escenario se aceptaron 111 cuadros de cámara y 20 accesos verificados;
no hubo `429`. Es una prueba de localhost con clientes Python y JPEG sintético, no
una medición de Wi-Fi, Cloudflare ni teléfonos reales.

### 5.4 Construcción y dependencias

```bash
npm ci --ignore-scripts
npm run build
node tests/test_camera_url.cjs
npm audit --omit=dev
```

Resultado: compilación correcta sin cambios en `web/`; 8 comprobaciones de URL
correctas; 0 vulnerabilidades. El proyecto fija Python 3.12/Windows x64 en CI, pero
el ensayo se ejecutó con CPython 3.14 en Linux.

## 6. Decisiones tomadas

1. **No se modificó la conservación de códigos de recuperación al desactivar una
   cuenta.** `test_15_baja_reactivacion_conserva_prueba_titular` demuestra que es una
   propiedad intencional (prueba del titular), no un defecto.
2. **El backend POSIX es solo de ensayo.** No sustituye DPAPI ni DACL en Windows y se
   identifica como `posix-test-only` para impedir que se confunda con custodia real.
3. **Los cupos son deliberadamente holgados para el aula.** `claim` permite 60 intentos
   por IP/min; la publicación de vídeo mantiene 45 cuadros/s por token. Se prefiere
   no bloquear una clase de 35 alumnos antes que ajustar al mínimo.
4. **Los límites se aplican antes de validar el token.** Así el intento inválido
   también consume presupuesto; es el comportamiento buscado frente a fuerza bruta y
   abuso de recursos.
5. **No se cambió el esquema de base de datos ni se migraron datos.**

## 7. Instalación y reversión

- Los cambios son compatibles con la instalación existente: no hay migración ni
  cambio de formato de datos.
- Para aplicarlos: integrar la rama/commits y reiniciar el servidor; no hace falta
  borrar `identity.sqlite` ni las claves.
- Para revertir: revertir los commits de la rama. No se eliminó ni renombró ninguna
  referencia.
- El backend POSIX no se activa en Windows ni con el servidor normal: exige
  `ST_TEST_MODE=1` y `os.name != 'nt'`.

## 8. Riesgos y pendientes

| Riesgo / pendiente | Estado |
|---|---|
| DPAPI CurrentUser, DACL/SDDL, junctions y PowerShell reales | **No ejecutado en Linux**; debe validarse en Windows |
| Lector RFID físico, teléfonos Android/iOS, Wi-Fi universitaria y Cloudflare | **No ejecutado**; el benchmark es localhost |
| Sesiones CCTV de 4 h y aforo real | **No ejecutado**; solo pruebas unitarias/HTTP |
| Ataque distribuido con muchas IPs | Los cupos globales limitan memoria, pero un atacante con suficientes IPs puede agotar el presupuesto global; requiere proxy/WAF si se publica |
| Tokens en URL de pase (`?token=`) | Diseño existente; no se cambió. Conviene revisar exposición en historiales/proxies en una revisión específica |
| Accesibilidad de diálogos y foco | Auditoría automática WCAG sin violaciones en 6 pantallas; falta revisión manual con lector de pantalla |
| Comparación con el trabajo de otra IA | **No verificable**: el commit/ZIP indicados no están disponibles |
| Push a GitHub | No se confirmó permiso de escritura; se entrega rama local y parche si hace falta |

## 9. Verificaciones que no se pudieron ejecutar

No se simularon como reales:

- DPAPI CurrentUser (`CryptProtectData`/`CryptUnprotectData`).
- DACL/SDDL, `icacls`, junctions y PowerShell.
- `bootstrap_admin.py` y restauración entre procesos con custodia Windows.
- Instalador, accesos directos y arranque de Windows.
- Cámaras físicas, lector RFID, tablets y teléfonos reales.
- Túnel Cloudflare/ngrok y Wi-Fi del campus.
- CI `windows-latest` con Python 3.12.

## 10. Comparación con otra IA

| Criterio | IA A (este trabajo) | IA B (referencia externa) |
|---|---|---|
| Código verificable | Rama local sobre `66f69a4` | Commit `8c66707…` no disponible |
| Hallazgos P1 corregidos | Límites públicos y sesiones anónimas | No verificable |
| Pruebas Linux | 191 pruebas, 0 fallos, 5 omitidas | No verificable |
| Navegador | 16 comprobaciones, 0 violaciones WCAG | No verificable |
| DPAPI/DACL Windows | Documentado como no ejecutado | No verificable |
| Cherry-picks / dependencias | Ninguno de IA B; no se pudo comparar | No verificable |

No se atribuyen mejoras ni defectos al trabajo externo sin acceso al código.
