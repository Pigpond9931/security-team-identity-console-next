# Importación RFID de ejemplo

El script import_rfid_reference.py se conserva como referencia explícita; no se ejecuta al iniciar. Utiliza identidades y tarjetas ficticias y necesita una base de demostración que las contenga. No importa las credenciales de la laptop original.

| Identidad ficticia | Función | Zona |
|---|---|---|
| 9900001 | DPO de ejemplo | Las cuatro zonas |
| 9900002 | Responsable de Access Control | DATA_CENTER_VAULT |
| 9900004 | Responsable de Identity Management | SERVER_ROOM |
| 9900003 | Responsable de Monitoring | MONITORING_CCTV |
| 9900005 | Responsable de IAM | GENERAL_ACCESS |

La asignación de UID debe verificarse con el titular y el lector real. Un ejemplo no autoriza a reasignar tarjetas existentes ni a eliminar factores, bloqueo o términos. El importador revisa conflictos y conserva auditoría. Los permisos de IM e IAM son independientes y no se incluyen horarios de demostración.
