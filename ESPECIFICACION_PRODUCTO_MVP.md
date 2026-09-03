# Especificación de producto y MVP

## Copiloto de análisis fundamental para empresas peruanas

**Estado:** Borrador inicial listo para desarrollo  
**Versión:** 1.0  
**Mercado inicial:** Perú  
**Sector piloto:** Empresas mineras no financieras supervisadas por la SMV  
**Tipo de producto:** Aplicación web de investigación financiera  

---

## 1. Resumen ejecutivo

El producto reducirá el tiempo necesario para analizar la información financiera pública de empresas peruanas. Recopilará datos estructurados, estados financieros, notas, informes de auditoría y hechos de importancia; calculará indicadores de forma reproducible y empleará inteligencia artificial únicamente para explicar, resumir y relacionar información con sus fuentes.

El producto no decidirá si una persona debe comprar o vender una acción. Su función será convertir documentación dispersa y difícil de comparar en evidencia ordenada que ayude al usuario a realizar su propio análisis.

### Propuesta de valor

> Entiende en minutos qué cambió en una empresa peruana, por qué puede importar y de dónde proviene cada dato.

### Hipótesis principal

Un inversionista o analista pagará por una herramienta que reduzca significativamente el tiempo de revisar reportes financieros, siempre que los datos sean exactos, comparables y verificables hasta el documento original.

---

## 2. Problema

La información necesaria para analizar empresas peruanas se encuentra distribuida entre estados financieros, notas, memorias, informes de gerencia, hechos de importancia y fuentes sectoriales. Aunque parte de la información está estructurada, el usuario todavía debe:

1. Localizar los documentos correctos.
2. Distinguir estados consolidados de separados.
3. Identificar unidades, moneda, periodo y acumulación de cifras.
4. Trasladar datos a hojas de cálculo.
5. Calcular indicadores.
6. Comparar periodos y empresas.
7. Leer notas extensas para detectar riesgos y cambios.
8. Relacionar los resultados con eventos corporativos y sectoriales.

Este trabajo es lento, repetitivo y susceptible a errores manuales.

---

## 3. Usuarios objetivo

### Usuario principal del MVP

Inversionista individual o analista junior que:

- Investiga empresas listadas o supervisadas en Perú.
- Comprende conceptos financieros básicos.
- Actualmente usa PDFs, Excel y sitios de la SMV o BVL.
- Analiza entre 2 y 15 empresas al mes.
- Necesita ahorrar tiempo sin perder trazabilidad.

### Usuarios secundarios

- Estudiantes y docentes de economía, finanzas y contabilidad.
- Analistas de sociedades agentes de bolsa.
- Consultoras financieras y oficinas de inversión.
- Periodistas económicos.

### No es usuario objetivo del MVP

- Personas que buscan señales de trading intradía.
- Usuarios que esperan rentabilidad garantizada.
- Gestores que necesitan precios en tiempo real o ejecución de órdenes.
- Empresas que requieren cobertura global desde el primer lanzamiento.

---

## 4. Objetivos del MVP

El MVP debe demostrar que la plataforma puede:

1. Ingerir información oficial de un universo pequeño y definido.
2. Normalizar estados financieros de manera confiable.
3. Calcular indicadores sin delegar operaciones matemáticas a un modelo de lenguaje.
4. Explicar los cambios más importantes entre periodos.
5. Resumir notas y eventos con citas verificables.
6. Reducir el tiempo de análisis de una empresa al menos en 60 % durante las pruebas con usuarios.
7. Conseguir evidencia de disposición a pagar.

### Indicadores de éxito

- Exactitud numérica validada igual o superior al 99.5 % en campos publicados.
- El 100 % de las cifras visibles tiene fuente, periodo, moneda y unidad.
- El 100 % de las afirmaciones generadas por IA incluye citas o se marca explícitamente como interpretación.
- Al menos 15 usuarios completan una prueba del producto.
- Al menos 10 usuarios comparan el flujo contra su proceso actual.
- Al menos 5 usuarios aceptan pagar o firman una carta de intención.
- El tiempo mediano para obtener una primera evaluación disminuye al menos 60 %.

---

## 5. Alcance cerrado del MVP

### 5.1 Universo inicial

El MVP cubrirá ocho empresas mineras no financieras:

