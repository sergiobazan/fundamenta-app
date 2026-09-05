import { StatementTable } from "@/components/StatementTable";
import { getStatement, statementNames } from "@/lib/financial";
import type { Filing } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

export const metadata = { title: "Comparación anual de estados financieros" };

export default async function StatementComparisonPage({ params, searchParams }: {
  params: Promise<{ smvRpj: string; statementType: string }>;
  searchParams: Promise<{ year?: string; scope?: string }>;
}) {
  const { smvRpj, statementType } = await params;
  const requested = await searchParams;
  const year = Number(requested.year || 2025);
  const scope = requested.scope || "consolidated";
  if (!["balance_sheet", "income_statement", "cash_flow"].includes(statementType)
    || !Number.isInteger(year) || year < 2000 || year > 2100
    || !["individual", "consolidated"].includes(scope)) notFound();
  const back = `/empresas/${smvRpj}/estados/${statementType}?year=${year}&scope=${scope}`;
  let statement;
  try {
    statement = await getStatement(smvRpj, statementType as Filing["statement_type"], year, scope as "individual" | "consolidated");
  } catch {
    return <section className="comparison-unavailable"><h1>Comparación no disponible</h1><p>No se pudo cargar el estado financiero solicitado.</p><Link href={back}>Volver al estado financiero</Link></section>;
  }
  const filing = statement.filing;
  const title = statementNames[filing.statement_type];
  const scale = { unknown: "Escala no verificada", units: "Unidades", thousands: "Miles", millions: "Millones" }[filing.reported_scale];
  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan"><Link href="/empresas">Empresas</Link><span>/</span><Link href={`/empresas/${smvRpj}`}>{filing.legal_name}</Link><span>/</span><Link href={back}>{title}</Link><span>/</span><b>Comparar años</b></nav>
    <header className="statement-header"><div><span className="overline">COMPARACIÓN ANUAL · {title}</span><h1>{year} vs. {year - 1}</h1><p>{filing.legal_name} · {scope === "individual" ? "Individual" : "Consolidado"} · {filing.currency_code} · {scale}</p></div><Link className="document-button" href={back}>Volver al estado ←</Link></header>
    {filing.scale_source_url && <a className="document-button" href={filing.scale_source_url} target="_blank" rel="noreferrer">Abrir PDF oficial ↗</a>}
    <StatementTable facts={statement.facts} year={year} unverifiedScale={filing.reported_scale === "unknown"} compare />
  </>;
}
