# Fase 4: directorio y estados financieros auditables

## Corte alcanzado

La aplicación dejó de ser un dashboard aislado. Ahora existe navegación autenticada
desde el directorio de empresas hasta la ficha del emisor y cada estado financiero.

## Rutas nuevas

- `/empresas`: directorio buscable por nombre, RUC, sector o código SMV.
- `/empresas/[smvRpj]`: ficha de empresa con cobertura, estados y 15 métricas.
- `/empresas/[smvRpj]/estados/balance_sheet`: situación financiera.
- `/empresas/[smvRpj]/estados/income_statement`: resultados.
- `/empresas/[smvRpj]/estados/cash_flow`: flujo de efectivo.

Todas las rutas requieren sesión válida. Un identificador o estado inexistente muestra
una página 404 contextual en lugar de un error genérico.

## Trazabilidad visible

El visor de estados muestra:

- Empresa, periodo, alcance, moneda y escala.
- Enlace al documento que confirma la escala.
- Proveedor, fecha de recuperación y prefijo de la huella SHA-256.
- Etiqueta contable original y concepto normalizado.
- Valor actual y comparativo.
- Resultado de los controles automáticos.

La tabla se limita a conceptos normalizados. No se estiman cuentas ausentes ni se
mezclan estados individuales con consolidados.

## Comportamiento responsive

- La tabla mantiene legibilidad y se desplaza horizontalmente en pantallas pequeñas.
- Los metadatos pasan de cuatro a dos columnas en móvil.
- Las tarjetas de estados y métricas pasan a una columna.
- El directorio oculta metadatos secundarios, pero conserva empresa, estado y acceso.
- La navegación móvil incorpora el acceso a empresas.

## Validación ejecutada

- TypeScript sin errores.
- Build de producción Next.js aprobado.
- Recorrido HTTP autenticado aprobado para directorio, ficha y tres estados.
- Ruta de estado inválida verificada con respuesta 404.

## Chrome MCP

En la fase 4 la herramienta todavía no estaba conectada, por lo que esa entrega se
validó mediante build, HTML, rutas HTTP y reglas responsive. La conexión quedó
operativa y la primera revisión visual real se registra en la fase 5.