1. Compañía de Minas Buenaventura S.A.A.
2. Minsur S.A.
3. Volcan Compañía Minera S.A.A.
4. Sociedad Minera Cerro Verde S.A.A.
5. Compañía Minera Poderosa S.A.A.
6. Nexa Resources Perú S.A.A.
7. Sociedad Minera El Brocal S.A.A.
8. Shougang Hierro Perú S.A.A.

La denominación y los identificadores oficiales deberán confirmarse durante la primera exploración de datos. Una empresa sólo ingresará al MVP si dispone de información suficiente y comparable en las fuentes autorizadas.

### 5.2 Cobertura temporal

- Últimos cinco ejercicios anuales completos.
- Últimos ocho trimestres disponibles.
- Información anual auditada e intermedia cuando corresponda.
- Se conservarán versiones anteriores si una empresa presenta cifras rectificadas.

### 5.3 Documentos incluidos

- Estado de situación financiera.
- Estado de resultados.
- Estado de flujos de efectivo.
- Estado de cambios en el patrimonio, si está estructurado de forma confiable.
- Notas a los estados financieros.
- Dictamen u opinión del auditor.
- Análisis y discusión de la gerencia, cuando esté disponible.
- Hechos de importancia.
- Memoria anual sólo para consultas y contexto puntual.

### 5.4 Funciones incluidas

#### Directorio de empresas

- Listado de las ocho empresas.
- Búsqueda por nombre o símbolo.
- Último periodo disponible.
- Fecha de la última actualización.
- Indicador de estado de los datos: verificado, parcial o pendiente.

#### Panel de empresa

- Resumen de la empresa.
- Evolución de ingresos, utilidad, activos, patrimonio, deuda y caja.
- Evolución de flujo operativo, inversión y flujo de caja libre.
- Variación interanual y frente al periodo anterior comparable.
- Principales fortalezas, deterioros y preguntas abiertas.
- Enlace a todos los documentos originales utilizados.

#### Indicadores financieros

- Crecimiento de ingresos.
- Margen operativo, cuando los componentes estén disponibles.
- Margen neto.
- ROA.
- ROE.
- Razón corriente.
- Deuda sobre patrimonio.
- Deuda neta.
- Flujo de caja operativo.
- Capex, sólo cuando pueda identificarse consistentemente.
- Flujo de caja libre, con fórmula visible.

Si un componente no puede determinarse con seguridad, el indicador se mostrará como no disponible. No se estimará silenciosamente.

#### Comparador

- Comparar hasta tres empresas.
- Utilizar siempre el mismo periodo, moneda normalizada y tipo de estado.
- Mostrar diferencias de definición o disponibilidad.
- Impedir comparaciones incompatibles.

#### Cambios entre periodos

- Identificar aumentos y disminuciones relevantes.
- Destacar cambios en deuda, caja, márgenes, flujo y patrimonio.
- Comparar las notas del periodo actual con las del anterior.
- Separar hechos observados de interpretaciones generadas.

#### Documentos y citas

- Visor o enlace al documento original.
- Referencia a documento, fecha y página.
- Fragmento utilizado como evidencia.
- Distinción entre documento vigente y rectificado.

#### Hechos de importancia

- Eventos oficiales asociados con cada empresa.
- Clasificación básica: dividendos, gerencia, juntas, deuda, operaciones, litigios, producción u otros.
- Fecha de publicación y fecha efectiva, si son distintas.
- Resumen breve con enlace a la fuente.

#### Asistente de consulta

El usuario podrá realizar preguntas como:

- ¿Cómo evolucionó la deuda de esta empresa?
- ¿Qué explica la caída del margen?
- ¿Qué riesgos aparecen en las notas?
- ¿Qué cambió frente al reporte anterior?
- Compara el flujo de caja de estas dos empresas.

El asistente responderá exclusivamente con información incorporada y citable. Si no existe evidencia suficiente, deberá decirlo.

---

## 6. Fuera del alcance del MVP

Quedan expresamente excluidos:

- Recomendaciones de comprar, mantener o vender.
- Puntuaciones opacas de atractivo de una acción.
- Asesoría personalizada según patrimonio o perfil de riesgo.
- Predicción de precios o rentabilidades.
- Ejecución de operaciones bursátiles.
- Integración con cuentas de corredores.
- Precios en tiempo real.
- Valorización completa por múltiplos o flujo de caja descontado.
- Optimización de portafolios.
- Cobertura de bancos, aseguradoras, AFP y fondos.
- Cobertura fuera de Perú.
- Aplicaciones móviles nativas.
- Red social, comentarios o contenido creado por usuarios.
- Facturación y autoservicio de suscripciones.
- Rastreo indiscriminado de medios periodísticos.
- Uso de contenido de pago sin licencia.
- Extracción masiva de sitios que prohíban automatización.

