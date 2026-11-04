# Condiciones de uso, seguridad y aviso de privacidad del proyecto SECURITY TEAM

Versión v1.1 | 3 de noviembre de 2026

Versión v1.1, publicada el 3 de noviembre de 2026. Este documento explica las condiciones de participación, el tratamiento de datos y los límites de la práctica. Lee el contenido completo y plantea tus dudas antes de aceptar. La aceptación en la aplicación registra fecha, versión y vía; la constancia de tablet identifica su propia versión.

## 1. Naturaleza y alcance de la práctica

SECURITY TEAM es un proyecto académico de gestión de identidades, control de acceso y visualización de cámaras. Estas condiciones se aplican a estudiantes, visitantes, operadores y administradores que utilicen el prototipo. Las zonas representan el escenario de la práctica; una autorización en pantalla no sustituye las reglas de ingreso de la universidad ni acciona una cerradura física. Este documento describe el funcionamiento del equipo del proyecto y no se presenta como aviso institucional de la universidad ni como certificación de cumplimiento legal.

## 2. Responsables operativos y atención presencial

La coordinación técnica corresponde al responsable del proyecto, David Alonzo Jerez Alvarado. La supervisión de privacidad corresponde al DPO del proyecto, Ángel Gabriel Reyes Quiñones. Ambos atienden presencialmente durante la práctica; solicita su identificación al operador de recepción. No se publica un correo de contacto en este aviso, por decisión del responsable. Si se requiere seguimiento fuera de la sesión, acuerda presencialmente con ellos un medio de respuesta y conserva una referencia de tu solicitud. El rol académico de DPO no acredita por sí mismo una designación institucional.

## 3. Datos que se utilizan y límites de la recolección

Según la función utilizada, se tratan nombre, matrícula o referencia de visitante, área, rol, permisos, licencias internas, UID de tarjeta RFID, vigencia del gafete, estado de cuenta y registros de autenticación y de acceso con fecha, zona, operador y resultado. Para visitantes pueden registrarse organización, motivo, anfitrión y vigencia. Las cámaras aportan imágenes en vivo. La constancia de tablet añade datos de participación, fecha del dispositivo, folio, aceptación y trazo de firma. No se solicitan contraseñas de otras plataformas, documentos oficiales, información financiera, datos de salud ni otros datos sensibles innecesarios. No escribas secretos ni datos de terceros en campos libres.

## 4. Finalidades y uso de las evidencias

Los datos se utilizan para identificar participantes, administrar cuentas y permisos, validar credenciales, registrar entradas y salidas, gestionar visitantes, supervisar el escenario y revisar incidentes o errores de la práctica. También permiten demostrar el funcionamiento del proyecto al profesor. Las evidencias para reportes deben limitarse a lo necesario: utiliza cuentas ficticias, anonimiza o cubre nombres, matrículas, UID y rostros cuando no sean indispensables. No se autoriza publicar listas de personas, gafetes, firmas, credenciales o imágenes identificables en repositorios públicos, redes sociales o grupos ajenos a la actividad. Una difusión adicional requiere evaluación y autorización específica; esta aceptación no la incluye.

## 5. Cuenta personal, contraseña y autenticador

Cada participante debe utilizar su propia cuenta, mantener una contraseña personal distinta de la de otros servicios y proteger su autenticador y códigos de recuperación. Una contraseña temporal solo sirve para el proceso autorizado de configuración o restablecimiento; no concede una sesión completa por sí sola. No compartas contraseñas, QR de configuración MFA ni códigos de recuperación con operadores o compañeros. El personal de soporte puede iniciar un restablecimiento autorizado, pero no debe pedir que le reveles tus secretos. Cierra tu sesión al dejar un dispositivo compartido y evita que el navegador conserve tus credenciales en una tablet de recepción.

## 6. Tarjetas RFID y gafetes QR

Las credenciales de acceso son personales e intransferibles. La tarjeta RFID de 125 kHz aporta un identificador que la aplicación vincula a una persona; los permisos residen en el sistema y no se graban en la tarjeta mediante esta integración. El gafete QR tiene vigencia y puede quedar invalidado por cambios de seguridad. Una fotografía o copia del QR puede ser reutilizada durante su vigencia; no la publiques y reporta su pérdida. La posesión de una tarjeta o imagen no garantiza la identidad del portador: el operador debe comprobar su correspondencia con la persona en la práctica. Las credenciales desconocidas, vencidas o revocadas no deben admitirse por insistencia del portador.

