# Panel interno: operación de análisis

Ruta: `/admin`. Visible en el menú únicamente para cuentas con `is_admin=true`.
El backend comprueba la sesión y el permiso en cada solicitud. El registro público y
el perfil no permiten asignar este rol.

## Alcance implementado

- Bandeja de trabajos de análisis por empresa, estado y página; contadores generales.
- Detalle con periodo, alcance, solicitante, intentos totales, actividad, errores y
  tiempo desde el inicio del último intento y de cada etapa.
- Historial persistente de cambios en trabajos y etapas, incluyendo actividad documental.
  La migración conserva una captura del estado previo; no reconstruye intentos antiguos.
- Reintento manual de trabajos `failed` o `review_required`, con motivo obligatorio.
  Conserva las etapas completadas, reinicia las pendientes y concede un nuevo presupuesto
  de intentos automáticos. El contador de intentos anteriores no se borra.
- Rechazo de trabajos activos, completados o sustituidos por otro del mismo periodo y
  alcance. Usa el mismo bloqueo de las solicitudes normales y el índice único de activos.
- Auditoría transaccional del actor, motivo, estado anterior y etapa de reanudación.
  Si no se puede registrar la auditoría, el reintento tampoco se confirma.

Este bloque cubre la operación de `analysis_jobs`. La revisión/aprobación de periodos,
cuentas no mapeadas, alta de fuentes, republicación y moderación de respuestas de IA de
la sección 16 de la especificación requieren flujos adicionales. Los informes IA tienen
su propia cola y no se reintentan desde esta bandeja.

La siguiente ampliación administrativa está definida en
[Usuarios y actividad](PANEL_ADMIN_USUARIOS_ACTIVIDAD.md): directorio de cuentas,
historial de uso, suspensión, revocación de sesiones y gestión auditada de permisos.
Está implementada en `/admin`, reutiliza sus controles de acceso y añade las
pestañas Resumen, Usuarios y Auditoría.

## Despliegue y primer administrador

1. Desplegar el backend con la migración `019_analysis_admin.sql`. El arranque normal
   aplica las migraciones antes de servir solicitudes. Desplegar también `apps/web`.
2. Confirmar que la cuenta destinataria ya existe. En el entorno del backend, ejecutar
   desde la raíz del proyecto (en Render, `/app`):

```bash
PYTHONPATH=backend .venv/bin/python -m app.admin grant \
  --email demo@fundamenta.pe \
  --reason 'Habilitación inicial del responsable de operación'
```

3. Iniciar sesión con esa cuenta y abrir `/admin`. Si la sesión ya estaba abierta,
   actualizar la página: el permiso se consulta en la base en cada petición.

El comando anterior está preparado para la cuenta indicada por el usuario; no se ha
ejecutado contra producción. No crea usuarios ni modifica contraseñas. Para retirar
el permiso, usar `revoke` con el mismo correo y un motivo; la acción también se audita.

## Verificación

```bash
.venv/bin/pytest -q
.venv/bin/ruff check backend/app/admin.py backend/tests/test_admin.py backend/tests/test_admin_db.py
npm run check --workspace=@fundamenta/web
npm run build --workspace=@fundamenta/web
```

Las pruebas transaccionales requieren `ADMIN_TEST_DATABASE_URL`, que debe apuntar a
una base de pruebas, nunca a producción. Crean un esquema temporal, aplican las
migraciones y lo eliminan al terminar. Comprueban conservación de etapas, presupuesto,
historial, concurrencia, rechazo de trabajos antiguos y reversión si falla la auditoría.
Sin esa variable se omiten explícitamente.

Antes de dar por validado el despliegue: confirmar 401 sin sesión, 403 con usuario
normal, abrir el detalle del trabajo fallido de Nexa con el administrador, registrar el
motivo y reintentar. Verificar que estados y métricas conservan sus resultados, aparece
la acción en auditoría y las notas quedan disponibles al terminar la etapa documental.