Estas funciones sólo podrán incorporarse en fases posteriores mediante una decisión explícita de producto, revisión de datos y, cuando corresponda, revisión legal.

---

## 7. Fuentes de información y prioridad

### Prioridad 1: datos oficiales estructurados

- Portal de Datos Abiertos de la SMV.
- Información financiera estructurada de la SMV.
- Archivos XBRL, JSON, Excel o formatos equivalentes autorizados.

### Prioridad 2: documentos regulatorios oficiales

- Estados financieros y notas presentados a la SMV.
- Informes de auditoría.
- Memorias e informes de gerencia.
- Hechos de importancia.
- Información publicada oficialmente por la BVL.

### Prioridad 3: contexto sectorial primario

- Ministerio de Energía y Minas.
- Banco Central de Reserva del Perú.
- Instituto Nacional de Estadística e Informática.
- Ministerio de Economía y Finanzas.
- Reguladores y organismos públicos pertinentes.
- Fuentes oficiales de precios de minerales cuya licencia permita el uso.

### Prioridad 4: noticias periodísticas

Sólo se incorporarán mediante API, RSS, enlace o licencia que permita el uso previsto. El sistema almacenará metadatos y fragmentos permitidos, no copias completas de artículos protegidos.

### Restricciones de adquisición

- Respetar términos de servicio, licencias, `robots.txt` y límites de frecuencia.
- Registrar la URL, fecha de consulta y versión de cada fuente.
- No depender de scraping frágil cuando exista una fuente estructurada.
- Aplicar caché y límites de solicitudes.
- No eludir controles de acceso, autenticación o medidas anti-bot.
- Documentar la base legal o licencia de cada conjunto de datos antes de producción.

---

## 8. Reglas financieras obligatorias

### 8.1 Identidad y contexto de cada cifra

Cada observación debe guardar:

- Empresa e identificador oficial.
- Cuenta y concepto normalizado.
- Etiqueta original.
- Valor original.
- Valor normalizado.
- Moneda.
- Unidad: unidades, miles o millones.
- Fecha inicial y final del periodo.
- Tipo de periodo: trimestre, acumulado, anual o instante.
- Estado consolidado o separado.
- Auditado o no auditado.
- Fuente, documento, versión y página.
- Fecha de captura.
- Método de extracción.
- Nivel de confianza.

### 8.2 Normalización

- Conservar siempre el dato original además del normalizado.
- No mezclar estados separados con consolidados.
- No comparar un trimestre individual con un valor acumulado del año.
- No mezclar monedas sin indicar tipo de cambio, fecha y fuente.
- No convertir unidades implícitamente en la interfaz.
- Priorizar la última versión presentada, manteniendo historial de rectificaciones.
- Versionar las fórmulas de los indicadores.

### 8.3 Validaciones automáticas

- Activos aproximadamente iguales a pasivos más patrimonio.
- El efectivo final del flujo de caja concuerda con el balance cuando sea comparable.
- Detección de cambios de unidad o moneda.
- Detección de duplicados y periodos superpuestos.
- Detección de valores atípicos frente al histórico.
- Reconciliación con totales publicados.
- Validación de signos contables.
- Validación de denominadores cero o negativos antes de calcular ratios.

Una validación fallida bloqueará la publicación automática del periodo afectado.

### 8.4 Fórmulas

Las fórmulas deben ejecutarse mediante código y estar documentadas. El usuario podrá ver la fórmula y los valores utilizados. Los modelos de lenguaje no realizarán los cálculos oficiales mostrados por el producto.

---

## 9. Uso de inteligencia artificial

### Usos permitidos

- Clasificar documentos y fragmentos.
- Resumir notas contables.
- Comparar narrativas entre periodos.
- Explicar indicadores calculados previamente.
- Relacionar hechos corporativos con métricas.
- Contestar preguntas mediante recuperación de evidencia.
- Proponer preguntas de investigación adicionales.

### Usos prohibidos

