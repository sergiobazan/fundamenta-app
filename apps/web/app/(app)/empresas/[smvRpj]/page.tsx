import { MetricCard } from "@/components/MetricCard";
import { EventTimeline } from "@/components/EventTimeline";
import { getEvents, getFilings, getNotes, getSummary, statementNames } from "@/lib/financial";
import type { Filing, NotesResponse } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

const statementOrder: Filing["statement_type"][] = ["balance_sheet", "income_statement", "cash_flow"];

function companyMark(legalName: string) {
  if (legalName.toLowerCase().includes("buenaventura")) return "BVN";
  if (legalName.toLowerCase().includes("minsur")) return "MIN";
  return legalName.replace(/[^a-záéíóúñ ]/gi, "").split(/\s+/).filter((word) => word.length > 3).slice(0, 3).map((word) => word[0]).join("").toUpperCase();
}

export const metadata = { title: "Detalle de empresa" };

export default async function CompanyPage({ params }: { params: Promise<{ smvRpj: string }> }) {
  const { smvRpj } = await params;
  let summary;
  let filings;
  let events;
  let notes: NotesResponse | null;
  try {
    [summary, filings, events, notes] = await Promise.all([
      getSummary(smvRpj),
      getFilings(smvRpj),
      getEvents({ companyRpj: smvRpj, limit: 3 }),
      getNotes(smvRpj).catch(() => null),
    ]);
  } catch {
    notFound();
  }

  const currentFilings = statementOrder.map((type) => filings.find(
    (filing) => filing.statement_type === type &&
      filing.fiscal_year === summary.period.year &&
      filing.scope === summary.period.scope,
  )).filter(Boolean) as Filing[];
  const sourceUrl = currentFilings.find((filing) => filing.scale_source_url)?.scale_source_url;
  const sourceLabel = `Presentación financiera ${summary.period.year} de ${summary.company.legal_name}`;
  const passedValidations = currentFilings.reduce((count, filing) => count + (filing.failed_validations === 0 ? 1 : 0), 0);

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan"><Link href="/empresas">Empresas</Link><span>/</span><b>{summary.company.legal_name}</b></nav>
    <header className="company-detail-header"><div className="company-mark large">{companyMark(summary.company.legal_name)}</div><div><span className="overline">SMV {summary.company.smv_rpj} · RUC {summary.company.ruc}</span><h1>{summary.company.legal_name}</h1><p>{summary.company.sector || "Minería"} · Información anual consolidada</p></div>{sourceUrl&&<a className="document-button" href={sourceUrl} target="_blank" rel="noreferrer">Documento original <span>↗</span></a>}</header>
    <section className="company-facts"><div><span>Periodo analizado</span><b>{summary.period.year} · Anual</b></div><div><span>Estados disponibles</span><b>{currentFilings.length} de 3</b></div><div><span>Indicadores calculados</span><b>{summary.metrics.filter((metric) => metric.status === "computed").length} de {summary.metrics.length}</b></div><div><span>Calidad</span><b className="quality-text">● {passedValidations === currentFilings.length ? "Verificada" : "Parcial"}</b></div></section>

    <section className="company-section"><div className="content-head"><div><span className="overline">ESTADOS FINANCIEROS</span><h2>Explora las cuentas reportadas</h2><p>Cada vista conserva etiqueta original, concepto normalizado, moneda, escala y fuente.</p></div></div><div className="statement-cards">{currentFilings.map((filing) => <Link href={`/empresas/${smvRpj}/estados/${filing.statement_type}`} key={filing.statement_type}><div className="statement-icon">{filing.statement_type === "balance_sheet" ? "▤" : filing.statement_type === "income_statement" ? "↗" : "≈"}</div><span>{filing.fiscal_year} · {filing.scope === "consolidated" ? "Consolidado" : "Individual"}</span><h3>{statementNames[filing.statement_type]}</h3><p>{filing.mapped_facts} de {filing.facts} cuentas normalizadas</p><div className="statement-card-foot"><i className={filing.failed_validations ? "failed" : ""}></i>{filing.failed_validations ? `${filing.failed_validations} alertas` : "Controles aprobados"}<b>→</b></div></Link>)}</div></section>

    {notes && <section className="company-section"><div className="content-head"><div><span className="overline">NOTAS AUDITADAS</span><h2>El contexto detrás de las cifras</h2><p>{notes.document.notes_count} notas extraídas y referenciadas por página desde el PDF oficial.</p></div><Link href={`/empresas/${smvRpj}/notas`}>Explorar todas las notas ↗</Link></div><Link className="company-notes-callout" href={`/empresas/${smvRpj}/notas`}><div><span>Documento consolidado · {notes.document.fiscal_year}</span><h3>Políticas, estimaciones, deuda, contingencias y hechos posteriores</h3><p>{notes.notes.filter((note) => note.is_priority).length} notas marcadas como relevantes para comenzar el análisis.</p></div><b>Leer notas →</b></Link></section>}

    <section className="company-section"><div className="content-head"><div><span className="overline">TODOS LOS INDICADORES</span><h2>15 métricas reproducibles</h2><p>Fórmula, versión, insumos y documento fuente visibles.</p></div><Link href={`/comparador?left=${summary.company.smv_rpj}`}>Comparar empresa ↗</Link></div><div className="metric-grid all-metrics">{summary.metrics.map((metric) => <MetricCard key={metric.metric_code} metric={metric} sourceUrl={sourceUrl} sourceLabel={sourceLabel} />)}</div></section>
    <section className="company-section"><div className="content-head"><div><span className="overline">CONTEXTO OFICIAL</span><h2>Eventos recientes</h2><p>Comunicaciones oficiales vinculadas a esta empresa.</p></div><Link href={`/eventos?company=${summary.company.smv_rpj}`}>Ver todos los eventos ↗</Link></div><EventTimeline events={events} compact /></section>
    <footer className="data-footer"><span>Los indicadores no equivalen a una recomendación de inversión.</span>{sourceUrl&&<a href={sourceUrl} target="_blank" rel="noreferrer">Fuente primaria: presentación oficial {summary.period.year} ↗</a>}</footer>
  </>;
}
