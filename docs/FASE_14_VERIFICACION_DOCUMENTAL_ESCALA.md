# Fase 14: verificación documental de escala

El flujo bajo demanda intenta verificar la escala de cada estado anual después de
publicar las métricas iniciales. Conserva `Escala no verificada` cuando no hay prueba
suficiente. No deriva la escala de otras empresas, estados o periodos.

## Evidencia requerida

- PDF servido desde una fuente oficial registrada; redirecciones restringidas a
  dominios aprobados y descarga con límites de tamaño y tiempo.
- Nombre legal, ejercicio principal y alcance compatibles en la portada.
- Encabezado del estado con moneda y escala explícitas.
- Al menos tres cuentas con etiqueta e importes actual y comparativo coincidentes
  con la SMV. Importes iguales sin etiqueta no son evidencia suficiente.
- Guardado por estado de URL, SHA-256, página, encabezado y líneas contrastadas.
- Comprobación de que los insumos no cambiaron mientras se descargaba el PDF.

Los importes originales no se multiplican: se actualiza su metadato de escala y se
recalculan las métricas. El frontend existente utiliza esa escala para presentarlas.
La reutilización de escala durante reingestión exige el mismo estado y hash de la
respuesta estructurada. Se eliminó la suposición de `thousands` por existir notas.

## Descubrimiento y límites

El conector general `smv_documents.py` consulta primero el formulario público de
información financiera de la SMV. Obtiene dinámicamente el identificador interno
por coincidencia única de razón social y consulta el ejercicio anual y alcance del
análisis. Conserva la sesión y los campos ocultos del formulario; no adivina IDs ni
nombres de PDF. Recoge los enlaces documentales oficiales de la tabla de resultados,
excluye XBRL y limita la cantidad de candidatos. Los anexos aún deben pasar los controles
de identidad, ejercicio, alcance e importes: el formulario puede devolver anexos de
alcances diferentes en un mismo envío.

Como alternativa, `document_origins` registra páginas oficiales de documentos y, cuando es necesario,
PDF oficiales directos. El extractor de enlaces es común a todas las empresas;
no construye nombres de archivos ni adivina dominios. Las fuentes de notas existentes
también son candidatas. Se priorizan enlaces financieros, con límites de candidatos.

Se registraron los índices de Cerro Verde y Alicorp. Para Alicorp hay además una URL
oficial SMV como alternativa; ambos proveedores pueden rechazar descargas automatizadas.
La consulta general SMV permite descubrir documentos sin registrar una URL por empresa.
Los dominios corporativos alternativos siguen requiriendo revisión operativa. Un error
de SMV no impide intentar las fuentes oficiales registradas y queda en el resultado
de verificación. No se consultan agregadores ni dominios inferidos de búsquedas abiertas.

Prueba de lectura del conector: encontró dos anexos para Shougang, dos para Casa Grande
y cinco para Nexa Perú, consultando 2025 individual. Encontrar anexos no garantiza validar
su escala o extraer todas sus notas. Por ejemplo, la identidad estricta actual rechaza
la abreviatura de Casa Grande; los formatos de tablas también pueden requerir soporte.
El cambio se ejecuta en la etapa documental de nuevos análisis o reintentos; no modifica
automáticamente trabajos terminados ni asigna escalas por migración.

La publicación de notas es independiente de la verificación de escala. Si el PDF
procede de una fuente oficial, supera identidad, ejercicio y alcance, y sus notas
pueden extraerse, se registra como fuente y continúa hacia notas y resúmenes. No es
necesario contrastar los tres estados para publicar el texto documental. Esto no
verifica cifras ni modifica escalas: las métricas mantienen sus advertencias hasta
contar con evidencia propia. Se conserva la primera fuente válida, priorizando SMV.
La extracción excluye índices con listas de títulos y referencias de página para
no confundirlos con el cuerpo de las notas (caso Alicorp: 44 notas en 142 páginas).
La extracción
admite encabezados individuales y detecta saltos en la secuencia. Se corrigió la nota
sin punto de jerarquía de instrumentos financieros. Una comparación histórica requiere
además el documento del ejercicio anterior; no se crea a partir del comparativo de cifras.

## Actualización de datos existentes

Migración 015: orígenes y evidencia por estado.
Migración 016: orígenes adicionales y reintento único de etapas documentales para
análisis anuales con escala desconocida y fuente registrada. Respeta trabajos activos
y conserva estados y métricas terminados. El worker actual procesa los reintentos.

## Comprobación

Prueba de lectura sobre Cerro Verde 2025: identidad y alcance individual compatibles;
balance en página 9 (23 coincidencias), resultados en página 10 (4 coincidencias) y
flujo en página 13 (3 coincidencias), todos con `US$(000)`. El extractor obtiene 24 notas.
Las pruebas unitarias cubren moneda, escala ambigua, identidad, año principal, alcance,
etiquetas, columnas comparativas y dominios no autorizados.

Reprocesamiento local confirmado: Cerro Verde finalizó con los tres estados en
`thousands`, 24 notas importadas y trabajo documental completado. Alicorp conservó
los tres estados en `unknown`: su índice redirigió a un control anti-bot y el PDF
alternativo SMV respondió 403. No se alteraron sus escalas sin evidencia.

## Escala declarada en las notas

El verificador admite también una política general de presentación explícita en
«Bases de preparación» o «Moneda de presentación». Además de identidad, ejercicio
y alcance, exige tres cuentas económicas distintas contrastadas en tablas con años
y moneda/escala explícitos, procedentes de al menos dos estados. Cada estado que se
actualice debe tener al menos una coincidencia propia. Así, la evidencia procede de
una declaración que cubre todos los estados y no de heredar la escala de otro estado.

Las tablas pueden tener dos o tres ejercicios, con posiciones identificadas por año.
Se admiten equivalencias contables limitadas y totales sin etiqueta sólo en la primera
tabla de una nota con título exacto y separador de total. Se excluyen cifras por acción
y se rechazan políticas contradictorias, excepciones específicas y unidades diferentes.
La salvedad genérica «excepto donde se indique de otro modo» se conserva en la evidencia;
cada tabla contrastada debe declarar la misma unidad que la política.

La migración 017 registra el PDF oficial SMV de Pacasmayo y reencola su etapa documental
2025 sin asignar ninguna escala por SQL. Prueba de lectura: declaración en página 3,
cuentas de balance en páginas 21, 25 y 29, resultados en página 38 y efectivo de cierre
del flujo en página 21. Esta extensión de verificación es independiente del descubridor SMV.

Reprocesamiento local confirmado de Pacasmayo: trabajo completado, tres estados en
`thousands`, cuatro métricas monetarias recalculadas y 28 notas importadas. Las pruebas
automatizadas incluyen años invertidos, tablas de tres ejercicios, monedas diferentes,
contradicciones de escala, magnitudes incompatibles y ausencia de evidencia por estado.
