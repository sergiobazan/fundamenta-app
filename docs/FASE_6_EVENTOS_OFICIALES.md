# Fase 6: eventos corporativos oficiales

## Corte alcanzado

Se añadió la primera capa de contexto corporativo del MVP. No es todavía un
agregador de prensa ni usa inteligencia artificial: trabaja con un conjunto curado
de comunicaciones oficiales, conserva trazabilidad y evita copiar el contenido
completo de los documentos.

## Modelo y versionado

La migración `infra/postgres/init/005_corporate_events.sql` crea
`corporate_events` con:

- empresa, proveedor e identificador externo;
- categoría, título, resumen y fechas de publicación/efecto;
- URL y nombre del documento oficial;
- huella SHA-256, fecha de consulta y metadatos JSON;
- número de versión y marca del registro vigente.

El par proveedor/identificador sólo puede tener una versión vigente. El importador
no modifica silenciosamente un evento: si cambia el contenido, desactiva la versión
anterior y crea la siguiente. Una carga idéntica es idempotente.

## Datos iniciales

El archivo `backend/data/events/official_events_2026.json` incorpora cuatro
eventos verificables:

- Buenaventura: Investor Day 2026 comunicado ante la SMV.
- Buenaventura: resultados operativos del segundo trimestre de 2026.
- Minsur: acuerdo de distribución de US$350 millones en dividendos.
- Minsur: presentación anual auditada consolidada 2025.

El registro almacena metadatos y un resumen redactado para Fundamenta. El contenido
íntegro permanece en el sitio oficial enlazado.

## API y frontend

Endpoint:

```text
GET /events?company_rpj=A20032&category=dividends&limit=50
```

Las categorías permitidas son `dividends`, `management`, `meetings`, `debt`,
`operations`, `litigation`, `production` y `other`.

La ruta autenticada `/eventos` incluye:

- filtros por empresa y categoría;
- línea de tiempo ordenada por publicación;
- fechas de publicación y efecto;
- versión y prefijo de la huella del registro;
- enlace a la empresa y al documento oficial.

La ficha de cada empresa muestra además sus tres eventos recientes.

## Validación ejecutada

- 19 pruebas backend aprobadas.
- Ruff sin observaciones.
- TypeScript sin errores.
- Build de producción Next.js aprobado, incluida `/eventos`.
- Importación inicial: 4 importados, 0 duplicados.
- Segunda importación: 4 sin cambios, 0 duplicados.
- Filtro API Minsur + Dividendos: un resultado correcto.
- Chrome DevTools MCP en escritorio y móvil a 390 px aprobado.
- Consola Chrome sin errores, advertencias ni issues.
- Ficha de empresa sin desbordamiento horizontal ni imágenes rotas.

## Límites pendientes

- La carga es manual y curada; aún no existe sincronización periódica con la SMV.
- La cobertura no pretende ser exhaustiva y sólo incluye dos empresas.
- No hay noticias de prensa. Esa etapa debe usar RSS, API o una licencia que permita
  el uso previsto, guardar sólo metadatos/resumen permitido y enlazar al original.
- No hay clasificación ni resumen generado por IA. La futura integración NVIDIA
  debe operar detrás de una interfaz de proveedor y no sustituir la fuente primaria.
- No hay alertas, notificaciones, búsqueda de texto completo ni evaluación de
  impacto sobre la tesis de inversión.
- Los eventos y métricas aportan evidencia, pero no constituyen recomendación de
  compra o venta.