- Inventar o completar cifras faltantes.
- Calcular los valores oficiales del panel.
- Emitir recomendaciones personalizadas.
- Afirmar causalidad cuando sólo existe correlación temporal.
- Presentar una inferencia como hecho.
- Responder sin evidencia cuando la pregunta exige datos específicos.
- Ocultar incertidumbre o conflictos entre fuentes.

### Reglas de respuesta

- Toda afirmación material debe tener una cita cercana.
- Separar las secciones `Hechos observados`, `Interpretación` y `Datos faltantes`.
- Mostrar un nivel de confianza: alto, medio o bajo.
- Una confianza baja exige advertencia visible y no genera conclusiones destacadas.
- Si las fuentes se contradicen, mostrar la contradicción.
- Incluir fecha de corte de la información.
- La respuesta debe poder regenerarse usando las mismas fuentes y versión del prompt.

---

## 10. Restricciones legales y de producto

- Presentar el producto como herramienta de investigación y educación financiera.
- No prometer resultados, rentabilidad ni reducción garantizada del riesgo.
- No usar frases como `debes comprar`, `vende ahora` o equivalentes.
- No adaptar conclusiones a la situación patrimonial del usuario durante el MVP.
- No recibir dinero ni ejecutar órdenes.
- Identificar claramente opiniones generadas por IA.
- Mostrar metodología, limitaciones y posibles errores.
- Mantener registro de fuentes y versiones que fundamentaron cada salida.
- Obtener revisión de un abogado peruano especializado en mercado de valores antes del lanzamiento público o de añadir recomendaciones.
- Un disclaimer no sustituye el diseño adecuado del producto ni el cumplimiento normativo.

Texto orientativo para la interfaz:

> Esta plataforma ofrece información y herramientas de investigación. No constituye asesoría financiera ni una recomendación de compra o venta. Verifica las fuentes y considera tu situación y tolerancia al riesgo antes de tomar decisiones.

El texto definitivo deberá ser revisado legalmente.

---

## 11. Experiencia de usuario

### Flujo principal

1. El usuario abre el directorio.
2. Selecciona una empresa.
3. Visualiza el último periodo y los cambios más importantes.
4. Inspecciona gráficos e indicadores.
5. Abre la evidencia de cualquier cifra o afirmación.
6. Compara con otra empresa o periodo.
7. Consulta una pregunta específica al asistente.
8. Evalúa riesgos, datos faltantes y hechos recientes.

### Pantallas mínimas

1. Inicio y directorio.
2. Panel de empresa.
3. Estados e indicadores.
4. Comparador.
5. Documentos y citas.
6. Hechos de importancia.
7. Asistente.
8. Metodología y limitaciones.

### Estados que toda pantalla debe contemplar

- Cargando.
- Sin información.
- Información parcial.
- Fuente no disponible.
- Error de actualización.
- Datos pendientes de revisión.
- Datos rectificados.

---

## 12. Arquitectura sugerida

La elección es recomendada, no una obligación contractual.

### Frontend

- Next.js con TypeScript.
- Diseño responsive para escritorio y tablet.
- Librería de gráficos accesible.
- Renderizado de tablas con exportación CSV.

### Backend

- Python con FastAPI.
- Procesos separados para ingestión, normalización, validación y publicación.
- Tareas asíncronas para documentos y modelos de IA.

### Datos

- PostgreSQL como fuente de verdad.
- Extensión vectorial únicamente para recuperar fragmentos documentales.
- Almacenamiento de objetos compatible con S3 para originales y derivados.
- Caché opcional cuando exista una necesidad medida.

### Componentes lógicos

1. Conectores de fuentes.
2. Registro de documentos.
3. Extractor estructurado.
4. Extractor de PDF y OCR como respaldo.
5. Normalizador contable.
6. Motor de validaciones.
7. Motor de indicadores.
8. Índice documental.
9. Servicio de explicaciones y preguntas.
10. API de producto.
11. Interfaz web.
12. Panel interno de revisión.

### Principio arquitectónico

La base de datos financiera es la fuente de verdad para cifras. El índice semántico sirve para buscar texto, pero nunca reemplaza los datos financieros normalizados.

---

## 13. Modelo de datos mínimo

### Entidades principales

- `companies`
- `securities`
- `filings`
- `documents`
- `document_pages`
- `reporting_periods`
- `financial_concepts`
- `financial_facts`
- `metric_definitions`
- `metric_values`
- `corporate_events`
- `source_fragments`
- `ai_outputs`
- `validation_results`
- `review_tasks`

