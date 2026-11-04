# Concurrencia local · muestra de 35 clientes

4 de noviembre de 2026. Ensayo opcional de `tests/benchmark_local_clients.py`, con HTTP en loopback, SQLite temporal y una cámara JPEG sintética. Crea su propio servidor en un puerto efímero y 35 personas ficticias. No acepta la URL de un servidor externo, no toca la instalación del salón y elimina su almacén temporal al terminar.

Las sesiones están **preautenticadas por el fixture**. Esta medición no incluye coste de bcrypt, inscripción de MFA, navegador gráfico, HTTPS, Cloudflare, teléfonos ni Wi‑Fi. La autenticación completa se comprueba por separado en los recorridos de navegador.

## Diseño del ensayo

Primera fase: 35 clientes empiezan juntos, cada uno consulta sesión, datos y su propio gafete: 105 solicitudes. Se comprueba que el gafete corresponde al titular de esa sesión.

Segunda fase: 35 lectores hacen ocho consultas cada uno mientras otro hilo registra veinte movimientos QR por la API real de terminal y otro envía JPEG durante cinco segundos. Se mantienen CSRF, cookies, permisos y verificación de acceso del servidor. Los tokens y claves ficticios nunca forman parte del informe. Se comprueba que los veinte movimientos se verifican y que se aceptan cuadros.

Se comparó una cola de aceptación de cinco con una cola de 64, **en el mismo backend de Next con la corrección de cámaras ya aplicada**. No es una comparación completa de Next frente a producción. La aplicación conserva un límite separado de 64 solicitudes activas y dieciséis vistas de vídeo; aumentar la cola no elimina esos límites.

## Resultado observado

| Medida | Cola 5 | Cola 64 |
|---|---:|---:|
| Fase inicial, respuestas HTTP correctas | 105/105 | 105/105 |
| Fase inicial, duración total | 2.23 s | 1.03 s |
| Fase inicial, latencia p50 | 94.0 ms | 125.0 ms |
| Fase inicial, latencia p95 | 2047.0 ms | 719.0 ms |
| Fase mixta, respuestas HTTP correctas | 362/362 | 391/391 |
| Fase mixta, latencia p50 | 31.0 ms | 125.0 ms |
| Fase mixta, latencia p95 | 1046.0 ms | 172.0 ms |
| Terminal, latencia p95 | 32.0 ms | 125.0 ms |
| Movimientos QR verificados | 20/20 | 20/20 |
| Cuadros sintéticos aceptados durante la fase mixta | 62 | 91 |

p50 es la mediana y p95 el percentil 95 de esta muestra. La cola de 64 redujo las esperas largas de conexión; **algunas medianas y el p95 de terminal aumentaron** al procesarse más consultas simultáneamente. No se presenta como mejora de todas las latencias. Una sola pareja de muestras no permite atribuir significación estadística ni predecir el rendimiento en otros equipos.

La eliminación de `BEGIN IMMEDIATE` del tráfico frecuente de cámara se validó con pruebas independientes: los cuadros y mensajes no pueden reservar el escritor, y los cambios de ciclo de vida conservan sus eventos de auditoría. Esta comparación de colas no mide por separado la ganancia de aquella corrección.

## Repetir con límites

Con las dependencias Python instaladas, desde la raíz de una copia de prueba:

```powershell
.\.venv\Scripts\python.exe tests/benchmark_local_clients.py --queue 5
.\.venv\Scripts\python.exe tests/benchmark_local_clients.py
```

El segundo comando usa la cola predeterminada de la aplicación: 64. Los informes se guardan en `../qa-load/`; `ST_QA_OUTPUT` permite otra carpeta. Ejecútalos de forma secuencial y con otros ensayos detenidos para reducir interferencias. El informe `ok` comprueba respuestas y resultados funcionales; no impone un umbral de velocidad que dependa del hardware.

Las evidencias originales saneadas están en [validation/clients-35-queue-5.json](validation/clients-35-queue-5.json) y [validation/clients-35-queue-64.json](validation/clients-35-queue-64.json).

## Aún requiere ensayo físico

Probar unas 35 personas en la red del salón, varias cámaras reales, suspensión/batería de teléfonos, pérdidas, congestión y sesiones de cuatro horas. El lector RFID es un dispositivo teclado; este ensayo usa QR ficticio por HTTP y no demuestra una lectura física de tarjeta. Conserva esas diferencias al presentar los resultados.
