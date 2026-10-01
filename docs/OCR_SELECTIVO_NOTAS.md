# Próxima funcionalidad: OCR selectivo para notas financieras

Fecha de acuerdo: 14 de septiembre de 2026.
Estado: especificada; pendiente de implementación.
Prioridad: siguiente funcionalidad, antes de nuevas ampliaciones de cobertura.

## Objetivo y problema

Recuperar notas de PDFs escaneados, páginas con texto ilegible y documentos mixtos,
sin presentar extracciones incompletas como completas. La solución debe funcionar
por características del documento, sin reglas dependientes de una empresa.

OCR mejora la lectura; la segmentación necesita controles propios. En Nexa,
«16 Inventarios» era legible y una regla del extractor rechazaba el título: ese
fallo se corrige en la segmentación, no aplicando OCR indiscriminadamente.
Esta entrega amplía la [extracción versión 2](EXTRACCION_NOTAS_V2.md).

## Flujo funcional

1. Leer primero el texto nativo y conservar el PDF original con su huella.
2. Evaluar cada página: presencia de texto útil, caracteres ilegibles, orden de
   lectura y discrepancias con el índice o la secuencia de encabezados.
3. Seleccionar páginas candidatas y registrar el motivo. Una discrepancia con
   texto legible debe revisarse también como problema de segmentación. No activa
   por sí sola OCR de todo el documento.
4. Procesar las páginas seleccionadas mediante OCR y análisis de disposición:
   bloques, coordenadas, orden de lectura, encabezados y pies. Conservar ambas
   lecturas; elegir la utilizable mediante controles explícitos y registrar la decisión.
5. Reconstruir los límites de notas con el texto elegido y contrastarlos con el
   índice cuando exista. Detectar omisiones, duplicados, desorden y mezcla de notas.
6. Publicar únicamente las secciones con límites y evidencia suficientes. Si
   persiste ambigüedad, registrar `requiere revisión` con motivo concreto. Una
   extracción parcial no puede presentarse como completa ni como ausencia de riesgos.

Sin índice reconocible, indicar que la cobertura no se pudo contrastar de forma
independiente; detectar una secuencia continua no certifica que esté completa.
La confianza informada por el motor OCR tampoco equivale a validación documental.

## Procesamiento y trazabilidad

- Ejecutar el respaldo OCR en una etapa persistente separada, con progreso por
  páginas, límites configurables de tiempo, tamaño, recursos y reintentos.
- Guardar avances por página y reanudar tras interrupciones. Agotar el presupuesto
  debe producir un estado explícito; no reiniciar indefinidamente la etapa documental
  ni repetir estados financieros y métricas ya completados.
- Deduplicar por huella del PDF, página, motor y versión, configuración y versión
  del procesamiento. Reutilizar resultados compatibles y conservar versiones previas.
- Registrar texto original y OCR, método elegido, motor, versiones, página física
  del PDF, coordenadas de bloques, motivos, duraciones y controles ejecutados.
- Mantener citas al documento oficial y a la página correcta. La lectura OCR debe
  poder cotejarse con la imagen original; no se debe afirmar que una cita OCR coincide
  literalmente con el original sin esa comprobación.
- Las discrepancias entre lecturas no se resuelven inventando contenido. OCR no
  confirma por sí solo cifras, moneda, escala, columnas ni relaciones contables.

## Aplicación y administrador

La vista de notas mostrará si la extracción es parcial y qué cobertura pudo
verificarse. Los detalles técnicos se reservan al administrador.

El administrador podrá consultar el motivo del respaldo, páginas candidatas y
terminadas, método utilizado, cobertura, errores, intentos y duración. Permitirá
comparar las lecturas con el original y reintentar la etapa fallida respetando
permisos, límites y auditoría del panel existente.

## Criterios de aceptación

- PDF digital legible: no se ejecuta OCR innecesario ni se degradan títulos,
  límites, citas o contenido previamente validado.
- PDF mixto: se aplica OCR sólo a páginas que lo necesitan; una página seleccionada
  conserva su número físico y sus bloques tras combinar ambas rutas.
- PDF escaneado o con glifos corruptos: recupera las notas de los casos compatibles
  del corpus; los casos no recuperables quedan explícitamente en revisión.
- Índice con una nota ausente, encabezado duplicado o límite ambiguo: ninguna
  ejecución termina como extracción completa sin resolver la discrepancia.
- Caída, timeout y reintento: se reutilizan páginas finalizadas y no se duplican
  documentos, notas ni trabajo de etapas ya completadas.
- Cifras conflictivas o tablas ambiguas: no se publican como datos verificados por
  el mero hecho de obtener texto mediante OCR.
- La interfaz y el administrador reflejan el resultado real, incluidas revisiones
  pendientes; un fallo de OCR conserva los resultados anteriores válidos.

## Validación previa a habilitarlo

Preparar un corpus versionado con PDFs oficiales y anotaciones revisadas manualmente
de títulos, límites, páginas y pasajes de control. Incluir varias empresas y años,
PDFs digitales, escaneados, mixtos, glifos corruptos, tablas y ausencia de índice.
Nexa es un caso de regresión de segmentación, no la única prueba de aceptación.
Separar documentos de ajuste de documentos reservados para evaluación.

Medir cobertura de notas, exactitud de límites y citas, errores en pasajes y cifras,
falsos resultados completos, páginas enviadas a OCR, tiempo, memoria y coste por
documento. El conjunto de aceptación debe tener cero omisiones o mezclas conocidas
publicadas como completas y cero regresiones conocidas en las secciones revisadas.
Esto es un requisito del corpus evaluado, no una garantía universal.

Elegir el motor y fijar umbrales de selección, límites operativos y presupuesto a
partir de esa evaluación antes de habilitar la funcionalidad. Desplegar con activación
configurable y probar el flujo completo en local y en la infraestructura destino.
Cada fallo nuevo se añadirá al corpus de regresión.

## Fuera de alcance y decisiones pendientes

No incluye reconstrucción contable completa de tablas, corrección automática de
escalas financieras ni promesa de extracción perfecta para cualquier PDF.

Quedan por decidir el motor local o servicio, dependencias, almacenamiento de
artefactos, retención y recursos necesarios. La elección requiere medir calidad y
coste sobre el corpus; esta especificación no selecciona proveedor ni activa servicios.
