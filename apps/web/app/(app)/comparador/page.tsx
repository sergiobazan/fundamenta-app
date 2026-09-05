import { formatMetric } from "@/components/MetricCard";
import { getCompanies, getFilings, getSummary } from "@/lib/financial";
import type { Filing, Summary } from "@/lib/types";
import Link from "next/link";

export const metadata = { title: "Comparador financiero" };

const metricOrder = [
  "revenue_growth",
  "gross_margin",
  "operating_margin",
  "net_margin",
  "current_ratio",
  "working_capital",
  "total_debt",
  "net_debt",
  "debt_to_equity",
  "liabilities_to_equity",
  "return_on_assets",
  "return_on_equity",
  "operating_cash_flow_margin",
  "free_cash_flow",
  "free_cash_flow_margin",
];

type ComparableCompany = {
  summary: Summary;
  filings: Filing[];
};

function representativeFiling(company: ComparableCompany) {
  return company.filings.find((filing) =>
    filing.fiscal_year === company.summary.period.year &&
    filing.period_code === company.summary.period.period_code &&
    filing.scope === company.summary.period.scope &&
    filing.statement_type === "balance_sheet"
  );
}

export default async function ComparatorPage({
  searchParams,
}: {
  searchParams: Promise<{ left?: string; right?: string }>;
}) {
  const requested = await searchParams;
  const companies = await getCompanies();
  const loaded = (await Promise.all(companies.map(async (company) => {
    if (!company.has_analysis || !company.latest_fiscal_year || !company.preferred_scope) {
      return null;
    }
    try {
      const [summary, filings] = await Promise.all([
        getSummary(company.smv_rpj, company.latest_fiscal_year, company.preferred_scope),
        getFilings(company.smv_rpj),
      ]);
      return { summary, filings };
    } catch {
      return null;
    }
  }))).filter((company): company is ComparableCompany => company !== null);

  if (loaded.length < 2) {
    return <section className="comparison-empty"><span className="overline">COMPARADOR</span><h1>Aún faltan empresas compatibles.</h1><p>Se necesitan al menos dos compañías con métricas calculadas para el mismo corte.</p><Link className="document-button" href="/empresas">Volver a empresas →</Link></section>;
  }

  const allowed = new Set(loaded.map((company) => company.summary.company.smv_rpj));
  const leftRpj = requested.left && allowed.has(requested.left) ? requested.left : loaded[0].summary.company.smv_rpj;
  const rightFallback = loaded.find((company) => company.summary.company.smv_rpj !== leftRpj)!.summary.company.smv_rpj;
  const rightRpj = requested.right && allowed.has(requested.right) && requested.right !== leftRpj ? requested.right : rightFallback;
  const left = loaded.find((company) => company.summary.company.smv_rpj === leftRpj)!;
  const right = loaded.find((company) => company.summary.company.smv_rpj === rightRpj)!;
  const leftFiling = representativeFiling(left);
  const rightFiling = representativeFiling(right);
  const formulasMatch = left.summary.metrics.every((metric) => {
    const counterpart = right.summary.metrics.find((candidate) => candidate.metric_code === metric.metric_code);
    return counterpart?.formula_version === metric.formula_version;
  });
  const compatible = Boolean(
    leftFiling && rightFiling &&
    left.summary.period.year === right.summary.period.year &&
    left.summary.period.period_code === right.summary.period.period_code &&
    left.summary.period.scope === right.summary.period.scope &&
    leftFiling.currency_code === rightFiling.currency_code &&
    leftFiling.reported_scale !== "unknown" &&
    leftFiling.reported_scale === rightFiling.reported_scale &&
    formulasMatch
  );

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan"><Link href="/empresas">Empresas</Link><span>/</span><b>Comparador</b></nav>
    <header className="app-header comparison-header"><div><span className="overline">COMPARACIÓN HOMOGÉNEA</span><h1>Comparador financiero</h1><p>Dos empresas, el mismo corte y las mismas fórmulas. Sin convertir una diferencia en recomendación.</p></div></header>

    <form className="comparison-picker" action="/comparador" method="get">
      <label><span>Empresa A</span><select name="left" defaultValue={leftRpj}>{loaded.map((company) => <option value={company.summary.company.smv_rpj} key={company.summary.company.smv_rpj}>{company.summary.company.legal_name}</option>)}</select></label>
      <span className="comparison-swap" aria-hidden="true">⇄</span>
      <label><span>Empresa B</span><select name="right" defaultValue={rightRpj}>{loaded.map((company) => <option value={company.summary.company.smv_rpj} key={company.summary.company.smv_rpj}>{company.summary.company.legal_name}</option>)}</select></label>
      <button type="submit">Comparar</button>
    </form>

    <section className={`compatibility-banner ${compatible ? "compatible" : "incompatible"}`}>
      <span>{compatible ? "✓" : "!"}</span><div><b>{compatible ? "Datos comparables" : "Comparación bloqueada"}</b><p>{compatible ? `${left.summary.period.year} · Anual · ${left.summary.period.scope === "consolidated" ? "Consolidado" : "Individual"} · ${leftFiling?.currency_code} en ${leftFiling?.reported_scale === "thousands" ? "miles" : leftFiling?.reported_scale} · Fórmula v${left.summary.metrics[0]?.formula_version}` : "El periodo, alcance, moneda, escala o versión de fórmula no coincide. No se muestran diferencias potencialmente engañosas."}</p></div>
    </section>

    {compatible && <section className="comparison-table-wrap">
      <table className="comparison-table">
        <thead><tr><th>Indicador</th><th><Link href={`/empresas/${leftRpj}`}>{left.summary.company.legal_name}</Link><small>SMV {leftRpj}</small></th><th><Link href={`/empresas/${rightRpj}`}>{right.summary.company.legal_name}</Link><small>SMV {rightRpj}</small></th></tr></thead>
        <tbody>{metricOrder.map((code) => {
          const leftMetric = left.summary.metrics.find((metric) => metric.metric_code === code);
          const rightMetric = right.summary.metrics.find((metric) => metric.metric_code === code);
          if (!leftMetric || !rightMetric) return null;
          return <tr key={code}><td><b>{leftMetric.display_name}</b><small>{leftMetric.description}</small></td><td><strong>{formatMetric(leftMetric)}</strong><span>{leftMetric.status === "computed" ? "Verificado" : leftMetric.reason}</span></td><td><strong>{formatMetric(rightMetric)}</strong><span>{rightMetric.status === "computed" ? "Verificado" : rightMetric.reason}</span></td></tr>;
        })}</tbody>
      </table>
    </section>}

    <section className="comparison-sources"><div><span className="overline">FUENTES PRIMARIAS</span><p>Cada columna conserva su propia referencia. Fundamenta no mezcla documentos ni rellena cuentas ausentes.</p></div><div>{leftFiling?.scale_source_url&&<a href={leftFiling.scale_source_url} target="_blank" rel="noreferrer">{left.summary.company.legal_name} ↗</a>}{rightFiling?.scale_source_url&&<a href={rightFiling.scale_source_url} target="_blank" rel="noreferrer">{right.summary.company.legal_name} ↗</a>}</div></section>
    <footer className="data-footer"><span>Una cifra mayor no implica automáticamente una inversión mejor.</span><Link href="/empresas">Auditar estados y fórmulas ↗</Link></footer>
  </>;
}