### Requisitos de auditoría

- No sobrescribir observaciones publicadas: crear una nueva versión.
- Conservar el documento original y su hash.
- Registrar qué proceso creó o modificó un dato.
- Registrar versión de fórmula, extractor, modelo y prompt.
- Poder reconstruir cualquier panel histórico.

---

## 14. Seguridad y privacidad

- El MVP tendrá acceso por invitación mediante correo y enlace seguro.
- No almacenará documentos de identidad, patrimonio ni información bancaria.
- No solicitará credenciales de corredores.
- Cifrado TLS en tránsito y cifrado del almacenamiento administrado.
- Secretos fuera del repositorio.
- Acceso mínimo necesario para servicios y administradores.
- Registro de acciones administrativas.
- Copias de seguridad automáticas y prueba de restauración.
- Límites de solicitudes para APIs y asistente.
- Política de retención y eliminación de cuentas.

---

## 15. Requisitos no funcionales

### Exactitud

- Ningún periodo se publica automáticamente si falla una validación crítica.
- Toda corrección debe quedar versionada.

### Rendimiento

- Panel inicial visible en menos de 3 segundos con caché caliente.
- Consultas normales de comparación en menos de 5 segundos.
- Respuesta inicial del asistente en menos de 10 segundos, salvo aviso explícito.

### Disponibilidad

- Objetivo del MVP: 99 % mensual, excluyendo mantenimiento programado.
- La caída de una fuente externa no debe borrar datos previamente publicados.

### Accesibilidad

- Navegación por teclado.
- Contraste suficiente.
- Gráficos acompañados por tablas o resúmenes textuales.
- No depender sólo del color para expresar riesgo o variación.

### Observabilidad

- Errores de ingestión.
- Antigüedad de los datos por empresa.
- Documentos pendientes.
- Validaciones fallidas.
- Coste y latencia del modelo.
- Preguntas sin respuesta.
- Citas abiertas por los usuarios.

---

## 16. Panel interno de revisión

Antes de crear herramientas administrativas generales, el MVP necesita una vista interna que permita:

- Revisar documentos nuevos.
- Comparar valores extraídos con el original.
- Aprobar o rechazar periodos.
- Resolver cuentas no mapeadas.
- Revisar validaciones fallidas.
- Ver respuestas de IA reportadas.
- Republicar una empresa después de una corrección.

La revisión manual es parte del MVP; no debe ocultarse como trabajo excepcional.

---

## 17. Analítica de producto

Eventos mínimos:

- Empresa consultada.
- Periodo cambiado.
- Indicador inspeccionado.
- Fuente abierta.
- Comparación creada.
- Pregunta realizada.
- Respuesta sin evidencia.
- Sesión completada.
- Intención de pago.

No registrar el texto completo de preguntas sensibles sin consentimiento y política de privacidad adecuada.

---

## 18. Criterios de aceptación del MVP

El MVP estará terminado cuando:

1. Las ocho empresas tengan los cinco años y ocho trimestres acordados, o una explicación pública de cada ausencia.
2. Los tres estados principales puedan consultarse con fuente y versión.
3. Todos los indicadores definidos tengan fórmula visible.
4. Las validaciones críticas bloqueen datos inconsistentes.
5. El comparador impida periodos o estados incompatibles.
6. El usuario pueda abrir la evidencia de cualquier cifra destacada.
7. Los resúmenes separen hechos, interpretación y datos faltantes.
8. El asistente se abstenga cuando no disponga de evidencia.
9. Los hechos de importancia se actualicen al menos una vez al día.
10. El sistema muestre la fecha de actualización de cada empresa.
11. Existan pruebas automatizadas de fórmulas, unidades, periodos y permisos.
12. Se realice una revisión manual de una muestra mínima de 200 observaciones por empresa.
13. No existan errores críticos conocidos de exactitud o trazabilidad.
14. Al menos 15 usuarios completen la prueba de validación.
15. Se documenten resultados, disposición a pagar y decisión de continuar, ajustar o detener.

---

## 19. Plan de desarrollo

### Orden vigente de ejecución

El desarrollo posterior a la Fase 10 se realizará en lotes verificables y en este
orden. No se inicia un bloque posterior mientras el anterior conserve fallos críticos
de exactitud o trazabilidad:

