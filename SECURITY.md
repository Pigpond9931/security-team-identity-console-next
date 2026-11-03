# Seguridad y datos privados

No subas bases, respaldos, `.env`, secretos MFA, DPAPI, tokens, cookies, credenciales temporales ni gafetes utilizables. `.gitignore` excluye los principales archivos de ejecución, pero revisa siempre el contenido de cada commit.

Windows DPAPI requiere el contexto del usuario/equipo. Para respaldos utiliza `maintenance.py` y conserva las dependencias de recuperación. No prometas portabilidad automática entre máquinas.

La cámara IP requiere IPv4 privada y aprobación del destino exacto; un cambio de IP/puerto/ruta necesita nueva validación. Una IP no identifica de forma fiable a una persona.

Las pruebas publicadas usan datos ficticios. Las cadenas de contraseña constantes bajo `tests/` y el modo `ST_TEST_MODE=1` pertenecen exclusivamente a pruebas; no uses ese modo al publicar una instancia.

El prototipo no sustituye controles de sistema operativo ni una custodia de auditoría independiente. No se ha definido un plazo de retención. Comunica incidencias al propietario por un canal privado, sin adjuntar secretos a issues.
