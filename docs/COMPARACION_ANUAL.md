# Comparación anual

La página principal y cada estado financiero muestran la misma franja verde de
las notas, con un botón que abre una página independiente. Métricas utiliza
`/empresas/[smvRpj]/comparar`; los estados utilizan
`/empresas/[smvRpj]/estados/[statementType]/comparar`. Los enlaces conservan año
y alcance. Las páginas de comparación incluyen navegación de retorno y muestran
las diferencias directamente, sin desplegables ni interruptores.
La comparación de notas conserva su página y se etiqueta explícitamente como tal.

El año anterior corresponde a las cifras comparativas incluidas en el informe
actual, no a una consulta al informe original anterior. Se conservan su moneda,
alcance y escala, y se advierte sobre posibles reclasificaciones o ajustes.
El backend recalcula las métricas anteriores con el mismo motor y los insumos
comparativos. Crecimiento de ingresos, ROA y ROE quedan sin comparativo porque
necesitan un ejercicio adicional; no se sustituye un promedio por el saldo final.

La diferencia es actual menos anterior; la variación relativa divide esa diferencia
entre el anterior, sólo con base positiva. Márgenes y rentabilidades muestran
puntos porcentuales. Datos ausentes no equivalen a cero. Las escalas desconocidas
conservan su advertencia y las diferencias usan magnitudes reportadas, sin asignar
unidades. Los colores no califican las variaciones como buenas o malas.

No requiere migración ni reprocesamiento. Requiere desplegar backend y frontend.