1. **Ampliar cobertura de datos (máxima prioridad).** Incorporar progresivamente las
   ocho empresas y los periodos acordados. Lotes completados: Volcan como tercera y
   Poderosa como cuarta empresa, con estados consolidados 2025 y notas auditadas
   2024–2025.
2. **Endurecimiento de producto.** Seguridad, rendimiento, accesibilidad, copias de
   seguridad y revisión legal.
3. **Analítica y validación con usuarios.** Instrumentación mínima, pruebas observadas
   y validación de disposición a pagar.
4. **Completar eventos y alertas.** Ampliar fuentes oficiales, actualización y avisos.
5. **Asistente con abstención y trazabilidad usando NVIDIA.** Sólo después de validar
   cobertura, calidad y uso real; nunca se usará para calcular cifras financieras.
6. **Pendientes post-MVP.** Incluye reconstrucción de tablas de notas y mejoras que no
   bloquean el piloto.

Las fases siguientes conservan el diseño técnico base ya ejecutado y sirven como
registro histórico de sus entregables.

### Fase 0: exploración de datos

- Confirmar fuentes, licencias y formatos.
- Descargar una muestra por cada empresa.
- Verificar identificadores, periodos, moneda y consolidación.
- Probar XBRL, datos abiertos y PDFs.
- Crear un diccionario inicial de cuentas.
- Confirmar que las ocho empresas son técnicamente cubribles.

**Salida obligatoria:** informe de viabilidad de datos y una empresa procesada de extremo a extremo.

### Fase 1: núcleo financiero

- Registro de empresas, documentos y periodos.
- Ingestión de estados estructurados.
- Normalización y versionado.
- Validaciones contables.
- Cálculo de indicadores.
- Panel interno de revisión básico.

### Fase 2: interfaz de análisis

- Directorio.
- Panel de empresa.
- Tablas y gráficos.
- Comparación.
- Evidencia y enlaces.

### Fase 3: documentos e IA

- Segmentación de notas.
- **Pendiente post-MVP:** reconstruir las tablas de las notas como HTML accesible y CSV,
  preservando encabezados, moneda, escala, periodos y referencia de página. Las tablas
  de baja confianza deben continuar mostrando el PDF original como respaldo.
- OCR sólo donde sea necesario.
- Índice de fragmentos. **Implementado en la Fase 8:** búsqueda local en español,
  filtros por empresa, tema y ejercicio, y referencias exactas a nota y página.
- Resúmenes citados. **Implementado en la Fase 9:** hechos extractivos con cita cercana,
  confianza, fecha de corte, interpretación separada y abstención ante texto insuficiente.
- Comparación narrativa. **Implementada en la Fase 10:** emparejamiento reproducible
  de notas 2025–2024, evidencia citada lado a lado, cobertura, confianza y abstención
  cuando no existe una equivalencia documental suficiente.
- Asistente con abstención y trazabilidad.

### Fase 4: eventos y validación

- Hechos de importancia.
- Alertas de actualización.
- Analítica de producto.
- Prueba con usuarios.
- Experimento de precio.

### Fase 5: endurecimiento

- Seguridad.
- Rendimiento.
- Accesibilidad.
- Copias de seguridad.
- Revisión legal.
- Corrección de resultados de la prueba.

---

## 20. Pruebas mínimas

### Pruebas unitarias

- Fórmulas financieras.
- Conversión de unidades.
- Normalización de fechas.
- Periodos trimestrales frente a acumulados.
- Signos y denominadores.

### Pruebas de integración

- Fuente a documento.
- Documento a observación.
- Observación a indicador.
- Indicador a interfaz.
- Cita a página original.
- Rectificación a nueva versión.

### Pruebas de regresión

- Conjunto dorado de documentos revisados manualmente.
- Resultados esperados por empresa y periodo.
- Comparación antes de desplegar cambios en extractores o fórmulas.

### Evaluación de IA

- Preguntas respondibles y no respondibles.
- Exactitud de citas.
- Fidelidad al documento.
- Identificación de contradicciones.
- Abstención ante evidencia insuficiente.
- Ausencia de recomendaciones de inversión.

---

