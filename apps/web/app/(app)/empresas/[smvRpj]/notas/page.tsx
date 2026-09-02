import { getNotes, noteTopicNames } from "@/lib/financial";
import type { NoteTopic } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

export const metadata = {
  title: "Notas a los estados financieros",
  description: "Notas auditadas extraídas de documentos oficiales con referencia a cada página.",
};

const topics = Object.entries(noteTopicNames) as [NoteTopic, string][];

export default async function NotesPage({
  params,
  searchParams,
}: {
  params: Promise<{ smvRpj: string }>;
  searchParams: Promise<{ q?: string; topic?: string; priority?: string }>;
}) {
  const { smvRpj } = await params;
  const requested = await searchParams;
  const topic = topics.some(([value]) => value === requested.topic)
    ? requested.topic as NoteTopic
    : undefined;
  const priorityOnly = requested.priority === "1";
  const query = requested.q?.trim().slice(0, 100) || undefined;
  let data;
  try {
    data = await getNotes(smvRpj, { topic, priorityOnly, query });
  } catch {
    notFound();
  }

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan">
      <Link href="/empresas">Empresas</Link><span>/</span>
      <Link href={`/empresas/${smvRpj}`}>{smvRpj}</Link><span>/</span><b>Notas</b>
    </nav>

    <header className="app-header notes-header">
      <div><span className="overline">ESTADOS FINANCIEROS AUDITADOS</span><h1>Notas financieras</h1><p>El contexto detrás de las cifras: políticas, estimaciones, deuda, compromisos y hechos posteriores.</p></div>
      <div className="directory-count"><strong>{data.notes.length}</strong><span>de {data.document.notes_count}<br />notas visibles</span></div>
    </header>

    <section className="note-source-bar">
      <div><span>✓</span><p><b>{data.document.document_name}</b><small>{data.document.page_count} páginas · versión {data.document.version} · extracción referenciada</small></p></div>
      <a href={data.document.source_url} target="_blank" rel="noreferrer">Abrir PDF oficial ↗</a>
    </section>

    <form className="notes-filters" action={`/empresas/${smvRpj}/notas`} method="get">
      <label className="note-search"><span>⌕</span><input name="q" defaultValue={query ?? ""} placeholder="Buscar título o contenido…" /></label>
      <label><span>Tema</span><select name="topic" defaultValue={topic ?? ""}><option value="">Todos los temas</option>{topics.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label className="priority-filter"><input type="checkbox" name="priority" value="1" defaultChecked={priorityOnly} /><span>Sólo relevantes para análisis</span></label>
      <button type="submit">Aplicar</button>
      {(query || topic || priorityOnly) && <Link href={`/empresas/${smvRpj}/notas`}>Limpiar</Link>}
    </form>

    {data.notes.length ? <div className="notes-grid">{data.notes.map((note) =>
      <Link className="note-card" href={`/empresas/${smvRpj}/notas/${note.note_number}`} key={note.id}>
        <div className="note-card-top"><b>Nota {note.note_number}</b><span className={note.is_priority ? "priority" : ""}>{noteTopicNames[note.topic]}</span></div>
        <h2>{note.original_title}</h2>
        <p>{note.excerpt}{note.excerpt.length >= 320 ? "…" : ""}</p>
        <div className="note-card-foot"><span>Páginas {note.start_page}{note.end_page !== note.start_page ? `–${note.end_page}` : ""}</span><b>Leer nota →</b></div>
      </Link>
    )}</div> : <section className="empty-result"><b>No encontramos notas con esos filtros.</b><p>Prueba otro término o limpia los filtros.</p></section>}

    <footer className="data-footer"><span>Texto extraído automáticamente; verifica importes y tablas en el PDF oficial.</span><span>Última comprobación: {new Date(data.document.last_checked_at ?? data.document.retrieved_at).toLocaleDateString("es-PE")}</span></footer>
  </>;
}
