import { AnnualMetricComparison } from "@/components/AnnualMetricComparison";
import { getSummary } from "@/lib/financial";
import Link from "next/link";
import { notFound } from "next/navigation";

export const metadata = { title: "Comparación anual de métricas" };

export default async function MetricComparisonPage({ params, searchParams }: {
  params: Promise<{ smvRpj: string }>;
  searchParams: Promise<{ year?: string; scope?: string }>;
}) {
  const { smvRpj } = await params;
  const requested = await searchParams;
  const year = Number(requested.year || 2025);
  const scope = requested.scope || "consolidated";
  if (!Number.isInteger(year) || year < 2000 || year > 2100 || !["individual", "consolidated"].includes(scope)) notFound();
  let summary;
  try {
    summary = await getSummary(smvRpj, year, scope as "individual" | "consolidated");
  } catch {
    return <section className="comparison-unavailable"><h1>Comparación no disponible</h1><p>No se pudieron cargar las métricas de {year} para el alcance solicitado.</p><Link href={`/empresas/${smvRpj}`}>Volver a la empresa</Link></section>;
  }
  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan"><Link href="/empresas">Empresas</Link><span>/</span><Link href={`/empresas/${smvRpj}`}>{summary.company.legal_name}</Link><span>/</span><b>Comparar métricas</b></nav>
    <header className="statement-header"><div><span className="overline">COMPARACIÓN ANUAL · MÉTRICAS</span><h1>{year} vs. {year - 1}</h1><p>{summary.company.legal_name} · {scope === "individual" ? "Individual" : "Consolidado"}</p></div><Link className="document-button" href={`/empresas/${smvRpj}`}>Volver al análisis ←</Link></header>
    <AnnualMetricComparison metrics={summary.metrics} year={year} />
  </>;
}