## 21. Riesgos principales y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---:|---|
| Cifras incorrectas | Crítico | Datos estructurados primero, validaciones y revisión humana |
| Confusión entre periodos | Crítico | Modelo temporal explícito y bloqueo de comparaciones |
| Alucinaciones de IA | Crítico | Recuperación con citas, abstención y evaluación continua |
| Riesgo regulatorio | Alto | Producto informativo, sin personalización y revisión legal |
| Licencias de noticias | Alto | Fuentes primarias y acuerdos/API autorizados |
| Mercado B2C pequeño | Alto | Validación de pago y posterior enfoque B2B/LatAm |
| Scraping inestable | Medio | Fuentes estructuradas, caché y conectores versionados |
| Diferencias contables | Alto | Un solo sector inicial y diccionario versionado |
| Costes de modelos | Medio | Procesamiento por lotes, caché y modelos según tarea |
| Resúmenes poco útiles | Medio | Evaluación con analistas y medición de fuentes abiertas |

---

## 22. Estrategia de validación comercial

### Prueba concierge previa al lanzamiento

1. Preparar manualmente análisis de cinco empresas usando el formato futuro.
2. Reclutar entre 15 y 20 participantes del público objetivo.
3. Observar su proceso actual sin sugerirles cómo usar el producto.
4. Medir tiempo, errores, dudas y fuentes consultadas.
5. Permitir que repitan el análisis con el prototipo.
6. Solicitar un compromiso real: pago anticipado, reserva o carta de intención.

### Experimentos de precio

- Plan individual de prueba: S/ 30 a S/ 60 mensuales.
- Plan profesional: validar entrevistas antes de fijar precio.
- No ofrecer plan gratuito ilimitado durante la validación.

Los precios son hipótesis, no decisiones definitivas.

### Señales para continuar

- Ahorro de tiempo repetible.
- Uso recurrente después de la primera prueba.
- Usuarios que abren y valoran las fuentes.
- Solicitudes convergentes de nuevas empresas o alertas.
- Compromisos de pago.

### Señales para detener o cambiar

- Los usuarios sólo valoran resúmenes gratuitos.
- No existe disposición a pagar.
- La revisión manual hace económicamente inviable cada actualización.
- La exactitud exigida no puede alcanzarse con las fuentes disponibles.
- La adquisición o licencia de datos elimina el margen esperado.

---

## 23. Decisiones que no deben reabrirse durante el MVP

Salvo evidencia crítica nueva:

- Se comienza con un solo sector.
- Se cubren ocho empresas.
- No hay recomendación de compra o venta.
- No hay precios en tiempo real.
- No hay aplicación móvil nativa.
- Los cálculos son deterministas.
- Toda cifra tiene trazabilidad.
- Los datos inconsistentes no se publican.
- La revisión humana forma parte de la operación inicial.
- La cobertura dentro del universo cerrado se amplía progresivamente y cada empresa
  debe superar el mismo control de calidad antes de publicarse.

---

## 24. Preguntas que la fase 0 debe resolver

- ¿Qué datos de la SMV están disponibles en XBRL, JSON o Excel por empresa y periodo?
- ¿Qué límites técnicos y legales existen para su reutilización?
- ¿Cómo se identifican rectificaciones?
- ¿Qué tan consistentes son las taxonomías entre empresas y años?
- ¿Qué documentos requieren OCR?
- ¿Qué fuente oficial ofrece el mejor historial de hechos de importancia?
- ¿Qué métricas mineras adicionales pueden calcularse de manera consistente?
- ¿Cuánto tiempo de revisión humana requiere una actualización?
- ¿Cuál es el coste por empresa y periodo?

No se ampliará el alcance hasta responder estas preguntas con evidencia.

---

## 25. Próximos pasos inmediatos

1. Generalizar el corte por empresa para admitir estados individuales sin presentarlos
   como consolidados.
2. Incorporar Cerro Verde, Nexa Resources Perú, El Brocal y Shougang con su alcance
   real publicado por la SMV.
4. Completar cinco años y ocho trimestres por empresa, o publicar la razón verificable
   de cada ausencia.
5. Construir el conjunto dorado y revisar una muestra mínima de 200 observaciones por
   empresa antes de cerrar la ampliación de cobertura.

---

## 26. Definición resumida del producto

El MVP no es un lector genérico de PDFs ni un sistema que adivina el precio futuro de una acción. Es una aplicación de investigación financiera para ocho empresas mineras peruanas, con datos históricos normalizados, indicadores reproducibles, documentos oficiales, hechos de importancia y explicaciones citadas. Su éxito se medirá por exactitud, ahorro de tiempo y disposición real a pagar.
