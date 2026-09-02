import { getNote, noteTopicNames } from "@/lib/financial";
import Link from "next/link";
import { notFound } from "next/navigation";

export const metadata = {
  title: "Detalle de nota financiera",
  description: "Contenido extraído de una nota financiera con referencias al documento oficial.",
};

export default async function NoteDetailPage({
  params,
}: {
  params: Promise<{ smvRpj: string; noteNumber: string }>;
}) {
  const { smvRpj, noteNumber: rawNoteNumber } = await params;
  const noteNumber = Number(rawNoteNumber);
  if (!Number.isInteger(noteNumber) || noteNumber < 1) notFound();
  let data;
  try {
    data = await getNote(smvRpj, noteNumber);
  } catch {
    notFound();
  }
  const { note, sections } = data;

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
  </>;
}
