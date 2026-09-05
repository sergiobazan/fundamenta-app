import { EventTimeline } from "@/components/EventTimeline";
import { eventCategoryNames, getCompanies, getEvents } from "@/lib/financial";
import type { CorporateEventCategory } from "@/lib/types";

export const metadata = {
  title: "Eventos corporativos oficiales",
  description: "Hechos corporativos de empresas peruanas con fecha, resumen y enlace a la fuente oficial.",
};

const categories = Object.entries(eventCategoryNames) as [CorporateEventCategory, string][];

export default async function EventsPage({
  searchParams,
}: {
  searchParams: Promise<{ company?: string; category?: string }>;
}) {
  const requested = await searchParams;
  const companies = (await getCompanies()).filter((candidate) => candidate.has_analysis);
  const company = companies.some((candidate) => candidate.smv_rpj === requested.company)
    ? requested.company
    : undefined;
  const category = categories.some(([value]) => value === requested.category)
    ? requested.category as CorporateEventCategory
    : undefined;
  const events = await getEvents({ companyRpj: company, category });

  return <>
    <header className="app-header events-header"><div><span className="overline">HECHOS CORPORATIVOS</span><h1>Eventos oficiales</h1><p>Qué ocurrió, cuándo ocurrió y dónde verificarlo. Cada registro conserva versión y huella de integridad.</p></div><div className="directory-count"><strong>{events.length}</strong><span>eventos<br />encontrados</span></div></header>

    <section className="events-coverage"><span>i</span><div><b>Cobertura inicial curada</b><p>Por ahora mostramos comunicaciones oficiales de Buenaventura y Minsur. Los resúmenes son propios; el documento completo permanece en la SMV o el sitio del emisor.</p></div></section>

    <form className="event-filters" action="/eventos" method="get">
      <label><span>Empresa</span><select name="company" defaultValue={company ?? ""}><option value="">Todas las empresas</option>{companies.map((candidate) => <option value={candidate.smv_rpj} key={candidate.smv_rpj}>{candidate.legal_name}</option>)}</select></label>
      <label><span>Categoría</span><select name="category" defaultValue={category ?? ""}><option value="">Todas las categorías</option>{categories.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <button type="submit">Aplicar filtros</button>
      {(company || category) && <a href="/eventos">Limpiar</a>}
    </form>

    <EventTimeline events={events} />
    <footer className="data-footer"><span>Los eventos aportan contexto, no una recomendación de inversión.</span><span>Metadatos y resumen propio · fuente primaria enlazada</span></footer>
  </>;
}
