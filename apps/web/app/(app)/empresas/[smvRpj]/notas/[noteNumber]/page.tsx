import { getNote, noteTopicNames } from "@/lib/financial";
import Link from "next/link";
import { notFound } from "next/navigation";

export const metadata = {
  title: "Detalle de nota financiera",
  description: "Contenido extraído de una nota financiera con referencias al documento oficial.",
};

export default async function NoteDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ smvRpj: string; noteNumber: string }>;
  searchParams: Promise<{ year?: string; period?: string; scope?: string }>;
}) {
  const { smvRpj, noteNumber: rawNoteNumber } = await params;
  const requested = await searchParams;
  const noteNumber = Number(rawNoteNumber);
  const parsedYear = Number(requested.year);
  const year = Number.isInteger(parsedYear) && parsedYear >= 2000 && parsedYear <= 2100
    ? parsedYear
    : 2025;
  const period = ["A", "1", "2", "3", "4"].includes(requested.period ?? "")
    ? requested.period as "A" | "1" | "2" | "3" | "4"
    : "A";
  const scope = requested.scope === "individual" ? "individual" : "consolidated";
  if (!Number.isInteger(noteNumber) || noteNumber < 1) notFound();
  let data;
  try {
    data = await getNote(smvRpj, noteNumber, { year, period, scope });
  } catch {
    notFound();
  }
  const { note, sections } = data;
  const summary = data.summary;

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan">
      <Link href="/empresas">Empresas</Link><span>/</span>
      <Link href={`/empresas/${smvRpj}`}>{smvRpj}</Link><span>/</span>
      <Link href={`/empresas/${smvRpj}/notas`}>Notas</Link><span>/</span><b>Nota {note.note_number}</b>
    </nav>

    <header className="note-detail-header">
      <div><span className="overline">NOTA {note.note_number} · {noteTopicNames[note.topic]}</span><h1>{note.original_title}</h1><p>{note.legal_name} · {note.fiscal_year} · {note.scope === "consolidated" ? "Consolidado" : "Individual"}</p></div>
      <a className="document-button" href={`${note.source_url}#page=${note.start_page}`} target="_blank" rel="noreferrer">Ver en PDF · pág. {note.start_page} ↗</a>
    </header>

    <section className="note-integrity">
      <div><span>Documento</span><b>{note.document_name}</b></div>
      <div><span>Páginas</span><b>{note.start_page}{note.end_page !== note.start_page ? `–${note.end_page}` : ""}</b></div>
      <div><span>Versión</span><b>{note.version}</b></div>
      <div><span>Integridad</span><b title={note.source_sha256}>SHA-256 verificada</b></div>
    </section>

    <div className="note-reading-layout">
      <article className="note-reading">
        {sections.map((section) => <section key={`${section.page_number}-${section.section_order}`}>
          <div className="page-reference"><span>Página {section.page_number}</span><a href={`${note.source_url}#page=${section.page_number}`} target="_blank" rel="noreferrer">Contrastar en fuente ↗</a></div>
          <div className="extracted-copy">{section.content_text}</div>
        </section>)}
      </article>
      <aside className="note-caution"><b>Cómo usar esta nota</b><p>Busca condiciones, supuestos y riesgos que expliquen las cifras. Los cuadros pueden perder estructura al extraerse: confirma siempre los importes en la página enlazada.</p><Link href={`/empresas/${smvRpj}/notas`}>← Volver a todas las notas</Link></aside>
    </div>

    {summary ? <section className="cited-summary" aria-labelledby="cited-summary-title">
      <header className="cited-summary-header">
        <div><span className="overline">LECTURA RÁPIDA · SIN IA</span><h2 id="cited-summary-title">Resumen citado</h2><p>Selección extractiva de hechos presentes en la nota. Cada punto lleva a su página de origen.</p></div>
        <span className={`summary-confidence ${summary.confidence}`}>Confianza {confidenceLabel(summary.confidence)}</span>
      </header>

      <div className="summary-sections">
        <section className="observed-facts">
          <div className="summary-section-title"><span>01</span><div><h3>Hechos observados</h3><p>Texto del documento, sin completar información faltante.</p></div></div>
          {summary.observed_facts.length ? <ol>{summary.observed_facts.map((fact) => <li key={fact.item_order}>
            <p>{fact.text}</p>
            <a href={`${fact.citation.source_url}#page=${fact.citation.page_number}`} target="_blank" rel="noreferrer">Fuente: {fact.citation.document_name} · pág. {fact.citation.page_number} ↗</a>
          </li>)}</ol> : <p className="summary-unavailable">No hay evidencia narrativa suficiente para producir un resumen seguro.</p>}
        </section>

        <section className="summary-interpretation">
          <div className="summary-section-title"><span>02</span><div><h3>Interpretación</h3><p>Separada de los hechos.</p></div></div>
          {summary.interpretations.length ? <ul>{summary.interpretations.map((item) => <li key={item.item_order}>{item.text}</li>)}</ul> : <p>No generada. Esta fase no infiere impacto, causalidad ni atractivo de inversión.</p>}
        </section>

        <section className="summary-missing">
          <div className="summary-section-title"><span>03</span><div><h3>Datos faltantes</h3><p>Límites que afectan la lectura.</p></div></div>
          {summary.missing_data.length ? <ul>{summary.missing_data.map((item) => <li key={item.item_order}>{item.text}</li>)}</ul> : <p>No se detectaron ausencias automáticas para este resumen.</p>}
        </section>
      </div>

      <footer className="summary-audit"><span>{summary.confidence_reason}</span><span>Corte: {formatDate(summary.information_cutoff)} · Método extractivo v{summary.generator_version}</span></footer>
    </section> : <section className="summary-pending"><b>Resumen citado pendiente</b><p>La nota completa y sus referencias permanecen disponibles arriba.</p></section>}
  </>;
}

function confidenceLabel(confidence: "high" | "medium" | "low") {
  return { high: "alta", medium: "media", low: "baja" }[confidence];
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
