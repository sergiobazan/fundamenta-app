# Extracción de notas: versión 2

El extractor anterior encontraba 15 notas en el informe individual 2025 de Nexa
Perú, aunque su índice contiene 33. El filtro de títulos sin punto rechazaba
«16 Inventarios» y su contenido terminaba dentro de la nota 15. Contar las notas
detectadas no era una validación suficiente de cobertura.

## Cambio

Cuando existe un índice numerado reconocible, se contrastan números y títulos
con los encabezados del cuerpo, incluidos títulos de una palabra y títulos
partidos entre líneas. Se exige que cada entrada aparezca una vez y en orden.
Una discrepancia detiene la publicación de esa extracción con un motivo de revisión.

Sin índice reconocible se conserva la detección por secuencia. Si hay un salto,
se omite también la última nota cuyo final no puede asegurarse. La interfaz
explicita que la cobertura no fue contrastada con un índice. Se eliminan
encabezados repetidos al inicio de los fragmentos y se excluyen anexos reconocidos.

La migración 020 guarda `extractor_version` y `extraction_quality`. El mismo PDF
puede producir una versión nueva con el extractor 2, conservando la anterior.
El bloqueo por fuente impide crear versiones duplicadas con trabajadores concurrentes.

## Validación del 14 de septiembre de 2026

Se usaron PDFs reales y texto extraído mediante el lector del proyecto:

| Documento | Notas | Alcance de la comprobación |
| --- | ---: | --- |
| Nexa Perú individual 2025 | 33 | 33 entradas del índice contrastadas con el cuerpo; separación de notas 15/16; última nota termina en página PDF 63 |
| Buenaventura consolidado 2025 | 36 | Cantidad y títulos sin regresión respecto a la extracción anterior |
| Minsur consolidado 2025 | 38 | Cantidad y títulos sin regresión |
| Minsur consolidado 2024 | 37 | Cantidad y títulos sin regresión |
| Volcan consolidado 2025 | 38 | Cantidad y títulos sin regresión |
| Volcan consolidado 2024 | 37 | Cantidad y títulos sin regresión |

`backend/tests/fixtures/notes_corpus_v2.json` registra hashes de los PDFs,
recuentos, método y límites de páginas observados. Es evidencia reproducible
con los mismos documentos, no una transcripción auditada de todo su contenido.
Las pruebas sintéticas cubren títulos partidos, duplicados, omisiones, orden,
subnotas, tablas numéricas, límites en una misma página y anexos. Las pruebas de
PostgreSQL usan esquemas aislados para comprobar versionado y concurrencia.

No se pudieron descargar tres fuentes adicionales de la SMV por respuestas HTTP
403; no se consideran validadas.

## Límites y activación

No se garantiza extracción perfecta de PDFs arbitrarios. Faltan una ruta de OCR
y análisis de disposición para páginas escaneadas o glifos ilegibles, reconstrucción
y validación de tablas, y un corpus revisado manualmente de más formatos.
El reconocimiento del índice requiere entradas numeradas con referencia de página;
no interpreta todas las variantes de índices partidos o maquetados en columnas.

Antes de usar esta versión, ejecutar las migraciones mediante el mecanismo habitual
del proyecto y reiniciar el backend. Los resultados persistidos no se corrigen al
abrir la página: hay que reprocesar las notas. Esta validación no despliega cambios
en producción ni resuelve la verificación de escala del flujo de efectivo de Nexa,
que es un problema distinto de correspondencia de etiquetas.