## 7. Roles, zonas y decisiones de acceso

El sistema aplica controles por rol y alcance, además del estado de cuenta, zona autorizada y licencias internas requeridas. Una tarjeta registrada no concede acceso a todas las áreas. La terminal consulta las condiciones actuales en cada lectura; los permisos pueden revocarse durante la sesión. Los operadores deben seleccionar la zona y el movimiento correctos y comprobar el resultado mostrado. No deben prestar sesiones administrativas, elevar privilegios sin autorización, alterar registros ni utilizar una salida asistida para simular un ingreso autorizado. Una denegación puede deberse a permisos, vigencia, configuración pendiente o estado de la cuenta; debe revisarse con el responsable.

## 8. Cámaras en vivo y respeto al entorno

La consola muestra vídeo en vivo de los dispositivos que sus titulares vinculan y mantienen activos. La aplicación no ofrece grabación persistente, captura de audio, reconocimiento facial ni consulta de vídeo histórico; procesa cuadros temporales en memoria. Los permisos del navegador para cámara son necesarios en el dispositivo emisor. Orienta las cámaras al escenario acordado y evita baños, espacios privados, documentos, pantallas de contraseñas o personas ajenas. No realices capturas o grabaciones externas de personas sin una autorización específica. Al terminar, detén la transmisión y retira la vinculación que ya no se necesite. La duración autorizada no garantiza continuidad si falla la red, la batería o el navegador.

## 9. Visitantes y responsabilidad del anfitrión

Solo los operadores autorizados pueden crear y gestionar pases de invitado dentro de su alcance. Deben explicar la finalidad de la visita, seleccionar la zona necesaria y la vigencia adecuada, y comprobar a quién entregan el pase. Un invitado debe conocer las condiciones antes de aceptar. La opción de aceptación presencial únicamente se utiliza cuando el titular acaba de leerlas y aceptarlas y el operador puede atestiguarlo; no debe marcarse por comodidad. La existencia de un pase no elimina restricciones de áreas que excluyen visitantes. Revoca el pase si se emitió por error, terminó la visita o se perdió su control.

## 10. Almacenamiento, conexión pública y terceros

Las cuentas, permisos, visitantes, aceptaciones y eventos se almacenan en SQLite en la laptop del proyecto, con archivos de configuración y claves locales separados. Los administradores pueden generar respaldos o exportaciones para operación y evidencia; deben custodiar esas copias. Cloudflare Tunnel transporta la conexión pública por HTTPS hacia la laptop; no sustituye al servidor, al respaldo ni al archivo de auditoría independiente. La infraestructura del proveedor y la red de la escuela intervienen en el transporte y pueden tratar datos técnicos conforme a sus propias condiciones. La aplicación no incluye funciones de publicidad ni venta de datos. El enlace temporal puede cambiar y requiere que la laptop y la red sigan disponibles.

## 11. Medidas de seguridad y límites técnicos

La aplicación utiliza contraseñas almacenadas mediante hash, secretos del autenticador cifrados, sesiones controladas, validaciones de permisos en el servidor y bitácoras de acciones. Estas medidas reducen riesgos, pero no garantizan seguridad absoluta ni significan que toda la base, los respaldos o las copias descargadas estén cifrados. El control de la laptop anfitriona sigue siendo una responsabilidad crítica. No existe actualmente un receptor independiente configurado para custodiar toda la auditoría fuera del equipo. Queda prohibido aprovechar errores, intentar adivinar credenciales, copiar la base o divulgar claves; reporta cualquier hallazgo al responsable y al DPO.

## 12. Confidencialidad de operadores y administradores

