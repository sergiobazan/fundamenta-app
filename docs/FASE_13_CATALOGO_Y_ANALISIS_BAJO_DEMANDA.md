# Fase 13: catálogo SMV y análisis progresivo bajo demanda

## Resultado

La aplicación dejó de tratar la lista de empresas analizadas como el universo completo.
Al arrancar, consulta los estados anuales individuales y consolidados del servicio de
datos abiertos de la SMV, combina los emisores por RPJ y conserva por separado su
estado de cobertura.

El directorio permite ahora distinguir entre:

- análisis disponible o parcial;
- solicitud en cola o procesándose;
- empresa todavía no analizada;
- fuente que requiere revisión;
- sector no compatible con el MVP.

## Alcance sectorial

La clasificación inicial aplica tres niveles:

1. minería no financiera: análisis completo cuando existen notas oficiales verificadas;
2. otros emisores no financieros: estados y métricas compatibles como análisis básico;
3. bancos, aseguradoras, AFP, fondos y otros formatos financieros especiales: visibles
   en el catálogo, pero sin generación automática.

La clasificación no autoriza a reutilizar una métrica cuando sus conceptos, moneda,
escala o alcance no sean compatibles.

## Cola y persistencia

La migración `013_company_analysis.sql` agrega:

- `company_coverage`, que separa catálogo, soporte sectorial, cobertura y validación;
- `analysis_jobs`, con solicitud, alcance, periodo, progreso, reintentos y resultado;
- `analysis_job_steps`, con las etapas de estados, métricas, documentos y resúmenes.

Un bloqueo transaccional y un índice único parcial evitan dos trabajos activos para la
misma empresa, periodo y alcance. El usuario puede abandonar la página: el estado queda
en PostgreSQL y los trabajos interrumpidos vuelven a `retrying` después de un reinicio.

Cada usuario puede mantener hasta tres solicitudes activas de manera predeterminada.
La creación de un trabajo exige una sesión válida y no acepta URLs proporcionadas por
el usuario.

## Procesamiento progresivo

El worker ejecuta las etapas en orden:

1. descarga y valida los tres estados financieros desde la SMV;
2. calcula únicamente métricas cuyos conceptos sean compatibles;
3. procesa notas del ejercicio actual y anterior si existe una fuente curada;
4. actualiza resúmenes citados y comparaciones narrativas.

Después de estados y métricas, la empresa ya puede aparecer como análisis parcial. Si
falta una URL documental verificada, minería pasa a `review_required`; un emisor con
soporte básico termina como `partial`. En ambos casos se conservan los resultados
seguros y se explica qué falta.

La escala no se infiere desde los importes. Cuando continúa como `unknown`, las razones
compatibles y las métricas monetarias se calculan sobre la magnitud original reportada.
En estas últimas, `value_scale = NULL` significa explícitamente `Escala no verificada`:
la interfaz muestra el valor sin convertirlo, destaca la tarjeta con un borde de alerta
y pide al usuario validar si corresponde a unidades, miles o millones. Nunca se hereda
una escala desde otra métrica o fuente.

## API e interfaz

Se agregaron los contratos:

```text
GET  /companies/{smv_rpj}
GET  /companies/{smv_rpj}/analysis
POST /companies/{smv_rpj}/analysis
```

El `POST` responde `202` para una solicitud nueva y `200` cuando reutiliza un trabajo
activo. La interfaz ofrece `Ver análisis`, `Ver progreso`, `Generar análisis` o
`Próximamente` según cobertura y soporte.

La pantalla de progreso consulta el trabajo periódicamente, muestra las cuatro etapas
y actualiza el panel cuando ya existen resultados consultables.

## Operación

El Blueprint gratuito no incluye un background worker separado. Por ello la API inicia
un hilo de análisis que reclama trabajos mediante `FOR UPDATE SKIP LOCKED`. El servicio
`notes-worker` de Docker Compose también puede procesarlos; el bloqueo de base de datos
permite que ambos convivan sin duplicar una ejecución.

Variables nuevas:

- `COMPANY_CATALOG_SYNC_ON_START`;
- `COMPANY_ANALYSIS_FISCAL_YEAR`;
- `ANALYSIS_WORKER_ENABLED`;
- `ANALYSIS_WORKER_POLL_SECONDS`;
- `ANALYSIS_WORKER_MAX_ATTEMPTS`;
- `ANALYSIS_ACTIVE_JOBS_PER_USER`.

## Verificación

- El servicio oficial respondió para el balance consolidado 2025 con 5 392 filas y 76
  RPJ distintos; el balance individual respondió con 20 358 filas y 273 RPJ distintos.
- 57 pruebas de backend aprobadas.
- Ruff sin errores.
- Sintaxis de la migración 013 validada con un parser PostgreSQL independiente.
- Build de producción de Next.js aprobado, incluida la ruta dinámica de proxy.

La base PostgreSQL local no estaba disponible en el entorno de trabajo, por lo que la
migración y las transacciones reales deben probarse al levantar el stack antes del
despliegue.

## Continuación

1. levantar PostgreSQL y ejecutar una prueba completa de migración, deduplicación y
   recuperación;
2. procesar desde la interfaz una minera que no pertenezca a la carga inicial;
3. medir duración y consumo de cada etapa;
4. automatizar el descubrimiento de notas sólo mediante fuentes oficiales autorizadas;
5. crear la bandeja interna para resolver trabajos `review_required`.
