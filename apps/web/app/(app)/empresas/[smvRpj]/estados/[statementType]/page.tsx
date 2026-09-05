import { StatementTable } from "@/components/StatementTable";
import { AnnualComparisonBanner } from "@/components/AnnualComparisonBanner";
import { getStatement, statementNames } from "@/lib/financial";
import type { Filing } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

const validTypes = new Set<Filing["statement_type"]>(["balance_sheet", "income_statement", "cash_flow"]);

export const metadata = { title: "Estado financiero" };

export default async function StatementPage({
  params,
  searchParams,
}: {
  params: Promise<{ smvRpj: string; statementType: string }>;
  searchParams: Promise<{ year?: string; scope?: string }>;
}) {
  const { smvRpj, statementType } = await params;
  const requested = await searchParams;
  if (!validTypes.has(statementType as Filing["statement_type"])) notFound();
  const year = Number(requested.year || 2025);
  const scope = requested.scope === "individual" ? "individual" : "consolidated";
  if (!Number.isInteger(year) || year < 2000 || year > 2100) notFound();
  let statement;
  try {
    statement = await getStatement(smvRpj, statementType as Filing["statement_type"], year, scope);
  } catch {
    notFound();
  }
  const filing = statement.filing;
  const passed = statement.validations.filter((validation) => validation.status === "passed").length;

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan"><Link href="/empresas">Empresas</Link><span>/</span><Link href={`/empresas/${smvRpj}`}>{filing.legal_name}</Link><span>/</span><b>{statementNames[filing.statement_type]}</b></nav>
    <header className="statement-header"><div><span className="overline">ESTADO FINANCIERO · INFORMACIÓN OFICIAL</span><h1>{statementNames[filing.statement_type]}</h1><p>{filing.legal_name}</p></div><a className="document-button" href={filing.scale_source_url || "#fuente"} target={filing.scale_source_url ? "_blank" : undefined} rel="noreferrer">Abrir fuente <span>↗</span></a></header>
    <section className="statement-context"><div><span>Periodo</span><b>{filing.fiscal_year} · Anual</b></div><div><span>Alcance</span><b>{filing.scope === "consolidated" ? "Consolidado" : "Individual"}</b></div><div><span>Moneda y escala</span><b>{filing.currency_code} · {filing.reported_scale === "thousands" ? "Miles" : filing.reported_scale}</b></div><div><span>Validaciones</span><b className="quality-text">● {passed}/{statement.validations.length} aprobadas</b></div></section>
    <section className="source-banner" id="fuente"><div><span>↗</span><p><b>Contexto de fuente para toda la tabla</b>Los valores corresponden al estado anual {filing.scope === "consolidated" ? "consolidado" : "individual"} presentado por el emisor. La API preserva proveedor, operación, fecha de recuperación y huella del payload.</p></div><dl><dt>Proveedor</dt><dd>{filing.provider}</dd><dt>Recuperado</dt><dd>{new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeZone: "America/Lima" }).format(new Date(filing.retrieved_at))}</dd><dt>Huella</dt><dd title={filing.payload_sha256}>{filing.payload_sha256.slice(0, 12)}…</dd></dl></section>
    <AnnualComparisonBanner title={`${filing.legal_name} · ${statementNames[filing.statement_type]}`} year={filing.fiscal_year} scope={filing.scope} href={`/empresas/${smvRpj}/estados/${statementType}/comparar?year=${year}&scope=${scope}`} sourceUrl={filing.scale_source_url} />
    <section className="statement-content"><StatementTable facts={statement.facts} year={filing.fiscal_year} unverifiedScale={filing.reported_scale === "unknown"} /></section>
    <section className="validation-section"><div><span className="overline">CONTROLES AUTOMÁTICOS</span><h2>Resultado de validaciones</h2></div><div>{statement.validations.map((validation) => <article key={validation.rule_code}><i className={validation.status}></i><div><b>{validation.rule_code.replaceAll("_", " ")}</b><span>{validation.status === "passed" ? "Aprobado" : validation.status === "failed" ? "Falló" : "No aplicable"}</span></div></article>)}</div></section>
    <footer className="data-footer"><span>Se muestran sólo conceptos normalizados; no se estiman cuentas faltantes.</span>{filing.scale_source_url && <a href={filing.scale_source_url} target="_blank" rel="noreferrer">Documento que confirma la escala ↗</a>}</footer>
  </>;
}
