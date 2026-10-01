# Ampliación del administrador: usuarios y actividad

Fecha: 30 de septiembre de 2026. Estado: implementada en código y migrada en local; despliegue en producción pendiente.
Complementa el [panel de análisis existente](PANEL_ADMIN_ANALISIS.md) y las secciones
16 y 17 de la especificación del producto. Se implementará dentro de `/admin`, con
secciones Resumen, Análisis, Usuarios y Auditoría.

## Objetivo

Permitir al responsable de Fundamenta conocer qué cuentas se han creado, qué
acciones registradas realizan y qué resultados obtienen, además de gestionar acceso
y permisos. Las acciones deben atribuirse con evidencia, sin inferir uso inexistente
a partir de solicitudes, sesiones o tareas del worker.

## Resumen y directorio de usuarios

- Mostrar cuentas totales, altas del periodo, cuentas habilitadas/suspendidas y
  usuarios con actividad registrada en el periodo seleccionado.
- Mostrar solicitudes de análisis e informes IA, errores y actividad reciente.
  Separar solicitudes de usuarios de ejecuciones e intentos automáticos del worker.
- Listar nombre, correo, fecha de alta, rol, estado, último inicio de sesión exitoso,
  última actividad registrada y número de solicitudes. Un dato desconocido aparece
  como «sin registro»; no como cero ni como «nunca».
- Buscar por nombre o correo y filtrar por rol, estado, alta y periodo de actividad.
  Paginar y ordenar en servidor; mostrar zona horaria de Lima en la interfaz.
- Definir cada contador y su ventana temporal. «Usuario con actividad» requiere al
  menos un evento humano registrado en la ventana; no implica conexión en tiempo real.

## Detalle e historial por usuario

La ficha tendrá datos básicos, estado, rol y una cronología paginada. Cada entrada
identifica fecha, acción, resultado y recurso relacionado cuando corresponda.
Permite filtrar por tipo, periodo, empresa y resultado, y abrir los trabajos o
informes relacionados para inspeccionar evidencia, errores y reintentos.

Registrar desde backend:

- Registro de cuenta, inicio de sesión exitoso y cierre de sesión.
- Solicitud de análisis, incluida reutilización de un trabajo existente.
- Solicitud o reintento manual de informe de notas, incluido resultado reutilizado.
- Cambios de perfil y acciones administrativas que afecten a la cuenta.

Instrumentar explícitamente en la aplicación:

- Empresa consultada, cambio de periodo o alcance, fuente abierta y comparación
  abierta o solicitada. No registrar cada consulta automática de progreso como uso.
- Eventos de búsqueda con filtros necesarios para entender el uso, evitando guardar
  consultas libres completas por defecto.

Los resultados automáticos se relacionan con la solicitud y su solicitante, pero
se etiquetan como actividad del sistema. Un informe completado no demuestra que
su solicitante lo haya leído. Un enlace abierto no demuestra que se haya leído el PDF.
Los eventos de navegación son señales de uso; no certifican acciones fuera de la app.

## Control de cuentas

- Suspender o reactivar con motivo obligatorio y resultado visible.
- La suspensión revoca sesiones existentes y bloquea login y solicitudes protegidas
  en backend; no basta con ocultar opciones en frontend. Conserva historial y trabajos
  ya creados; no cancela automáticamente ejecuciones compartidas por otros usuarios.
- Revocar todas las sesiones sin suspender la cuenta; el usuario podrá iniciar sesión
  de nuevo si está habilitado.
- Conceder o retirar rol administrador con motivo. Impedir suspender o retirar el
  rol del último administrador activo, incluso con solicitudes concurrentes.
- Confirmar cambios de acceso mostrando la cuenta y la consecuencia concreta.
  Si falla la auditoría, revertir la operación. No incluir eliminación de usuarios,
  lectura de contraseñas, suplantación ni establecimiento de claves desde este panel.

## Registro y seguridad

Extender las cuentas con estado y datos de suspensión, reutilizar el rol existente
y conservar sesiones revocadas conforme a la política de retención.
Crear eventos estructurados con identificador, fecha UTC, actor humano o sistema,
usuario afectado si aplica, acción, resultado, recurso e identificador de correlación.
Los metadatos se limitan mediante un contrato por tipo de evento.

Persistir solicitudes y cambios de acceso con su evento en la misma transacción.
El registro de navegación puede ser asíncrono y limitado para no afectar el recorrido
del usuario; su fallo debe ser observable y no puede inventar eventos posteriores.
Deduplicar envíos repetidos por identificador de evento, sin fusionar acciones distintas.

Reutilizar la auditoría administrativa para actor, destinatario, motivo y valores
anteriores/nuevos. Registrar también consultas de fichas o historiales por administradores
para auditar el acceso a información de cuentas. El historial no se modifica desde la UI.
Comprobar permisos en cada endpoint y evitar respuestas administrativas en cachés
compartidas. Ninguna cuenta normal accede a fichas ni eventos de otros usuarios.

