# Fase 2: métricas financieras y punto de corte previo al frontend

**Fecha de verificación:** 2026-08-29  
**Empresa piloto:** Compañía de Minas Buenaventura S.A.A.  
**RPJ:** `B20003`  
**Periodo:** Anual 2025 consolidado  
**Estado:** Backend listo para iniciar el frontend  

## Alcance terminado

- Tres estados financieros persistidos.
- 172 cuentas originales.
- 39 conceptos normalizados después de incorporar deuda financiera.
- Seis validaciones contables aprobadas.
- Quince métricas derivadas.
- Fórmulas versionadas.
- Insumos y filing de origen guardados por métrica.
- Protección frente a denominadores cero o negativos.
- Protección frente a monedas o escalas incompatibles.
- Cálculo y actualización idempotentes.
- Endpoint de resumen verificado con HTTP 200.

## Métricas calculadas

| Métrica | Valor | Convención |
|---|---:|---|
| Crecimiento de ingresos | 0.499767452938 | 49.98 % |
| Margen bruto | 0.451821078181 | 45.18 % |
| Margen operativo | 0.365668594898 | 36.57 % |
| Margen neto | 0.479423251613 | 47.94 % |
| Razón corriente | 2.007875136721 | 2.01x |
| Capital de trabajo | 580,526 | Miles de USD |
| Deuda financiera total | 744,891 | Miles de USD |
| Deuda financiera neta | 215,052 | Miles de USD |
| Deuda financiera / patrimonio | 0.174551167965 | 0.17x |
| Pasivos / patrimonio | 0.411338112908 | 0.41x |
| ROA | 0.149978786421 | 15.00 % |
| ROE | 0.212129907555 | 21.21 % |
| Margen de flujo operativo | 0.333395124503 | 33.34 % |
| Flujo de caja libre | 104,312 | Miles de USD |
| Margen de flujo de caja libre | 0.060238883509 | 6.02 % |

Los porcentajes se almacenan como proporciones decimales. El frontend será
responsable de multiplicar por 100 únicamente para presentación.

## Fórmulas relevantes

```text
crecimiento_ingresos = ingresos_actuales / ingresos_comparativos - 1
margen_bruto = utilidad_bruta / ingresos
margen_operativo = utilidad_operativa / ingresos
margen_neto = utilidad_neta / ingresos
razon_corriente = activos_corrientes / pasivos_corrientes
capital_trabajo = activos_corrientes - pasivos_corrientes
deuda_total = deuda_corriente + deuda_no_corriente
deuda_neta = deuda_total - efectivo
ROA = utilidad_neta / activos_promedio
ROE = utilidad_neta / patrimonio_promedio
flujo_caja_libre = flujo_operativo + compras_de_propiedad_planta_equipo
```

Las compras de propiedad, planta y equipo vienen reportadas con signo negativo.

## Contrato disponible para el frontend

### Salud

```http
GET /health
```

### Empresas

```http
GET /companies
```

### Filings disponibles

```http
GET /companies/B20003/filings
```

### Estado financiero

```http
GET /companies/B20003/statements/balance_sheet?year=2025
GET /companies/B20003/statements/income_statement?year=2025
GET /companies/B20003/statements/cash_flow?year=2025
```

Parámetro opcional:

```text
normalized_only=true
```

### Resumen de métricas

```http
GET /companies/B20003/summary?year=2025&period=A&scope=consolidated
```

Cada métrica incluye:

- Código estable.
- Nombre y descripción.
- Tipo: monetaria, porcentaje o ratio.
- Expresión de la fórmula.
- Versión de fórmula.
- Estado: calculada o no disponible.
- Valor.
- Moneda y escala cuando corresponde.
- Razón de indisponibilidad, si aplica.
- Cuentas y valores utilizados.
- Identificadores de los filings de origen.
- Fecha de cálculo.

## Reglas que debe respetar el frontend

- No recalcular métricas en React.
- No convertir moneda sin una fuente de tipo de cambio.
- Mostrar `%` sólo cuando `value_kind = percentage`.
- Mostrar `x` para ratios según la decisión de diseño.
- Respetar `currency_code` y `value_scale` en valores monetarios.
- Mostrar el estado no disponible y su razón; nunca sustituirlo por cero.
- Permitir que el usuario inspeccione fórmula e insumos.
- Mostrar periodo, alcance consolidado/individual y fecha de actualización.
- No presentar las métricas como recomendación de compra o venta.

## Comprobaciones finales

- Trece pruebas automatizadas aprobadas.
- Quince métricas calculadas.
- Cero métricas no disponibles para Buenaventura 2025.
- Dos ejecuciones consecutivas mantienen quince filas en `metric_values`.
- `GET /companies/B20003/summary?year=2025` responde HTTP 200.
- El flujo de caja libre conserva sus dos cuentas de origen y filing asociado.

## Trabajo deliberadamente pendiente

- Frontend Next.js.
- Diseño visual y sistema de componentes.
- Gráficos y experiencia responsive.
- Cobertura histórica de cinco años.
- Resto de empresas del universo piloto.
- Autenticación.
- Noticias, documentos e inteligencia artificial.

El próximo cambio debe comenzar con las especificaciones de frontend del usuario.

