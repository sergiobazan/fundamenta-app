import { eventCategoryNames } from "@/lib/financial";
import type { CorporateEvent } from "@/lib/types";
import Link from "next/link";

const limaDate = new Intl.DateTimeFormat("es-PE", {
  timeZone: "America/Lima",
  day: "2-digit",
  month: "short",
  year: "numeric",
});

function formatPublishedDate(value: string) {
  return limaDate.format(new Date(value));
}

function formatEffectiveDate(value: string) {
  return limaDate.format(new Date(`${value}T12:00:00-05:00`));
}

function providerName(provider: string) {
  if (provider === "smv") return "SMV";
  if (provider.startsWith("issuer_")) return "Emisor";
  return provider;
}

export function EventTimeline({ events, compact = false }: { events: CorporateEvent[]; compact?: boolean }) {
  if (events.length === 0) {
    return <div className="events-empty"><b>No hay eventos para estos filtros.</b><p>Prueba con otra empresa o categoría.</p></div>;
  }

  return <div className={`event-timeline${compact ? " compact" : ""}`}>
    {events.map((event) => <article className="event-card" key={event.id}>
      <div className="event-rail" aria-hidden="true"><i></i></div>
      <div className="event-date"><time dateTime={event.published_at}>{formatPublishedDate(event.published_at)}</time><span>Publicado</span></div>
      <div className="event-body">
        <div className="event-tags"><span>{eventCategoryNames[event.category]}</span><b>{providerName(event.source_provider)}</b></div>
        <h2>{event.title}</h2>
        <p>{event.summary}</p>
        <div className="event-meta">
          <span>SMV {event.smv_rpj}</span>
          {event.effective_date && <span>Fecha efectiva: {formatEffectiveDate(event.effective_date)}</span>}
          <span>Versión {event.version} · SHA {event.source_sha256.slice(0, 10)}</span>
        </div>
        <div className="event-actions">
          <Link href={`/empresas/${event.smv_rpj}`}>{event.legal_name}</Link>
          <a href={event.source_url} target="_blank" rel="noreferrer" aria-label={`Abrir fuente oficial: ${event.source_document_name}`}>Fuente oficial ↗</a>
        </div>
      </div>
    </article>)}
  </div>;
}