No guardar contraseñas, tokens, API keys, prompts, razonamiento del modelo, documentos
completos ni texto de preguntas sensibles como metadatos de actividad. IP y agente de
usuario no forman parte del seguimiento de uso inicial. La política de privacidad
debe describir los eventos; definir retención y acceso antes de habilitarlos en producción.

## Historial disponible y migración

`app_users`, `analysis_jobs.requested_by`, `notes_reports.requested_by` y la auditoría
existente permiten recuperar altas, solicitudes persistidas y acciones administrativas
que efectivamente estén guardadas. Presentarlas como registros históricos de esas
fuentes, con referencias estables, sin duplicarlas con los eventos nuevos.

No se reconstruyen visitas, búsquedas, cierres de sesión ni solicitudes reutilizadas
anteriores sin evidencia. Una sesión persistida no sustituye un evento de login auditado.
Mostrar desde qué fecha se registra cada clase de actividad. Los contadores anteriores
a esa fecha explicitan cobertura limitada.

## Criterios de aceptación

1. Sin sesión se devuelve 401 y una cuenta normal obtiene 403 en todas las rutas
   administrativas, incluidas operaciones y acceso directo a otra ficha.
2. Altas y filtros reflejan la base, con paginación estable; periodos y contadores
   tienen la misma definición en resumen, listado e historial.
3. Un registro, login, solicitud nueva, solicitud reutilizada y reintento producen
   eventos atribuibles, sin duplicados por polling ni por entrega repetida.
4. Suspender invalida sesiones ya abiertas y bloquea login; reactivar no resucita las
   sesiones revocadas. Revocar sesiones permite un nuevo login válido.
5. Cambios de rol se aplican a sesiones existentes en la siguiente petición y no
   permiten dejar el sistema sin administradores activos bajo concurrencia.
6. Fallo de auditoría revierte cambios de acceso; actor, motivo y destinatario quedan
   registrados cuando la operación se confirma.
7. Historial y contadores separan acciones humanas, reutilización y ejecución
   automática; los periodos sin instrumentación se muestran como cobertura desconocida.
8. Las respuestas y metadatos no contienen secretos ni contenido sensible excluido.

## Entregas previstas

Primero: migración, directorio, ficha e historial de solicitudes existentes, explicando
su cobertura. Después: suspensión, sesiones, permisos y auditoría transaccional.
Finalmente: eventos de uso, resumen y validación integrada con cuentas normales y
administradoras. La reconstrucción del historial disponible no sustituye la
instrumentación futura. Las tres entregas están implementadas. La instrumentación recoge apertura del buscador, no el texto de consultas libres.


## Implementación y activación

- Migraciones 021 y 022: estado de cuenta, eventos tipados y vista de historial con
  referencias a las solicitudes antiguas. Las consultas de fichas se auditan sin
  incorporarse al feed de uso, para no alterar su paginación al abrirlo.
- Backend: `user_admin.py`, `activity.py` y `activity_api.py`. Reutiliza la auditoría
  existente y el control de sesión en cada petición. El CLI de roles comparte la
  protección del último administrador con las operaciones web.
- Frontend: pestañas Resumen, Análisis, Usuarios y Auditoría en `/admin`, ficha,
  filtros, confirmación de acceso, motivos y enlaces a los trabajos e informes.
- Navegación: eventos limitados a 60 por cuenta/minuto, deduplicados por UUID. Los
  recursos se validan y los rechazos quedan visibles en los logs HTTP. No se registra
  el polling de progreso. La señal de apertura de fuente no certifica lectura.
- Política de privacidad de preproducción actualizada con el registro de actividad
  y el acceso administrativo. En este MVP los registros operativos y de auditoría se
  conservan con la cuenta y sus solicitudes; no hay purga automática. Los plazos
  legales de conservación y el procedimiento de eliminación siguen requiriendo
  revisión antes de producción, como indica la política existente.

En local se aplicaron las migraciones mediante `app.migrations`. Para activar el
código en un proceso que no usa recarga automática, reiniciar backend y frontend.
Entrar con una cuenta administradora y abrir `/admin` → Usuarios. Producción requiere
el despliegue de ambos servicios y las migraciones; no se ha desplegado desde esta tarea.

La verificación usa esquemas temporales PostgreSQL y cubre bloqueo de sesiones,
reactivación sin resucitar sesiones, login, permisos, protección concurrente del último
administrador, reversión si falla auditoría, historial antiguo, deduplicación y límites.

Resultado de la validación del 30 de septiembre de 2026: 167 pruebas aprobadas con
PostgreSQL aislado, Ruff sin errores, compilación de landing y aplicación aprobada y
comprobación TypeScript final aprobada. El navegador local mostró la pantalla de login;
la revisión visual de las pestañas con una sesión administradora sigue pendiente.
