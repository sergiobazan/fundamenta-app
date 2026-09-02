# Fase 0: resultado del primer corte vertical

**Fecha de verificación:** 2026-08-28  
**Empresa:** Compañía de Minas Buenaventura S.A.A.  
**RPJ:** `B20003`  
**RUC:** `20100079501`  
**Periodo:** Anual 2025  
**Alcance:** Consolidado  
**Estado:** Situación financiera  

## Fuente

- Portal de Datos Abiertos de la SMV.
- Operación SOAP: `obtener_BalanceGeneral`.
- Documento de contraste: estado anual integrado 2025 de Buenaventura.
- Moneda normalizada: `USD`.
- Escala confirmada mediante documento: `thousands` (`US$(000)`).

## Resultado almacenado

| Entidad | Registros |
|---|---:|
| Empresas | 1 |
| Filings | 1 |
| Cuentas financieras | 71 |
| Conceptos normalizados | 7 |
| Validaciones | 1 |
| Capturas de fuente | 1 |

La respuesta SOAP original se conserva completa en PostgreSQL junto con su hash
SHA-256. Para esta captura el hash es:

```text
720870b4877eb791a5766ba9c737f3fa592ae7edb9c9a8e3759980f39cc11efb
```

## Conceptos normalizados

| Concepto | 2025 | Comparativo |
|---|---:|---:|
| Efectivo y equivalentes | 529,839 | 478,435 |
| Activos corrientes | 1,156,516 | 838,362 |
| Pasivos corrientes | 575,990 | 479,738 |
| Activos totales | 6,022,836 | 5,047,903 |
| Pasivos totales | 1,755,371 | 1,488,202 |
| Patrimonio total | 4,267,465 | 3,559,701 |
| Pasivos y patrimonio | 6,022,836 | 5,047,903 |

Los valores están expresados en miles de dólares estadounidenses.

## Validación

```text
activos totales - pasivos y patrimonio = 0
```

La regla `balance_equation` terminó con estado `passed`.

## Idempotencia

La misma ingesta se ejecutó dos veces. La segunda ejecución actualizó el filing sin
crear empresas, capturas, cuentas o validaciones duplicadas.

## API verificada

- `GET /health`: HTTP 200.
- `GET /companies`: HTTP 200 y devuelve Buenaventura.

## Restricciones todavía vigentes

- Sólo se ingirió el estado de situación financiera.
- Sólo siete cuentas tienen concepto normalizado.
- La escala debe confirmarse por empresa, periodo y documento.
- Todavía no existen métricas financieras derivadas.
- Todavía no existe frontend.
- Todavía no se usa inteligencia artificial.

## Siguiente incremento recomendado

1. Ingerir el estado de resultados 2025 consolidado.
2. Ingerir el estado de flujos de efectivo 2025 consolidado.
3. Mapear ingresos, utilidad operativa, utilidad neta y flujos principales.
4. Validar las cifras contra el mismo documento anual.
5. Exponer los tres estados mediante endpoints de lectura.

