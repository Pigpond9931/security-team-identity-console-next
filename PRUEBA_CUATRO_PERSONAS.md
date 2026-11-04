# Prueba de cuatro identidades autorizadas

El requisito de cuatro personas se aplica a F1, Centro de datos (DATA_CENTER_VAULT). No limita a cuatro usuarios del portal ni obliga a eliminar tarjetas de otras áreas. El aforo simultáneo es un ajuste independiente.

El operador Windows puede detener la aplicación, respaldar y ejecutar:

```
.venv\Scripts\python.exe maintenance.py project-access-four MATRICULA_1 MATRICULA_2 MATRICULA_3 MATRICULA_4
```

Deben ser cuatro personas diferentes, activas, desbloqueadas y con tarjetas registradas. El perfil asigna zona F1 y licencia LIC-DC-VAULT únicamente a esas cuatro identidades, fija cuatro plazas, revoca el permiso F1 de otras identidades y conserva sus demás zonas, roles, claves, MFA y tarjetas. No inventa UID ni autoriza una tarjeta desconocida. Mientras esté activo, la interfaz no amplía las plazas de F1 por encima de cuatro y los invitados no sirven como una quinta identidad de esa zona.

Cada acceso sigue exigiendo cuenta activa, desbloqueada, contraseña cambiada, MFA, términos y permiso/licencia actuales. Una cuenta elegida pero sin completar su alta seguirá recibiendo denegación.

Ensayo: presentar las cuatro tarjetas en F1 y comprobar permitido; presentar otra tarjeta registrada y una desconocida y comprobar denegado; registrar salida y revisar el evento. Después probar las otras áreas para demostrar que conservan sus permisos. El perfil no acciona una cerradura ni un LED físico.