Quien tenga acceso a perfiles, registros, cámaras, firmas o exportaciones debe consultarlos solo para sus tareas y evitar que terceros los observen. No descargues una base completa o un listado de personas para una evidencia que pueda resolverse con datos ficticios o un resultado anonimizado. Protege la pantalla de recepción, bloquea los equipos sin supervisión y entrega las constancias únicamente al custodio autorizado o a su titular. La posibilidad técnica de ver o exportar información no constituye permiso para difundirla. Las operaciones administrativas deben contar con una justificación del proyecto y quedar sujetas a revisión.

## 13. Conservación y eliminación manual

El plazo acordado para los datos y constancias identificables del proyecto es de hasta 30 días naturales después de la última práctica. El responsable y el DPO deben registrar la fecha de esa última sesión y calcular el vencimiento; mientras esa fecha no se haya confirmado, no debe inventarse una fecha de eliminación. Al terminar el plazo deben revisar y eliminar de forma controlada la información identificable que custodian, incluidas exportaciones, firmas descargadas y respaldos del proyecto. No hay borrado automático ni un botón de eliminación masiva de auditoría. La ejecución requiere intervención administrativa y comprobación de las copias existentes; no debe confundirse desactivar una cuenta con borrar sus datos.

## 14. Consultas, correcciones y solicitudes sobre los datos

Puedes acudir presencialmente al responsable o al DPO para conocer qué datos tuyos se tratan, pedir correcciones, plantear oposición o solicitar cancelación o retiro de una constancia. Explica qué información afecta tu solicitud y proporciona únicamente los datos mínimos para identificarte y recibir seguimiento. No entregues contraseñas ni códigos MFA como prueba. El equipo debe dejar constancia de la recepción, verificar la identidad y revisar el alcance y la respuesta; la aplicación no ofrece actualmente un trámite automatizado de estas solicitudes ni garantiza un borrado inmediato desde el panel. Si el asunto corresponde a un tratamiento institucional de la universidad, deberá canalizarse a la instancia institucional competente. La aceptación no implica renunciar a derechos.

## 15. Incidentes, errores y retiro de credenciales

Reporta de inmediato la pérdida de tarjeta o teléfono, un QR divulgado, un ingreso ajeno, una firma guardada en el lugar equivocado o un dato mostrado por error. Identifica la cuenta, credencial o evento afectado sin reenviar secretos. El equipo podrá bloquear o revocar el acceso correspondiente, retirar una transmisión y revisar la bitácora; conservará el mínimo de información necesario para explicar la actuación dentro del plazo acordado. Un bloqueo por intentos fallidos debe resolverse mediante verificación del titular, no probando contraseñas repetidamente. No se prometen disponibilidad permanente, recuperación de vídeo que no fue grabado ni resultados técnicos que el prototipo no puede producir.

## 16. Firma en tablet y custodia de constancias

La pantalla de firma permite leer las condiciones, completar datos, marcar una aceptación expresa y dibujar una firma. El trazo no se somete a análisis biométrico ni se verifica criptográficamente la identidad. La herramienta prepara una imagen o impresión con el contenido y la versión aceptados, fecha del dispositivo y folio; no proporciona un sello de tiempo certificado. No envía automáticamente las firmas al servidor ni actualiza la aceptación de la cuenta. La copia queda donde el operador la guarde y debe tratarse con la misma confidencialidad y plazo de conservación. Verifica su guardado antes de preparar a la siguiente persona y retira de pantalla los datos del participante anterior.

## 17. Aceptación, cambios y efectos del documento

La aceptación debe ser libre, informada y expresa: la casilla no debe aparecer marcada previamente ni debe firmarse por otra persona. Si no comprendes o no aceptas una condición, solicita una explicación o una alternativa de participación al responsable y al profesor antes de usar el sistema; el prototipo puede impedir activar funciones que requieren aceptación. Los cambios materiales se publican con una versión nueva y se solicita una aceptación nueva cuando corresponda. Las constancias anteriores conservan su texto y versión y no deben reescribirse como si hubieran aceptado condiciones posteriores. No se incluyen autorizaciones generales de difusión, renuncias de derechos ni exenciones ilimitadas de responsabilidad.

Documento académico de condiciones de uso y aviso de privacidad del proyecto. La aceptación electrónica simple o el trazo en pantalla no equivalen a una firma electrónica avanzada, no sustituyen el aviso institucional aplicable y no acreditan cumplimiento legal certificado.
