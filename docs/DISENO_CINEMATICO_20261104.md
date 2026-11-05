# Rediseño de Next · 4 de noviembre de 2026

Por solicitud del propietario se reemplaza la dirección grafito/papel/cobre por
azul medianoche, platino y azul de acción. La escena de acceso es una escultura
procedural original de cintas metálicas: se dibuja localmente, se anima y responde
suavemente al puntero. No es un vídeo descargado ni una cámara real.

## Alcance

- Composición editorial del acceso, nueva jerarquía de tipografía y formularios.
- Escena visible también en móvil; control de pausa/reanudación y respeto a la
  preferencia de movimiento reducido del dispositivo y de la aplicación.
- El render se detiene al ocultar la pestaña, salir de pantalla, reducir
  movimiento o desmontar el componente. Límite de 24 fps y DPR máximo de 1.5.
- Sidebar, acciones, métricas, panel de identidad, tablas, perfil, gafetes,
  terminal y vigilancia comparten la nueva dirección. Los estados de éxito,
  advertencia y denegación conservan sus colores semánticos.
- No se modifican los servicios Python, permisos, MFA, cuentas, claves o esquema.
  El servidor local ya abierto sirve los nuevos archivos compilados.

## Referencias y herramientas

Se consultaron el [sistema de colores Geist](https://vercel.com/geist/colors), la
[revisión de interfaz de Linear](https://linear.app/now/behind-the-latest-design-refresh)
y los temas accesibles del plugin MagicPath, incluida la definición OpenAI 9000.
Sirven como referencias de jerarquía, superficies y contraste. No se importaron
componentes, código ni recursos visuales de esas marcas, ni se creó un proyecto
remoto. No se añadieron dependencias, fuentes remotas, rastreadores o servicios.

## Validación y límite de esta sesión

La compilación con esbuild, el análisis sintáctico del ensayo de navegador y
`git diff --check` finalizaron correctamente.

En el navegador integrado se revisó el acceso a 320, 390, 768 y 1440 px sin
desbordamiento horizontal. Se comprobaron visualmente la escena y los estados de
pausa, reanudación y movimiento reducido. La consola del navegador integrado no
mostró errores ni advertencias durante esta revisión. Se guardaron capturas sin
credenciales en la carpeta outputs/diseno-next del chat.

El ensayo automatizado se amplió para verificar píxeles de animación, pausa,
movimiento reducido y accesibilidad del acceso en tres tamaños adicionales.
Su ejecución **no pudo completarse**: Chrome recibió `ERR_NETWORK_ACCESS_DENIED`
al abrir el servidor temporal en loopback dentro de la sesión restringida.
Por tanto, no se atribuyen a esta revisión los resultados de 197 pruebas ni el
CI de la revisión anterior. El recorrido completo, incluyendo axe en las nueve
pantallas previstas, queda pendiente de ejecutarse en un entorno que lo permita.
La consola autenticada recibió estilos, pero no se inició sesión por el usuario
para inspeccionarla en esta sesión.
