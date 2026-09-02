# Fase 7: notas a los estados financieros

## Resultado

El MVP incorpora las notas auditadas consolidadas de 2025 como un módulo separado de
los hechos corporativos. La sincronización no depende de un comando manual: un worker
se registra al arrancar, encola una ejecución idempotente y vuelve a comprobar las
fuentes el primer día de cada mes a las 06:00 (`America/Lima`).

Fuentes primarias verificadas:

- Buenaventura: `https://www.smv.gob.pe/ConsultasP8/temp/BVN%20CONSOLIDADO%202025.pdf`
- Minsur: `https://www.smv.gob.pe/ConsultasP8/temp/Informe%20Minsur%20Consolidado.pdf`

Carga real validada:

| Empresa | PDF | Notas | Notas prioritarias |
| --- | ---: | ---: | ---: |
| Buenaventura (`B20003`) | 136 páginas | 36 | 8 |
| Minsur (`A20032`) | 143 páginas | 38 | 11 |

## Flujo automático

1. `notes-worker` lee el catálogo curado de fuentes HTTPS.
2. Registra o actualiza las fuentes en PostgreSQL.
3. Crea como máximo un trabajo por fuente y mes mediante `dedupe_key`.
4. Descarga el PDF con límite de tiempo y tamaño.
5. Comprueba que sea PDF y que contenga los identificadores esperados.
6. Extrae títulos secuenciales, texto y secciones por página.
7. Calcula SHA-256. Si el archivo no cambió, no duplica el documento; si cambió,
   conserva la versión previa y crea una nueva.
8. Ante una falla, reintenta con espera exponencial y deja el error observable en la cola.

PostgreSQL funciona también como cola para este volumen inicial. No se incorporaron
Redis, Celery ni NestJS porque no aportan valor proporcional al MVP.

## Experiencia en la app

- Acceso desde el detalle de cada empresa sin alterar las tres tarjetas de estados.
- Listado con búsqueda por título o contenido, tema y filtro de notas prioritarias.
- Clasificación determinista: deuda, segmentos, activos/CAPEX, deterioro, provisiones,
  contingencias, partes relacionadas, estimaciones y hechos posteriores.
- Detalle dividido por páginas, con enlace a la página correspondiente del PDF.
- Documento, versión y huella SHA-256 visibles.
- El fallo del módulo de notas queda aislado y no impide abrir el detalle financiero.

Endpoints:

- `GET /companies/{smv_rpj}/notes?year=2025&period=A&scope=consolidated`
- `GET /companies/{smv_rpj}/notes/{note_number}?year=2025&period=A&scope=consolidated`

## Límites honestos

- La extracción conserva texto y referencia de página, pero no reconstruye la geometría
  de todas las tablas. Los importes deben verificarse en el PDF enlazado.
- La prioridad es una regla explicable basada en el título; no es una evaluación de
  materialidad ni una recomendación de inversión.
- El catálogo inicial contiene dos empresas. Sumar otra requiere registrar y validar su
  URL oficial e identificadores, no cambiar la arquitectura.
- No se usa IA en esta fase.

## Pendiente post-MVP: reconstrucción de tablas

**Estado:** pendiente priorizado; no bloquea el MVP actual.

La lectura lineal del PDF mezcla columnas y puede hacer que los cuadros contables sean
difíciles de interpretar. Hasta resolverlo, la interfaz mantendrá el texto extraído, la
advertencia visible y el enlace a la página exacta del documento oficial.

La mejora futura deberá:

- detectar regiones tabulares y reconstruir filas, columnas y encabezados;
- conservar moneda, escala, periodos, subtotales, notas al pie y coordenadas de origen;
- mostrar una tabla HTML accesible y permitir exportarla a CSV;
- asignar confianza a cada tabla y usar imagen o PDF como respaldo cuando la estructura
  no pueda recuperarse con seguridad;
- validar resultados contra un conjunto dorado de tablas de Buenaventura y Minsur;
- impedir que una extracción dudosa se presente como dato estructurado verificado.

Se considerará terminada cuando las tablas del conjunto dorado conserven correctamente
sus encabezados, etiquetas, importes y escala, y cada celda publicada mantenga referencia
a la página original.

## Operación

En una instalación nueva, `006_financial_notes.sql` se aplica automáticamente al crear
el volumen. En una base existente debe aplicarse una sola vez antes de levantar el
worker. Después, la operación normal es:

```bash
docker compose up -d
```

El argumento interno `--once` existe sólo para pruebas y diagnóstico; no forma parte
del flujo de producción.
