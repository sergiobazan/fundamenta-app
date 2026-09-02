# Fundamenta

MVP de investigación fundamental para empresas peruanas. El repositorio contiene una
landing pública en Astro, una aplicación autenticada en Next.js, una API FastAPI y
PostgreSQL.

El alcance actual descarga estados financieros desde el servicio oficial de datos
abiertos de la SMV, conserva la respuesta cruda, filtra una empresa por su código RPJ,
normaliza un conjunto pequeño de conceptos y ejecuta una validación contable.

Los recorridos reales con Buenaventura y Minsur 2025 ya fueron ejecutados y verificados. Los
resultados se encuentran en [`docs/FASE_0_RESULTADOS.md`](docs/FASE_0_RESULTADOS.md).
La incorporación verificada del estado de resultados y flujo de efectivo está en
[`docs/FASE_1_RESULTADOS_Y_FLUJO.md`](docs/FASE_1_RESULTADOS_Y_FLUJO.md).
Las métricas y el contrato disponible antes de iniciar Next.js están en
[`docs/FASE_2_METRICAS_Y_CORTE_FRONTEND.md`](docs/FASE_2_METRICAS_Y_CORTE_FRONTEND.md).
La segunda empresa y el comparador homogéneo están documentados en
[`docs/FASE_5_MINSUR_Y_COMPARADOR.md`](docs/FASE_5_MINSUR_Y_COMPARADOR.md).
La línea de tiempo de eventos oficiales, su importación versionada y los límites
legales de esta etapa están en
[`docs/FASE_6_EVENTOS_OFICIALES.md`](docs/FASE_6_EVENTOS_OFICIALES.md).
La extracción, versionado y sincronización automática de notas auditadas están en
[`docs/FASE_7_NOTAS_FINANCIERAS.md`](docs/FASE_7_NOTAS_FINANCIERAS.md).
El arranque automático sobre una base vacía y el Blueprint de Render se explican en
[`docs/DESPLIEGUE_RENDER_DATOS_INICIALES.md`](docs/DESPLIEGUE_RENDER_DATOS_INICIALES.md).
El Blueprint actual usa únicamente una API y un PostgreSQL gratuitos. En ese nivel,
la base expira a los 30 días, los avatares subidos no son persistentes y la revisión
mensual de notas se ejecuta al primer despertar de la API durante el nuevo mes.

## Arquitectura

- `apps/landing`: sitio público Astro (puerto `4321`).
- `apps/web`: login, registro, panel y perfil en Next.js (puerto `3000`).
- `backend`: API FastAPI, autenticación y datos financieros (puerto `8000`).
- `notes-worker`: sincronización al arrancar y luego mensual, con cola en PostgreSQL.
- `infra/postgres/init`: esquema SQL y migraciones iniciales.

## Requisitos

- Docker con Docker Compose.
- Python 3.12 o superior.
- `uv` para instalar y ejecutar el backend.
- Node.js 22 o superior y npm.

## Inicio rápido

```bash
cp .env.example .env
docker compose up -d db
uv sync
npm install
```

Las seis migraciones y la carga inicial se ejecutan automáticamente al iniciar la API
o el worker. Para preparar la base explícitamente durante desarrollo también puedes
usar:

```bash
PYTHONPATH=backend uv run python -m app.bootstrap
```

El comando es idempotente: en una base vacía aplica las seis migraciones y carga
Buenaventura, Minsur, sus métricas, cuatro eventos y las notas; en una base completa
termina sin volver a descargar las fuentes.

En tres terminales:

```bash
PYTHONPATH=backend uv run uvicorn app.main:app --reload
npm run dev:landing
npm run dev:web
```

Abre:

- Landing: `http://localhost:4321`
- App: `http://localhost:3000/login`
- Directorio autenticado: `http://localhost:3000/empresas`
- Comparador autenticado: `http://localhost:3000/comparador`
- Eventos oficiales autenticados: `http://localhost:3000/eventos`
- API: `http://localhost:8000/docs`

### Usuario local de prueba

- Correo: `demo@fundamenta.pe`
- Contraseña: `Demo-Fundamenta-2026!`

Para recrearlo o cambiar la contraseña:

```bash
PYTHONPATH=backend uv run python -m app.cli seed-user \
  --email demo@fundamenta.pe \
  --password 'Demo-Fundamenta-2026!' \
  --name 'Usuario Demo'
```

## Configuración de la landing

Copia `apps/landing/.env.example` si quieres activar integraciones. Google Analytics
no se carga hasta que exista `PUBLIC_GA_MEASUREMENT_ID` y el visitante dé su
consentimiento. El mapa, indicaciones y schema local sólo se renderizan cuando se
configuran datos reales. Las reseñas se publican desde `apps/landing/src/config.ts`
y requieren `permissionRecorded: true`.

