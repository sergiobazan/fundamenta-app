# Despliegue del backend y datos iniciales en Render

El backend está preparado para arrancar sobre un Render Postgres completamente vacío.
No es necesario abrir una consola ni ejecutar comandos SQL después del despliegue.

## Qué ocurre al arrancar

La API ejecuta `app.runtime` antes de iniciar su proceso normal. Ese módulo:

1. toma un bloqueo de PostgreSQL para que sólo una instancia inicialice la base;
2. descubre y aplica en orden las doce migraciones de `infra/postgres/init`;
3. registra cada migración y su SHA-256 en `schema_migrations`;
4. comprueba si el corte inicial ya está completo;
5. si falta información, descarga desde la SMV los tres tipos de estado financiero
   consolidado 2025 para Buenaventura, Minsur, Volcan y Poderosa;
6. calcula las 15 métricas de cada empresa;
7. importa los cuatro eventos oficiales curados;
8. descarga, extrae y versiona las notas financieras 2025 y 2024 de ocho PDF oficiales;
9. indexa cada fragmento de las notas por empresa, documento, ejercicio y página;
10. genera resúmenes extractivos con citas y estados de evidencia insuficiente;
11. empareja las notas de ambos ejercicios y fija la evidencia utilizada en la
    comparación narrativa;
12. valida cantidades mínimas, métricas disponibles y controles contables.

Si Render reinicia, despierta o redespliega el servicio, no se duplican filings,
métricas, eventos ni documentos de notas. En cada nuevo mes el arranque de la API
encola y procesa una revisión de los PDF; por eso la actualización ocurre al primer
despertar mensual del servicio gratuito.

## Recursos incluidos en el Blueprint

El archivo `render.yaml` declara:

- `fundamenta-postgres`: PostgreSQL 17 sin acceso público;
- `fundamenta-api`: API FastAPI gratuita con health check en `/health`.

Los dos recursos usan el plan `free`, por lo que el Blueprint no requiere un worker
ni un disco de pago. Esta variante es apropiada para validar el MVP, no para una
operación permanente, y tiene estas restricciones:

- PostgreSQL gratuito expira 30 días después de crearse, tiene 1 GB y no incluye
  backups;
- la API duerme después de 15 minutos sin tráfico y puede tardar cerca de un minuto
  en responder al siguiente acceso;
- el filesystem es efímero: un avatar personalizado desaparece al dormir o
  redesplegar; el avatar predeterminado sigue funcionando;
- la revisión mensual de notas es oportunista: se ejecuta cuando la API vuelve a
  arrancar durante el nuevo mes, no en una hora exacta.

## Crear los recursos

1. Sube el repositorio a GitHub, GitLab o Bitbucket.
2. En Render selecciona **New > Blueprint**.
3. Conecta el repositorio y deja que Render lea `render.yaml`.
4. Revisa región y planes y confirma la creación.
5. Espera a que termine la carga inicial; la primera ejecución tarda más porque
   consulta la SMV y procesa ocho PDF completos.
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
URLs públicas de avatares. No agregues `DATABASE_URL` a Vercel: sólo la API debe
conectarse a PostgreSQL.

## Operación y recuperación

- Una migración ya aplicada no vuelve a ejecutarse. Si su archivo cambia, el
  arranque se detiene para evitar una base con historial ambiguo; una modificación
  de esquema posterior debe agregarse como una migración nueva y consecutiva.
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
