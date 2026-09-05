import { formatMetric } from "@/components/MetricCard";
import type { Metric } from "@/lib/types";

export function AnnualMetricComparison({ metrics, year }: { metrics: Metric[]; year: number }) {
  return <section className="annual-comparison" aria-label="Comparación anual de métricas">
    <p>El año anterior se recalcula con las cifras comparativas publicadas en {year}; pueden incluir reclasificaciones o ajustes. No es una consulta al informe original de {year - 1}.</p>
    <p>La variación porcentual se omite con base cero o negativa. Los márgenes y rentabilidades se comparan en puntos porcentuales (pp). Subir o bajar no implica una mejora o deterioro.</p>
    <div className="statement-table-wrap"><table className="statement-table">
      <thead><tr><th>Métrica</th><th>{year}</th><th>{year - 1}</th><th>Diferencia</th><th>Variación %</th></tr></thead>
      <tbody>{metrics.map(metric => {
        const previous = metric.comparative ? { ...metric, ...metric.comparative } : null;
        const comparable = previous?.status === "computed" && metric.status === "computed"
          && previous.value !== null && metric.value !== null
          && previous.currency_code === metric.currency_code && previous.value_scale === metric.value_scale;
        const difference = comparable ? Number(metric.value) - Number(previous!.value) : null;
        const unknown = metric.value_kind === "monetary" && (metric.value_scale === null || previous?.value_scale === null);
        return <tr key={metric.metric_code}>
          <td><b>{metric.display_name}</b>{unknown && <small>Escala no verificada · magnitudes reportadas</small>}</td>
          <td>{formatMetric(metric)}</td><td>{previous ? formatMetric(previous) : "No disponible"}
            {previous?.status === "not_available" && <small>{previous.reason}</small>}</td>
          <td>{difference === null ? "—" : metric.value_kind === "percentage"
            ? `${new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1, signDisplay: "exceptZero" }).format(difference * 100)} pp`
            : formatMetric({ ...metric, value: difference })}</td>
          <td>{difference !== null && Number(previous!.value) > 0 && metric.value_kind !== "percentage"
            ? new Intl.NumberFormat("es-PE", { style: "percent", maximumFractionDigits: 1, signDisplay: "exceptZero" }).format(difference / Number(previous!.value)) : "—"}</td>
        </tr>;
      })}</tbody>
    </table></div>
  </section>;
}
