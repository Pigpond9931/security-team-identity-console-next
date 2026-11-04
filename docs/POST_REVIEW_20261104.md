# Revisión posterior · 4 de noviembre de 2026

Este documento actualiza los informes de la primera entrega local. La confirmación personal de GitHub se completó: los tres repositorios personales son privados, y la integración Codex tiene acceso a Next. GitHub CLI fue autorizado expresamente por el propietario y guarda la sesión en el llavero de Windows. La subida y CI se verifican en el recibo de cierre; no se considera completado el avance externo faltante.

## Correcciones adicionales

- La CLI de respaldo ejecuta la copia bajo el bloqueo antes de inicializar o migrar la base. Una prueba con esquema antiguo y clave raw confirma que el origen queda byte por byte intacto.
- Antes de cambiar permisos recursivamente se exige una carpeta nueva/vacía o el marcador `.identity-console-store.json` con aplicación/formato reconocidos. Se admite el bloqueo inicial propio. Una carpeta ajena poblada se rechaza antes de DACL y SQLite, también desde publicadores, configurador y supervisor. El marcador identifica una carpeta preparada; no es una credencial ni protección frente al usuario Windows que controla sus archivos.
- Las carpetas antiguas sin marcador no se adoptan automáticamente. El respaldo por CLI puede leerlas sin inicializarlas para conservar la posibilidad de una migración futura revisada. No se adoptó ni migró la instalación activa.
- El respaldo conserva el marcador y exige la clave QR en almacenes Next o si hay evidencia de pases emitidos. El manifiesto señala su presencia. Solo una base realmente nueva puede crear una clave QR; al reabrir o consultar una existente, perderla provoca un error y no se genera otra. La API responde 503 con un mensaje para contactar al operador.
- La restauración de prueba verifica además un token firmado antes del respaldo. No basta con comparar la existencia de archivos.

## Evidencia

La suite actual contiene 185 pruebas en 25 grupos: todas pasan, sin omisiones. El caso de junction ya se ejecutó con permisos completos de Windows. Se probó asimismo una carpeta centinela ajena y se conservaron sus bytes, mtime y DACL al rechazarla. Los recorridos anteriores de Chrome/Chromium se conservan como evidencia de su etapa; el recorrido Chromium de cierre se repite sobre esta custodia actualizada. No se probaron dispositivos ni datos de producción.

Sigue faltando el ZIP externo cuyo SHA-256 informado es `55fe85bb4930b849f2c6be2be723943afe775888207caee583063de5ba772d79`; no se recuperó el commit `8c667079ae43a3046a4dd8c4fab83bfa2db5b24c`. La revisión del portal continúa limitada porque el navegador rechazó su descarga. No se intentó obtenerlo por otra vía.
