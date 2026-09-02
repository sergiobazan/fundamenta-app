# Despliegue del backend y datos iniciales en Render

El backend está preparado para arrancar sobre un Render Postgres completamente vacío.
No es necesario abrir una consola ni ejecutar comandos SQL después del despliegue.

## Qué ocurre al arrancar

Tanto la API como el worker ejecutan `app.runtime` antes de iniciar su proceso normal.
Ese módulo:

1. toma un bloqueo de PostgreSQL para que sólo una instancia inicialice la base;
2. descubre y aplica en orden las seis migraciones de `infra/postgres/init`;
3. registra cada migración y su SHA-256 en `schema_migrations`;
4. comprueba si el corte inicial ya está completo;
5. si falta información, descarga los tres estados financieros consolidados 2025 de
   la SMV y almacena Buenaventura y Minsur;
6. calcula las 15 métricas de cada empresa;
7. importa los cuatro eventos oficiales curados;
8. descarga, extrae y versiona las notas financieras de los dos PDF oficiales;
9. valida cantidades mínimas, métricas disponibles y controles contables.

Si dos servicios arrancan a la vez, el segundo espera el bloqueo y después detecta
que la inicialización ya terminó. Si Render reinicia o redespliega un servicio, no se
duplican filings, métricas, eventos ni documentos de notas.

## Recursos incluidos en el Blueprint

El archivo `render.yaml` declara:

- `fundamenta-postgres`: PostgreSQL 17 sin acceso público;
- `fundamenta-api`: API FastAPI con health check en `/health`;
- `fundamenta-notes-worker`: sincronización al arrancar y mensual;
- un disco persistente para los avatares subidos a la API.

Los planes configurados son de pago porque el worker permanente y el disco de
avatares no están cubiertos adecuadamente por un despliegue gratuito. Se pueden
cambiar en el Dashboard antes de confirmar la creación, entendiendo que quitar el
disco hará que los avatares se pierdan en cada despliegue.

## Crear los recursos

1. Sube el repositorio a GitHub, GitLab o Bitbucket.
2. En Render selecciona **New > Blueprint**.
3. Conecta el repositorio y deja que Render lea `render.yaml`.
4. Revisa región y planes y confirma la creación.
5. Espera a que termine la carga inicial; la primera ejecución tarda más porque
   consulta la SMV y procesa dos PDF completos.
6. Verifica `https://<servicio-api>.onrender.com/health` y luego `/companies`.

En los logs debe aparecer `Inicialización de datos: completed` la primera vez y
`Inicialización de datos: already_complete` en reinicios posteriores.

## Variables para Vercel

En el proyecto Next.js configura:

```text
API_URL=https://<servicio-api>.onrender.com
NEXT_PUBLIC_API_URL=https://<servicio-api>.onrender.com
NEXT_PUBLIC_LANDING_URL=https://<dominio-landing>
```

`API_URL` se usa en el servidor de Next.js. `NEXT_PUBLIC_API_URL` se usa para las
URLs públicas de avatares. No agregues `DATABASE_URL` a Vercel: sólo la API y el
worker deben conectarse a PostgreSQL.

## Operación y recuperación

- Una migración ya aplicada no vuelve a ejecutarse. Si su archivo cambia, el
  arranque se detiene para evitar una base con historial ambiguo; una modificación
  de esquema posterior debe agregarse como `007_*.sql`.
- Una caída durante una migración revierte esa migración completa.
- Una caída durante la carga de datos puede dejar una parte válida ya guardada. El
  siguiente arranque vuelve a comprobar el conjunto y completa lo faltante mediante
  operaciones idempotentes.
- Para desactivar únicamente la carga inicial y conservar las migraciones usa
  `BOOTSTRAP_ON_START=false`.

Los comandos siguientes sirven para diagnóstico local, pero no son parte del flujo
normal de producción:

```bash
PYTHONPATH=backend uv run python -m app.migrations
PYTHONPATH=backend uv run python -m app.bootstrap
```
