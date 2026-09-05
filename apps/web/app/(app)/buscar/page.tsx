import { getCompanies, noteTopicNames, searchFragments } from "@/lib/financial";
import type { FragmentSearchResponse, NoteTopic } from "@/lib/types";
import Link from "next/link";

export const metadata = {
  title: "Buscar en documentos financieros",
  description: "Búsqueda trazable dentro de notas financieras con referencia a empresa, nota y página oficial.",
};

const topics = Object.entries(noteTopicNames) as [NoteTopic, string][];

export default async function DocumentSearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; company?: string; topic?: string; year?: string; page?: string }>;
}) {
  const requested = await searchParams;
  const companies = (await getCompanies()).filter((candidate) =>
    candidate.completed_steps.includes("documents")
  );
  const query = requested.q?.trim().slice(0, 100) ?? "";
  const company = companies.some((candidate) => candidate.smv_rpj === requested.company)
    ? requested.company
    : undefined;
  const topic = topics.some(([value]) => value === requested.topic)
    ? requested.topic as NoteTopic
    : undefined;
  const parsedYear = Number(requested.year);
  const year = Number.isInteger(parsedYear) && parsedYear >= 2000 && parsedYear <= 2100
    ? parsedYear
    : undefined;
  const parsedPage = Number(requested.page);
  const page = Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const pageSize = 20;

  let data: FragmentSearchResponse | null = null;
  let searchFailed = false;
  if (query.length >= 2) {
    try {
      data = await searchFragments({
        query,
        companyRpj: company,
        topic,
        year,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });
    } catch {
      searchFailed = true;
    }
  }

  return <>
    <header className="app-header search-header">
      <div><span className="overline">ÍNDICE DOCUMENTAL</span><h1>Buscar en documentos</h1><p>Encuentra conceptos dentro de las notas financieras y llega a la página exacta del PDF oficial.</p></div>
      {data && <div className="directory-count"><strong>{data.total}</strong><span>fragmentos<br />encontrados</span></div>}
    </header>

    <section className="search-coverage"><span>⌕</span><div><b>Búsqueda sobre texto extraído</b><p>El índice cubre las notas oficiales disponibles de Buenaventura, Minsur, Volcan y Poderosa. Cada coincidencia conserva su documento, versión y página para que puedas contrastarla.</p></div></section>

    <form className="document-search-form" action="/buscar" method="get">
      <label className="document-query"><span>Concepto, riesgo o cuenta</span><div><span>⌕</span><input name="q" defaultValue={query} minLength={2} maxLength={100} placeholder="Ej. deuda, cierre de minas, contingencias…" required /></div></label>
      <label><span>Empresa</span><select name="company" defaultValue={company ?? ""}><option value="">Todas las empresas</option>{companies.map((candidate) => <option value={candidate.smv_rpj} key={candidate.smv_rpj}>{candidate.legal_name}</option>)}</select></label>
      <label><span>Tema</span><select name="topic" defaultValue={topic ?? ""}><option value="">Todos los temas</option>{topics.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label><span>Ejercicio</span><input name="year" type="number" min="2000" max="2100" defaultValue={year ?? ""} placeholder="Todos" /></label>
      <button type="submit">Buscar</button>
      {(query || company || topic || year) && <Link href="/buscar">Limpiar</Link>}
    </form>

    {!query && <section className="search-empty"><span>⌕</span><h2>Empieza con una pregunta concreta</h2><p>Prueba con “deuda financiera”, “provisión por cierre” o “hechos posteriores”.</p></section>}
    {query.length === 1 && <section className="search-empty"><h2>Escribe al menos 2 caracteres</h2><p>Una consulta más específica produce resultados más útiles.</p></section>}
    {searchFailed && <section className="search-empty error"><h2>No se pudo consultar el índice</h2><p>El resto de tus datos sigue disponible. Inténtalo nuevamente en unos instantes.</p></section>}
    {data && data.results.length === 0 && <section className="search-empty"><h2>No encontramos coincidencias</h2><p>Prueba otro término o elimina alguno de los filtros.</p></section>}

    {data && data.results.length > 0 && <section className="search-results" aria-label="Resultados documentales">
      <div className="search-results-heading"><h2>Coincidencias para “{data.query}”</h2><span>Ordenadas por relevancia documental</span></div>
      {data.results.map((fragment) => <article className="fragment-card" key={fragment.id}>
        <div className="fragment-meta">
          <span>{fragment.legal_name}</span>
          <span>Ejercicio {fragment.fiscal_year}</span>
          <span>{fragment.period_code === "A" ? "Anual" : `${fragment.period_code}T`}</span>
          <span>{fragment.scope === "consolidated" ? "Consolidado" : "Individual"}</span>
          <span>Página {fragment.page_number}</span>
        </div>
        <div className="fragment-title"><div><small>NOTA {fragment.note_number} · {noteTopicNames[fragment.topic]}</small><h2>{fragment.original_title}</h2></div>{fragment.is_priority && <b>Relevante</b>}</div>
        <p className="fragment-excerpt">{fragment.excerpt}</p>
        <div className="fragment-trace">
          <span>Versión {fragment.document_version} · SHA-256 verificada</span>
          <div><Link href={`/empresas/${fragment.smv_rpj}/notas/${fragment.note_number}?year=${fragment.fiscal_year}&period=${fragment.period_code}&scope=${fragment.scope}`}>Leer nota completa</Link><a href={`${fragment.source_url}#page=${fragment.page_number}`} target="_blank" rel="noreferrer">Ver página en PDF ↗</a></div>
        </div>
      </article>)}
      {data.total > pageSize && <nav className="search-pagination" aria-label="Paginación de resultados">
        {page > 1 ? <Link href={searchPageHref({ query, company, topic, year, page: page - 1 })}>← Anterior</Link> : <span />}
        <span>Página {page} de {Math.ceil(data.total / pageSize)}</span>
        {data.offset + data.results.length < data.total ? <Link href={searchPageHref({ query, company, topic, year, page: page + 1 })}>Siguiente →</Link> : <span />}
      </nav>}
    </section>}

    <footer className="data-footer"><span>Texto extraído automáticamente: confirma cifras y tablas en la fuente.</span><span>Índice local · sin interpretación de IA</span></footer>
  </>;
}

function searchPageHref({
  query,
  company,
  topic,
  year,
  page,
}: {
  query: string;
  company?: string;
  topic?: NoteTopic;
  year?: number;
  page: number;
}) {
  const params = new URLSearchParams({ q: query, page: String(page) });
  if (company) params.set("company", company);
  if (topic) params.set("topic", topic);
  if (year) params.set("year", String(year));
  return `/buscar?${params.toString()}`;
}
