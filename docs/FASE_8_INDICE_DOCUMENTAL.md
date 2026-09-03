# Fase 8: índice de fragmentos documentales

## Resultado

El MVP incorpora una búsqueda transversal sobre el contenido extraído de las notas
financieras. No utiliza IA ni genera interpretaciones: recupera texto existente y
mantiene la trazabilidad necesaria para contrastarlo con el documento oficial.

La migración `infra/postgres/init/007_source_fragments.sql` produjo un backfill local
de 319 fragmentos para las 74 notas auditadas de Buenaventura y Minsur 2025. La
consulta de verificación `deuda financiera` encontró 14 fragmentos.

## Modelo e indexación

`source_fragments` conserva por cada sección:

- empresa;
- documento y versión;
- nota financiera;
- ejercicio, período y alcance, mediante el documento relacionado;
- número de página y orden dentro de la nota;
- título y texto extraído;
- vector de búsqueda de PostgreSQL configurado para español.

El título de la nota tiene más peso que el cuerpo. El índice GIN permite buscar por
palabras y formas lingüísticas relacionadas sin recorrer todos los textos. También
existe una coincidencia literal controlada para términos que el diccionario de texto
completo no reconozca.

La migración rellena el índice a partir de `note_sections`. A partir de entonces,
`app.notes.store_note_document` escribe los fragmentos en la misma transacción que
crea una nueva versión del documento. Por ello el worker mensual no necesita un
comando adicional ni puede dejar una nota nueva sin indexar.

## API

El endpoint es:

```text
GET /search/fragments?q=deuda+financiera&company_rpj=A20032&topic=debt&year=2025
```

Parámetros:

- `q`: obligatorio, entre 2 y 100 caracteres;
- `company_rpj`: filtro opcional por empresa;
- `topic`: filtro opcional por categoría de nota;
- `year`: filtro opcional por ejercicio;
- `limit`: entre 1 y 50, con 20 por defecto;
- `offset`: desplazamiento para paginación posterior.

Cada resultado devuelve el extracto relevante, empresa, nota, tema, ejercicio,
alcance, página, versión, huella SHA-256 y URL oficial. Sólo se consultan versiones
vigentes de los documentos.

## Interfaz

La ruta autenticada `/buscar` incluye:

- consulta por concepto, riesgo o cuenta;
- filtros por empresa, tema y ejercicio;
- total y orden por relevancia;
- contexto legible alrededor de cada coincidencia;
- enlace a la nota completa dentro de Fundamenta;
- enlace a la página exacta del PDF oficial;
- advertencia explícita de que el texto fue extraído automáticamente.

Se agregó el acceso “Buscar” a las navegaciones de escritorio y móvil. La vista fue
revisada en Chrome a tamaño de escritorio y en un viewport móvil de 390 × 844; los
enlaces internos funcionan y no hubo errores de consola.

## Verificación

- 41 pruebas de backend aprobadas.
- `ruff check backend` aprobado.
- comprobación de TypeScript y Astro aprobada.
- builds de Astro y Next.js aprobados.
- migración 007 aplicada sobre PostgreSQL local.
- endpoint probado contra datos reales.
- auditoría móvil de Chrome: 100 en accesibilidad, buenas prácticas, SEO y
  navegación automatizada.

## Límites deliberados

- La calidad del extracto depende de la estructura del PDF original.
- Las tablas complejas continúan remitiendo al PDF; su reconstrucción accesible y CSV
  permanece como pendiente post-MVP.
- Los resúmenes citados se incorporaron posteriormente en la Fase 9 utilizando este
  índice como capa de evidencia.
- No existen respuestas conversacionales ni recomendaciones de inversión en esta fase.
