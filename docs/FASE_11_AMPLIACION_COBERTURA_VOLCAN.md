# Fase 11: ampliación progresiva de cobertura — Volcan

**Fecha de verificación:** 2026-09-02  
**Fuente estructurada:** Datos Abiertos de la SMV  
**Corte incorporado:** anual 2025, consolidado  
**Notas incorporadas:** anuales 2025 y 2024, consolidadas

## Resultado

Volcan Compañía Minera S.A.A. (`CM0001`) es la tercera empresa publicada. El lote
quedó incorporado por el bootstrap automático y no requiere comandos manuales en
producción.

- 3 estados financieros 2025;
- 172 hechos contables;
- 15 métricas calculadas y ninguna no disponible;
- 0 validaciones contables fallidas;
- 38 notas auditadas de 2025 y 37 de 2024;
- resúmenes citados e índice documental por página;
- comparación narrativa 2025 frente a 2024, con 30 equivalencias, 8 notas sólo en
  2025 y 7 sólo en 2024.

El estado `partial` de la comparación narrativa describe cobertura de emparejamiento,
no un fallo de extracción: todas las notas de ambos documentos están disponibles y las
no equivalentes permanecen visibles como tales.

## Fuentes primarias

- [Volcan consolidado auditado 2025](https://www.smv.gob.pe/ConsultasP8/temp/2025%20Anual%20Auditado%20Cons.pdf)
- [Volcan consolidado auditado 2024](https://www.smv.gob.pe/ConsultasP8/temp/Volcan%20EEFF%20Consol%20Aud%2031dic2024.pdf)
- Servicio oficial `WebServiceInfoFinanciera.asmx` de la SMV para los tres estados
  estructurados.

Ambos PDF declaran importes en miles de dólares (`US$000`), por lo que el filing usa
`reported_scale = thousands` y conserva la URL de respaldo.

## Compatibilidad resuelta en el extractor

Los documentos de Buenaventura y Minsur numeran las notas con punto (`1. Título`).
Volcan usa encabezados sin punto (`1 TÍTULO`) y no repite el rótulo general de notas en
cada página. El extractor ahora admite ambos formatos, exige títulos en mayúsculas
cuando falta el punto y mantiene numeración secuencial. Esto evita confundir una línea
como `31 de diciembre de 2025` con la nota 31.

La regresión se verificó contra los seis PDF registrados. Ningún documento existente
perdió notas.

## Auditoría del universo objetivo

La consulta oficial del balance anual 2025 confirmó los identificadores y el alcance
disponible para el siguiente trabajo:

| Empresa | RPJ | Alcance anual 2025 encontrado | Estado |
|---|---|---|---|
| Buenaventura | `B20003` | Consolidado | Publicada |
| Minsur | `A20032` | Consolidado | Publicada |
| Volcan | `CM0001` | Consolidado e individual | Publicada en consolidado |
| Poderosa | `B20041` | Consolidado e individual | Siguiente lote |
| Cerro Verde | `CM0006` | Individual | Pendiente de soporte multi-alcance |
| Nexa Resources Perú | `B20010` | Individual | Pendiente de soporte multi-alcance |
| El Brocal | `B20026` | Individual | Pendiente de soporte multi-alcance |
| Shougang Hierro Perú | `CM0004` | Individual | Pendiente de soporte multi-alcance |

No se presentará un estado individual como consolidado. Por eso Poderosa es el cuarto
caso recomendado: puede atravesar primero el flujo consolidado ya validado. Después se
generalizarán los parámetros de alcance de backend y frontend antes de incorporar las
cuatro empresas que sólo aparecieron con información individual.

## Verificación ejecutada

- Bootstrap: 3 empresas, 9 filings, 516 hechos, 45 métricas, 0 métricas ausentes y 0
  validaciones fallidas.
- Notas: 6 documentos vigentes y 223 notas en total.
- API: compañía, resumen, notas y comparación de Volcan respondieron HTTP 200.
- Backend: 50 pruebas aprobadas y Ruff sin errores.
- Frontend: compilación de producción Next.js aprobada.
- Chrome móvil: directorio con `3 de 8`, tarjeta de Volcan, detalle completo y consola
  sin errores.

## Próximo lote

1. localizar y validar los PDF consolidados auditados 2025 y 2024 de Poderosa;
2. incorporar sus tres estados y ejecutar los controles contables;
3. revisar las 15 métricas y una muestra manual contra el PDF;
4. importar notas sólo si el extractor supera la regresión documental;
5. publicar la cuarta empresa y actualizar el contador automáticamente.
