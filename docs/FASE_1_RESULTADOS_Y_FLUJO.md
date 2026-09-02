# Fase 1: estado de resultados y flujo de efectivo

**Fecha de verificación:** 2026-08-28  
**Empresa:** Compañía de Minas Buenaventura S.A.A.  
**RPJ:** `B20003`  
**Periodo:** Anual 2025  
**Alcance:** Consolidado  
**Moneda y escala:** Miles de dólares estadounidenses  

## Resultado consolidado en PostgreSQL

| Entidad | Registros |
|---|---:|
| Empresas | 1 |
| Filings | 3 |
| Cuentas financieras | 172 |
| Conceptos normalizados | 37 |
| Validaciones | 6 |
| Validaciones fallidas | 0 |
| Capturas de fuente | 3 |

Los tres filings corresponden al estado de situación financiera, estado de resultados
y estado de flujos de efectivo.

## Estado de resultados normalizado

| Concepto | 2025 | Comparativo |
|---|---:|---:|
| Ingresos | 1,731,639 | 1,154,605 |
| Costo de ventas | -949,248 | -795,318 |
| Utilidad bruta | 782,391 | 359,287 |
| Utilidad operativa | 633,206 | 445,655 |
| Utilidad antes de impuestos | 967,310 | 573,449 |
| Impuesto a las ganancias | -128,201 | -156,164 |
| Utilidad de operaciones continuadas | 839,109 | 417,285 |
| Operaciones discontinuadas | -8,921 | -1,022 |
| Utilidad neta | 830,188 | 416,263 |
| Utilidad atribuible a propietarios | 782,145 | 402,689 |
| Utilidad atribuible a no controladores | 48,043 | 13,574 |

Los importes de la tabla están en miles de USD.

La ganancia básica por acción ordinaria también se normalizó, pero se almacena con
`value_kind = 'per_share'` y `fact_scale = 'units'`. Su valor 2025 es USD 3.08 por
acción, evitando tratarlo erróneamente como miles de USD.

## Flujo de efectivo normalizado

| Concepto | 2025 | Comparativo |
|---|---:|---:|
| Flujo operativo | 577,320 | 486,059 |
| Compra de propiedades, planta y equipo | -473,008 | -337,743 |
| Flujo de inversión | -477,666 | -117,924 |
| Préstamos recibidos | 634,344 | 0 |
| Pago de préstamos | -556,750 | -79,602 |
| Dividendos pagados | -122,478 | -25,783 |
| Flujo de financiación | -48,250 | -109,490 |
| Variación neta de efectivo | 51,404 | 258,645 |
| Efectivo inicial | 478,435 | 219,790 |
| Efectivo final | 529,839 | 478,435 |

Los importes están en miles de USD.

## Validaciones aprobadas

1. Activos igual a pasivos más patrimonio.
2. Ingresos más costo de ventas igual a utilidad bruta.
3. Operaciones continuadas más discontinuadas igual a utilidad neta.
4. Flujo operativo más inversión y financiación igual a variación neta.
5. Efectivo inicial más variación neta igual a efectivo final.
6. Efectivo final del flujo igual al efectivo del balance.

Todas terminaron con estado `passed` y diferencia cero.

## Endpoints agregados

### Listar filings de una empresa

```http
GET /companies/B20003/filings
```

### Consultar un estado completo

```http
GET /companies/B20003/statements/income_statement?year=2025
GET /companies/B20003/statements/cash_flow?year=2025
```

Para devolver únicamente cuentas normalizadas:

```http
GET /companies/B20003/statements/income_statement?year=2025&normalized_only=true
```

Cada respuesta incluye metadatos de fuente, hash de la captura, cuentas, unidades,
escalas y validaciones.

## Idempotencia

Resultados y flujo se ingirieron dos veces. La segunda ejecución actualizó los
filings existentes y mantuvo exactamente tres filings, 172 cuentas, seis validaciones
y tres capturas de fuente.

## Próximo incremento recomendado

1. Crear métricas derivadas versionadas.
2. Calcular crecimiento, márgenes, liquidez, apalancamiento, ROA, ROE y flujo libre.
3. Definir reglas para denominadores negativos o cero.
4. Exponer un endpoint de resumen financiero.
5. Agregar pruebas con resultados esperados para Buenaventura 2025.

