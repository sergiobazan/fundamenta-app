# Fase 5: Minsur y comparador homogéneo

## Corte alcanzado

Se incorporó una segunda empresa real y se habilitó el primer comparador financiero
del MVP. La comparación sólo se muestra cuando periodo, alcance, moneda, escala y
versión de fórmula coinciden.

## Minsur 2025

- Empresa: Minsur S.A.
- SMV RPJ: `A20032`.
- RUC: `20100136741`.
- Corte: anual, consolidado, 2025.
- Moneda y escala: USD en miles.
- Estados: situación financiera, resultados y flujo de efectivo.
- Hechos almacenados: 172.
- Conceptos normalizados: 41.
- Validaciones: 7 aprobadas, 0 fallidas.
- Métricas: 15 calculadas, 0 no disponibles.

La presentación anual auditada consolidada fue comunicada a la SMV el 26 de marzo
de 2026. La respuesta SOAP cruda, su huella SHA-256 y la URL oficial se conservan en
la base.

## Corrección contable del flujo

La primera ejecución mostró una diferencia de USD 1,538 miles entre la suma de las
actividades y el aumento neto de efectivo. No era un error del emisor: correspondía
al efecto de variaciones en el tipo de cambio.

La normalización ahora reconoce:

- `3D0401`: aumento neto antes del efecto cambiario.
- `3D0404`: efecto de variaciones en tasas de cambio.

El pipeline ejecuta por separado la conciliación de actividades y la conciliación
del efecto cambiario. Minsur y Buenaventura pasan ambos controles, además del
rollforward de efectivo y el cruce contra el balance.

## Comparador

Ruta autenticada: `/comparador`.

Incluye:

- Selectores de empresa A y empresa B.
- Guardia de compatibilidad por año, periodo, alcance, moneda, escala y fórmula.
- Las 15 métricas lado a lado.
- Referencia primaria independiente por columna.
- Acceso a la ficha y estados auditables de cada emisor.
- Aviso explícito de que una cifra mayor no implica una mejor inversión.

## Generalización del frontend

Las tarjetas y fichas dejaron de enlazar siempre a Buenaventura. La fuente, nombre,
identificador visual y texto de referencia ahora se obtienen de la empresa y sus
filings. El directorio muestra dos de las ocho empresas objetivo.

## Incidencia visual corregida

Chrome DevTools MCP detectó que el avatar demo devolvía 404 porque `UPLOAD_DIR` se
interpretaba de manera distinta según el directorio desde el cual arrancaba Uvicorn.
La ruta relativa ahora se resuelve siempre desde la raíz del proyecto y el avatar se
sirve como `image/webp` con HTTP 200.

## Validación ejecutada

- 16 pruebas backend aprobadas.
- Ruff sin observaciones.
- TypeScript sin errores.
- Build de producción Next.js aprobado.
- Login demo y render HTTP del comparador aprobados.
- Revisión visual Chrome MCP en escritorio y móvil aprobada.
- Consola Chrome sin errores, advertencias ni issues.
