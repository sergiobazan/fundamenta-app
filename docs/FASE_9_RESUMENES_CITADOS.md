# Fase 9: resúmenes citados

## Resultado

Cada detalle de nota financiera incorpora una lectura rápida verificable. Esta primera
versión no usa NVIDIA ni otro modelo de IA: selecciona texto narrativo del documento
mediante reglas deterministas y lo presenta sin reescribirlo. Así se obtiene utilidad
inmediata sin introducir alucinaciones, coste externo ni una API key.

Sobre las 74 notas actuales se generaron:

- 74 resúmenes versionados;
- 154 hechos observados con cita válida;
- 40 resúmenes de confianza alta;
- 12 de confianza media;
- 10 parciales de confianza baja;
- 12 abstenciones por evidencia narrativa insuficiente;
- 0 interpretaciones automáticas.

## Persistencia y auditoría

La migración `infra/postgres/init/008_cited_summaries.sql` agrega:

- `cited_summaries`: nota, método, generador, versión, estado, confianza, motivo,
  fecha de corte, SHA-256 de entrada y fecha de generación;
- `cited_summary_items`: sección, orden, texto y fragmento fuente cuando el elemento
  representa un hecho observado.

Los hechos requieren una referencia a `source_fragments` por restricción de base de
datos. Las interpretaciones y los datos faltantes no pueden aparentar tener una cita
documental. Una nueva versión del PDF crea nuevas notas, fragmentos y resúmenes sin
sobrescribir la versión anterior.

## Generación automática

`app.cited_summaries`:

1. descarta filas tabulares, texto demasiado corto, bloques numéricos y frases que
   parezcan recomendaciones de inversión;
2. puntúa oraciones mediante términos explicables según el tema de la nota;
3. elimina selecciones redundantes;
4. conserva hasta tres hechos con página y fragmento exactos;
5. calcula confianza según la cantidad y diversidad de la evidencia;
6. se abstiene cuando no encuentra narrativa suficientemente legible.

El importador genera el resumen dentro de la misma transacción que almacena cada nota.
Además, el arranque ejecuta un backfill idempotente para documentos existentes. No hay
un comando manual en el flujo de despliegue.

## Contrato de la API

La respuesta existente:

```text
GET /companies/{smv_rpj}/notes/{note_number}?year=2025&period=A&scope=consolidated
```

agrega `summary` con:

- `status`: generado, parcial o evidencia insuficiente;
- `confidence` y `confidence_reason`;
- `information_cutoff`;
- método, generador, versión y SHA-256 de entrada;
- `observed_facts`, cada uno con documento, versión, página, URL y fragmento;
- `interpretations`, vacío en esta fase;
- `missing_data`, con los límites detectados.

## Experiencia de uso

El detalle de la nota separa visualmente:

1. **Hechos observados:** extractos con una cita inmediata al PDF.
2. **Interpretación:** muestra expresamente que no fue generada.
3. **Datos faltantes:** falta de período comparable, tablas no reconstruidas o texto
   narrativo insuficiente.

También muestra confianza, justificación, fecha de corte y versión del método. El
resumen aparece después de la nota completa, como cierre de la lectura y sin ocultar
la evidencia original.

## Límites honestos

- La confianza mide disponibilidad y legibilidad de evidencia, no certeza económica.
- La selección extractiva reduce lectura, pero no sustituye el análisis profesional.
- Los textos tabulares se omiten cuando no pueden presentarse con seguridad; el PDF
  sigue siendo la fuente para importes y columnas.
- No se infiere materialidad, causalidad, riesgo futuro ni conveniencia de inversión.
- Un futuro modelo de NVIDIA podrá redactar explicaciones, pero deberá reutilizar estas
  citas, guardar versión de modelo y prompt, y superar evaluaciones de fidelidad y
  abstención antes de publicarse.

## Verificación

- 44 pruebas de backend aprobadas.
- 74 de 74 notas con un registro de resumen.
- 154 de 154 hechos con referencia válida a un fragmento.
- 0 interpretaciones generadas.
- Ruff, TypeScript, Astro y build de Next.js aprobados.
- Estados de confianza media, alta y abstención revisados en Chrome.
- Sin desbordamiento horizontal a 390 px.
- Auditoría móvil de Chrome: 100 en accesibilidad, buenas prácticas, SEO y
  navegación automatizada.

## Continuación

La comparación narrativa se incorporó en la Fase 10 después de añadir las notas
auditadas 2024 de ambas empresas. Los resúmenes de esta fase siguen siendo la capa de
evidencia fijada por la comparación.