Variables principales:

- `PUBLIC_SITE_URL` y `PUBLIC_APP_URL`.
- `PUBLIC_CONTACT_EMAIL`.
- `PUBLIC_GA_MEASUREMENT_ID`.
- `PUBLIC_BUSINESS_ADDRESS`, `PUBLIC_MAP_EMBED_URL` y `PUBLIC_DIRECTIONS_URL`.

## Recorrido de datos

Para ingerir un nuevo estado financiero:

```bash
PYTHONPATH=backend uv run python -m app.cli smv-ingest \
  --company-rpj B20003 \
  --year 2025 \
  --period A \
  --scope C \
  --statement balance_sheet \
  --reported-scale thousands \
  --scale-source-url 'https://buenaventura.com/wp-content/uploads/2026/04/Integrated-annual-report-2025_Buenaventura_ENG.pdf'
```

El módulo `app` vive en `backend`, por lo que los comandos manuales deben ejecutarse
con esta variable cuando no se utiliza la configuración de pruebas:

```bash
PYTHONPATH=backend uv run python -m app.cli --help
```

Para calcular o actualizar las métricas del periodo ingerido:

```bash
PYTHONPATH=backend uv run python -m app.cli metrics-calculate \
  --company-rpj B20003 \
  --year 2025 \
  --period A \
  --scope consolidated
```

Para importar el conjunto curado inicial de hechos corporativos:

```bash
PYTHONPATH=backend uv run python -m app.cli events-import \
  --file backend/data/events/official_events_2026.json
```

Repetir el comando no duplica registros. Un contenido idéntico queda como
`unchanged`; una modificación conserva el anterior y crea una versión nueva.

Endpoints iniciales:

- `GET /health`
- `GET /companies`
- `GET /events?company_rpj=A20032&category=dividends&limit=50`
- `GET /companies/{smv_rpj}/filings`
- `GET /companies/{smv_rpj}/statements/{statement_type}?year=2025`
- El parámetro `normalized_only=true` limita la respuesta a conceptos normalizados.
- `GET /companies/{smv_rpj}/summary?year=2025`
- `GET /companies/{smv_rpj}/notes?year=2025&period=A&scope=consolidated`
- `GET /companies/{smv_rpj}/notes/{note_number}?year=2025&period=A&scope=consolidated`
- `GET /docs`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `PATCH /auth/profile`
- `POST /auth/profile/avatar`

## Fuente y alcance actual

- Fuente: Portal de Datos Abiertos de la SMV.
- Servicio: `WebServiceInfoFinanciera.asmx`.
- Empresas verificadas: Compañía de Minas Buenaventura S.A.A. (`B20003`) y
  Minsur S.A. (`A20032`).
- Corte común: tres estados anuales consolidados 2025, USD en miles.
- Resultado: 15 métricas por compañía y comparador con control de compatibilidad.
- Contexto corporativo inicial: cuatro eventos oficiales versionados de Buenaventura
  y Minsur, con fecha, resumen propio, enlace primario y huella SHA-256.
- Notas auditadas 2025: 36 para Buenaventura y 38 para Minsur, versionadas y
  referenciadas por página desde sus PDFs oficiales de la SMV.

## Sincronización automática de notas

`docker compose up -d` levanta `notes-worker`. El worker sincroniza una vez al arrancar
y luego el primer día de cada mes a las 06:00, hora de Lima. La deduplicación mensual,
los reintentos y el versionado se guardan en PostgreSQL; no hay comandos manuales en
el flujo normal de producción. El horario se puede cambiar con `NOTES_SYNC_DAY`,
`NOTES_SYNC_HOUR` y `NOTES_SYNC_TIMEZONE`.

## Restricción conocida

La respuesta del servicio identifica moneda, cuenta y montos, pero el diccionario
público consultado no declara de forma explícita la escala (`unidades`, `miles` o
`millones`). Por esa razón cada filing comienza con `reported_scale = 'unknown'`.
La escala sólo se cambia al contrastarla con un documento oficial y se conserva la
URL que la respalda. Para Buenaventura y Minsur 2025 consolidados, la documentación
financiera oficial confirma `US$(000)`, por lo que se registra `thousands`.

## Pruebas

```bash
uv run pytest
uv run ruff check backend
npm run check
npm run build
```

## Límites antes de producción

- Añadir rate limiting y monitoreo al login.
- Incorporar recuperación de contraseña y verificación de correo.
- Habilitar eliminación de cuenta y cerrar la revisión legal de privacidad.
- Configurar HTTPS, dominio, correo real, dirección real y Google Analytics.
- Conseguir y autorizar reseñas reales; el MVP no inventa testimonios.
- Reemplazar las credenciales demo en cualquier ambiente público.
