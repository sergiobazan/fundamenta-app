import type { Metric } from "@/lib/types";

const conceptNames: Record<string, string> = {
  cash_and_cash_equivalents: "Efectivo y equivalentes",
  current_assets: "Activos corrientes",
  current_borrowings: "Deuda financiera corriente",
  current_liabilities: "Pasivos corrientes",
  gross_profit: "Utilidad bruta",
  net_profit: "Utilidad neta",
  non_current_borrowings: "Deuda financiera no corriente",
  operating_cash_flow: "Flujo de efectivo operativo",
  operating_profit: "Utilidad operativa",
  purchases_property_plant_equipment: "Compras de propiedad, planta y equipo",
  revenue: "Ingresos",
  total_assets: "Activos totales",
  total_equity: "Patrimonio total",
  total_liabilities: "Pasivos totales",
};

const formulaNames: Record<string, string> = {
  revenue_growth: "(Ingresos actuales / Ingresos comparativos) - 1",
  gross_margin: "Utilidad bruta / Ingresos",
  operating_margin: "Utilidad operativa / Ingresos",
  net_margin: "Utilidad neta / Ingresos",
  current_ratio: "Activos corrientes / Pasivos corrientes",
  working_capital: "Activos corrientes − pasivos corrientes",
  total_debt: "Deuda corriente + deuda no corriente",
  net_debt: "Deuda corriente + deuda no corriente − efectivo",
  debt_to_equity: "Deuda financiera total / Patrimonio",
  liabilities_to_equity: "Pasivos totales / Patrimonio",
  return_on_assets: "Utilidad neta / Promedio de activos actuales y comparativos",
  return_on_equity: "Utilidad neta / Promedio del patrimonio actual y comparativo",
  operating_cash_flow_margin: "Flujo de efectivo operativo / Ingresos",
  free_cash_flow: "Flujo operativo + compras de propiedad, planta y equipo",
  free_cash_flow_margin: "Flujo de caja libre / Ingresos",
};

const metricsUsingComparative = new Set([
  "revenue_growth",
  "return_on_assets",
  "return_on_equity",
]);

export function formatMetric(metric: Metric) {
  if (metric.status !== "computed" || metric.value === null) return "No disponible";
  const value = Number(metric.value);
  if (metric.value_kind === "percentage") {
    return new Intl.NumberFormat("es-PE", {
      style: "percent",
      maximumFractionDigits: 1,
    }).format(value);
  }
  if (metric.value_kind === "ratio") {
    return `${new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(value)}×`;
  }
  const divisor = metric.value_scale === "thousands" ? 1000 : 1;
  const prefix = metric.currency_code === "USD" ? "US$ " : metric.currency_code === "PEN" ? "S/ " : "";
  const suffix = metric.value_scale === "thousands" || metric.value_scale === "millions" ? " M" : "";
  return `${prefix}${new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 }).format(value / divisor)}${suffix}`;
}

function formatInput(
  value: string | number | null,
  currencyCode: string | null,
  scale: Metric["inputs"][string]["scale"],
) {
  if (value === null) return "No reportado";
  const number = Number(value);
  const prefix = currencyCode === "USD" ? "US$ " : currencyCode === "PEN" ? "S/ " : "";
  const displayValue = scale === "thousands" ? number / 1000 : number;
  const suffix = scale === "thousands" || scale === "millions" ? " M" : "";
  return `${prefix}${new Intl.NumberFormat("es-PE", { maximumFractionDigits: 3 }).format(displayValue)}${suffix}`;
}

function MetricExplanation({ metric }: { metric: Metric }) {
  const inputs = Object.entries(metric.inputs);
  const showComparative = metricsUsingComparative.has(metric.metric_code);

  return <div className="metric-explanation">
    <div className="metric-formula">
      <span>Cómo se calcula</span>
      <b>{formulaNames[metric.metric_code] ?? metric.formula_expression}</b>
    </div>

    {inputs.length > 0 && <div className="metric-inputs">
      <span>Datos utilizados</span>
      <div className="metric-input-list" aria-label={`Insumos de ${metric.display_name}`}>
        {inputs.map(([concept, input]) => <div className="metric-input-item" key={concept}>
          <b>{conceptNames[concept] ?? concept.replaceAll("_", " ")}</b>
          <dl>
            <div><dt>Actual</dt><dd>{formatInput(input.current, input.currency_code, input.scale)}</dd></div>
            {showComparative && <div><dt>Comparativo</dt><dd>{formatInput(input.comparative, input.currency_code, input.scale)}</dd></div>}
          </dl>
        </div>)}
      </div>
    </div>}

    {metric.status === "not_available" && <p className="metric-unavailable">Motivo: {metric.reason}</p>}
    <div className="metric-result"><span>Resultado</span><b>{formatMetric(metric)}</b><small>Fórmula versión {metric.formula_version}</small></div>
  </div>;
}

export function MetricCard({
  metric,
  featured = false,
  sourceUrl,
  sourceLabel,
}: {
  metric: Metric;
  featured?: boolean;
  sourceUrl?: string | null;
  sourceLabel?: string;
}) {
  return <article className={`metric-card ${featured ? "featured" : ""}`}>
    <div className="metric-title"><span>{metric.display_name}</span><i>{metric.status === "computed" ? "Verificado" : "Pendiente"}</i></div>
    <strong>{formatMetric(metric)}</strong>
    <p>{metric.description}</p>
    <details>
      <summary>Ver cálculo e insumos <span aria-hidden="true">+</span></summary>
      <MetricExplanation metric={metric} />
    </details>
    {sourceUrl && <a className="metric-source" href={sourceUrl} target="_blank" rel="noreferrer">↗ {sourceLabel || "Documento financiero oficial"}</a>}
  </article>;
}
