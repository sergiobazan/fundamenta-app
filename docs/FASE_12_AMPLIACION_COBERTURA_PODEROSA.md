# Fase 12: ampliación progresiva de cobertura — Poderosa

## Resultado

Compañía Minera Poderosa S.A.A. (`B20041`) es la cuarta empresa publicada. Se
incorporó con estados financieros anuales consolidados 2025, métricas deterministas y
notas auditadas 2025–2024. La moneda se conserva como PEN y no se convierte ni se
mezcla silenciosamente con las empresas que reportan en USD.

## Fuentes oficiales verificadas

- [Poderosa consolidado auditado 2025](https://www.smv.gob.pe/ConsultasP8/temp/EEFF%20Anuales%20Auditados%20Consolidados%202025.pdf)
- [Poderosa consolidado auditado 2024](https://www.smv.gob.pe/ConsultasP8/temp/EEFF%20Anuales%20Auditados%20Consolidados%202024.pdf)

Los estados estructurados provienen del servicio oficial de información financiera de
la SMV. El PDF 2025 confirma presentación en miles de soles (`S/(000)`). El balance
consolidado registra activos por S/ 3 187 017 miles, cifra contrastada antes de publicar
el corte.

## Datos incorporados

| Control | Resultado |
|---|---:|
| Estados estructurados 2025 | 3 |
| Hechos financieros normalizados | 200 |
| Métricas calculadas | 15 de 15 |
| Métricas no disponibles | 0 |
| Validaciones contables fallidas | 0 |
| Notas 2025 | 38 |
| Notas 2024 | 39 |
| Páginas PDF 2025 / 2024 | 79 / 87 |

La comparación narrativa emparejó 33 notas; conserva visibles 5 notas exclusivas de
2025 y 6 exclusivas de 2024. Su estado es `partial` con confianza media, por lo que la
interfaz no presenta el conjunto como una comparación total.

## Hallazgo y corrección del extractor

Poderosa denomina su última revelación 2025 “Eventos posteriores…”, mientras que en
2024 usa “Hechos posteriores”. Se amplió el clasificador para reconocer ambas formas,
se agregó una migración idempotente para corregir documentos ya almacenados y se
versionó nuevamente el emparejador. Las dos notas ahora se muestran como equivalentes
con similitud 0,88 y permanecen enlazadas a sus páginas de origen.

## Compatibilidad de comparación

Buenaventura, Minsur y Volcan reportan el corte publicado en miles de USD. Poderosa lo
hace en miles de PEN. El comparador debe bloquear una selección entre Poderosa y una
empresa en USD, explicar la incompatibilidad y no renderizar cifras aparentemente
comparables.

## Despliegue

El bootstrap espera cuatro empresas, doce estados, sesenta métricas y ocho documentos
de notas. En PostgreSQL vacío aplica automáticamente doce migraciones y carga todo el
corte. En una base existente, las migraciones 010 a 012 reclasifican “Eventos
posteriores”, excluyen un anexo suplementario detectado tras el cierre de la última
nota y recuperan la palabra final de su título, dividida en otra línea por el PDF. La
versión 5 del comparador regenera las equivalencias sin alterar los PDF originales.

## Siguiente lote

Las cuatro empresas restantes no ofrecen necesariamente un estado consolidado. Antes
de publicarlas se debe generalizar el corte por empresa para representar explícitamente
`individual` o `consolidated` en ingestión, consultas y rutas de interfaz. Ningún estado
individual se etiquetará como consolidado para completar una cuota de cobertura.
