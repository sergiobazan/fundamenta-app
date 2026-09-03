# Fase 10: comparación narrativa de notas

## Resultado

Fundamenta incorpora un segundo ejercicio de notas auditadas consolidadas para
Buenaventura y Minsur y permite contrastar 2025 frente a 2024. La pantalla no entrega
una recomendación ni convierte una diferencia textual en un cambio económico: muestra
la evidencia seleccionada de ambos períodos lado a lado y deja la interpretación en
manos del analista.

Las cuatro fuentes son PDF oficiales publicados por la SMV. La validación directa del
extractor obtuvo:

- Buenaventura 2025: 36 notas;
- Buenaventura 2024: 37 notas;
- Minsur 2025: 38 notas;
- Minsur 2024: 37 notas;
- total: 148 notas y 306 hechos extractivos citables.

## Extracción y anomalía de Buenaventura 2024

El PDF de Buenaventura 2024 pierde el glifo `3` del encabezado de la nota 3 en su capa
de texto. El documento conserva los subapartados 3.1 y 3.2, pero el extractor anterior
detenía la secuencia después de la nota 2.

La recuperación implementada sólo acepta el título contable conocido “Juicios,
estimados y supuestos contables significativos” y sólo cuando la secuencia espera la
nota 3. No se infieren números para otros encabezados dañados. Existe una prueba de
regresión específica para este caso.

## Emparejamiento reproducible

La migración `009_narrative_comparisons.sql` agrega:

- `narrative_comparisons`: empresa, documentos de ambos períodos, algoritmo, versión,
  confianza, fecha de corte y SHA-256 combinado de las entradas;
- `narrative_comparison_notes`: nota actual, nota anterior, resúmenes citados fijados,
  método, similitud, confianza y estado del emparejamiento.

El algoritmo primero busca títulos normalizados idénticos. Para los restantes calcula
similitud explicable entre los términos del título y conserva únicamente coincidencias
por encima del umbral definido. Nunca empareja sólo porque el número de nota coincide:
los números pueden desplazarse si una empresa agrega o elimina una revelación.

Sobre los documentos reales:

- Buenaventura: 36 equivalencias; “Préstamos bancarios” aparece sólo en 2024;
- Minsur: 37 equivalencias; “Hechos posteriores” aparece sólo en 2025.

Las notas sin equivalente permanecen visibles y con confianza baja. “Sólo en un
período” significa que el sistema no encontró un título equivalente; no demuestra que
el asunto económico sea nuevo o haya desaparecido.

## Evidencia y abstención

Cada lado de una equivalencia reutiliza una versión concreta del resumen extractivo y
conserva sus enlaces al PDF y página. La interfaz separa:

1. hechos observados en 2025;
2. hechos observados en 2024;
3. calidad y método del emparejamiento;
4. límites de la comparación.

No se generan causalidad, materialidad, impacto esperado ni atractivo de inversión.
Si un resumen no tiene narrativa suficientemente legible, la columna muestra la
abstención en vez de rellenar contenido.

## Automatización

Las fuentes 2024 están en el mismo catálogo que las de 2025. En una base vacía, el
arranque de Render aplica las nueve migraciones, descarga los cuatro PDF y genera
resúmenes y comparaciones sin comandos manuales. En una base existente, la diferencia
en el catálogo hace que el bootstrap complete los documentos 2024 faltantes.

Antes de guardar una comparación, el proceso completa la versión vigente de los
resúmenes de ambos períodos. Así los identificadores de evidencia que quedan fijados
no apuntan por accidente a una versión anterior.

Los resúmenes extractivos v3 ya no guardan como dato faltante la disponibilidad de
otro ejercicio: esa condición depende del catálogo completo y ahora corresponde
exclusivamente al comparador. El emparejador v2 fija estos resúmenes después de que
están disponibles, por lo que el orden de descarga de las empresas no altera el
resultado.

## Contrato y pantalla

La API expone:

```text
GET /companies/{smv_rpj}/note-comparisons
    ?current_year=2025
    &previous_year=2024
    &period=A
    &scope=consolidated
```

Admite filtros por tema y notas prioritarias. Devuelve cobertura total, estado global,
confianza, versiones documentales, equivalencias y los hechos citados de cada lado.

La aplicación añade la ruta:

```text
/empresas/{smv_rpj}/notas/comparar
```

El acceso está disponible desde el directorio de notas. Por defecto se muestran las
notas prioritarias y el usuario puede ampliar a todas.

## Verificación

- 49 pruebas de backend aprobadas.
- Ruff sin incidencias.
- Los cuatro PDF oficiales fueron descargados y procesados con el extractor real.
- Emparejamiento real: 73 equivalencias, una nota sólo en 2025 y una sólo en 2024.
- TypeScript aprobado.
- Build de producción de Next.js aprobado, incluida la nueva ruta.
- Revisión desktop y móvil en Chrome: sin desbordamiento horizontal a 390 px.
- Lighthouse móvil: 100 en accesibilidad, buenas prácticas, SEO y navegación
  automatizada; consola sin errores ni advertencias.
- Migración 009 aplicada en PostgreSQL local: cuatro documentos vigentes y 148 notas.
- Endpoint real verificado con HTTP 200, 11 comparaciones prioritarias para Minsur,
  resúmenes v3 y cero mensajes obsoletos sobre ausencia del período anterior.

## Próxima etapa de la especificación

El siguiente punto es el **asistente con abstención y trazabilidad**. La futura
integración con NVIDIA podrá redactar interpretaciones, pero deberá usar estas
evidencias fijadas, citar cada afirmación material y pasar evaluaciones antes de quedar
visible para usuarios.
