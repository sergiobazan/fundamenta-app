import { getNoteComparison, noteTopicNames } from "@/lib/financial";
import type { NarrativeComparisonItem, NoteTopic } from "@/lib/types";
import Link from "next/link";

export const metadata = {
  title: "Comparación de notas financieras",
  description: "Notas auditadas de dos períodos comparadas con evidencia citada por página.",
};

const topics = Object.entries(noteTopicNames) as [NoteTopic, string][];

export default async function NoteComparisonPage({
  params,
  searchParams,
}: {
  params: Promise<{ smvRpj: string }>;
  searchParams: Promise<{
    topic?: string;
    all?: string;
    currentYear?: string;
    scope?: string;
  }>;
}) {
  const { smvRpj } = await params;
  const requested = await searchParams;
  const topic = topics.some(([value]) => value === requested.topic)
    ? requested.topic as NoteTopic
    : undefined;
  const showAll = requested.all === "1";
  const parsedCurrentYear = Number(requested.currentYear);
  const currentYear = Number.isInteger(parsedCurrentYear) && parsedCurrentYear >= 2001
    && parsedCurrentYear <= 2100 ? parsedCurrentYear : 2025;
  const scope = requested.scope === "individual" ? "individual" : "consolidated";
  let data;
  try {
    data = await getNoteComparison(smvRpj, {
      currentYear,
      previousYear: currentYear - 1,
      scope,
      topic,
      priorityOnly: !showAll,
    });
  } catch {
    return <ComparisonUnavailable smvRpj={smvRpj} currentYear={currentYear} scope={scope} />;
  }

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan">
      <Link href="/empresas">Empresas</Link><span>/</span>
      <Link href={`/empresas/${smvRpj}`}>{smvRpj}</Link><span>/</span>
      <Link href={`/empresas/${smvRpj}/notas`}>Notas</Link><span>/</span><b>Comparar períodos</b>
    </nav>

    <header className="app-header note-comparison-header">
      <div><span className="overline">COMPARACIÓN DOCUMENTAL CITADA</span><h1>{data.current_year} frente a {data.previous_year}</h1><p>{data.legal_name} · Anual · {scope === "consolidated" ? "Consolidado" : "Individual"}. Las equivalencias se determinan por títulos; los hechos permanecen separados por período.</p></div>
      <span className={`summary-confidence ${data.confidence}`}>Emparejamiento · {confidenceLabel(data.confidence)}</span>
    </header>

    <section className="comparison-coverage" aria-label="Cobertura de la comparación">
      <div><span>Notas actuales</span><b>{data.coverage.current_total}</b></div>
      <div><span>Equivalencias</span><b>{data.coverage.matched}</b></div>
      <div><span>Sólo en {data.current_year}</span><b>{data.coverage.current_only}</b></div>
      <div><span>Sólo en {data.previous_year}</span><b>{data.coverage.previous_only}</b></div>
    </section>

    <section className="comparison-boundary">
      <span>!</span><div><b>Lectura comparativa, no conclusión de inversión</b><p>Una diferencia entre extractos no demuestra por sí sola un cambio económico. No se generan causalidad, materialidad ni recomendaciones.</p></div>
    </section>

    <section className="comparison-documents">
      <a href={data.current_source_url} target="_blank" rel="noreferrer"><span>{data.current_year} · versión {data.current_document_version}</span><b>{data.current_document_name}</b><small>Abrir PDF oficial ↗</small></a>
      <a href={data.previous_source_url} target="_blank" rel="noreferrer"><span>{data.previous_year} · versión {data.previous_document_version}</span><b>{data.previous_document_name}</b><small>Abrir PDF oficial ↗</small></a>
    </section>

    <form className="note-comparison-filters" action={`/empresas/${smvRpj}/notas/comparar`} method="get">
      <input type="hidden" name="currentYear" value={currentYear} />
      <input type="hidden" name="scope" value={scope} />
      <label><span>Tema</span><select name="topic" defaultValue={topic ?? ""}><option value="">Todos los temas</option>{topics.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label className="priority-filter"><input type="checkbox" name="all" value="1" defaultChecked={showAll} /><span>Mostrar también notas no prioritarias</span></label>
      <button type="submit">Aplicar</button>
      {(topic || showAll) && <Link href={`/empresas/${smvRpj}/notas/comparar?currentYear=${currentYear}&scope=${scope}`}>Restablecer</Link>}
      <span className="visible-count">{data.visible_items} comparaciones visibles</span>
    </form>

    {data.items.length ? <div className="narrative-comparison-list">
      {data.items.map((item, index) => <ComparisonCard item={item} currentYear={data.current_year} previousYear={data.previous_year} smvRpj={smvRpj} scope={scope} key={`${item.current?.note_number ?? "x"}-${item.previous?.note_number ?? "x"}-${index}`} />)}
    </div> : <section className="empty-result"><b>No hay comparaciones con esos filtros.</b><p>Muestra todas las notas o selecciona otro tema.</p></section>}

    <footer className="comparison-audit-footer"><span>{data.confidence_reason}</span><span>Corte: {formatDate(data.information_cutoff)} · Emparejador v{data.generator_version}</span></footer>
  </>;
}

function ComparisonUnavailable({ smvRpj, currentYear, scope }: { smvRpj: string; currentYear: number; scope: "individual" | "consolidated" }) {
  return <section className="comparison-unavailable">
    <span>COMPARACIÓN EN PREPARACIÓN</span>
    <h1>Los períodos todavía no están listos.</h1>
    <p>La pantalla existe, pero la API aún no terminó de aplicar las migraciones o de procesar las notas 2024. Revisa el arranque del backend y vuelve a intentarlo.</p>
    <div><Link className="document-button" href={`/empresas/${smvRpj}/notas?year=${currentYear}&scope=${scope}`}>Volver a las notas</Link><Link className="document-button" href={`/empresas/${smvRpj}/notas/comparar?currentYear=${currentYear}&scope=${scope}`}>Reintentar</Link></div>
  </section>;
}

function ComparisonCard({ item, currentYear, previousYear, smvRpj, scope }: { item: NarrativeComparisonItem; currentYear: number; previousYear: number; smvRpj: string; scope: "individual" | "consolidated" }) {
  const topic = item.current?.topic ?? item.previous?.topic ?? "other";
  return <article className={`narrative-comparison-card ${item.match_status}`}>
    <header>
      <div><span>{noteTopicNames[topic]}</span><h2>{item.current?.title ?? item.previous?.title}</h2></div>
      <span className={`comparison-match ${item.confidence}`}>{matchLabel(item.match_status)}</span>
    </header>
    <div className="comparison-period-columns">
      <EvidenceColumn note={item.current} year={currentYear} smvRpj={smvRpj} scope={scope} emptyText={`Sin nota equivalente identificada en ${currentYear}.`} />
      <EvidenceColumn note={item.previous} year={previousYear} smvRpj={smvRpj} scope={scope} emptyText={`Sin nota equivalente identificada en ${previousYear}.`} />
    </div>
    <footer><span>{item.confidence_reason}</span><span>{methodLabel(item.match_method)}</span></footer>
  </article>;
}

function EvidenceColumn({ note, year, smvRpj, scope, emptyText }: { note: NarrativeComparisonItem["current"]; year: number; smvRpj: string; scope: "individual" | "consolidated"; emptyText: string }) {
  if (!note) return <section className="comparison-period empty"><div><b>{year}</b></div><p>{emptyText}</p></section>;
  const facts = note.summary?.observed_facts ?? [];
  return <section className="comparison-period">
    <div><b>{year}</b><Link href={`/empresas/${smvRpj}/notas/${note.note_number}?year=${year}&period=A&scope=${scope}`}>Nota {note.note_number} · leer completa →</Link></div>
    <h3>{note.title}</h3>
    {facts.length ? <ol>{facts.map((fact) => <li key={fact.item_order}><p>{fact.text}</p><a href={`${fact.citation.source_url}#page=${fact.citation.page_number}`} target="_blank" rel="noreferrer">Pág. {fact.citation.page_number} del PDF oficial ↗</a></li>)}</ol> : <p className="comparison-no-evidence">El extractor se abstuvo: no encontró narrativa suficientemente legible para citar.</p>}
  </section>;
}

function confidenceLabel(confidence: "high" | "medium" | "low") {
  return { high: "alta", medium: "media", low: "baja" }[confidence];
}

function matchLabel(status: NarrativeComparisonItem["match_status"]) {
  return { matched: "Notas equivalentes", current_only: "Sin equivalente anterior", previous_only: "Sin equivalente actual" }[status];
}

function methodLabel(method: NarrativeComparisonItem["match_method"]) {
  return { normalized_title: "Título equivalente", title_similarity: "Título similar", none: "Sin coincidencia automática" }[method];
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}
