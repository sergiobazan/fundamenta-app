import Link from "next/link";
import { EventTimeline } from "@/components/EventTimeline";
import { getCompanies, getEvents } from "@/lib/financial";
import { panelOverview } from "@/lib/panel";
import "@/app/panel.css";

export const metadata = { title: "Panel de investigación" };

export default async function Dashboard() {
  const [catalog, events] = await Promise.allSettled([
    getCompanies(),
    getEvents({ limit: 4 }),
  ]);
  const companies = catalog.status === "fulfilled" ? catalog.value : [];
  const overview = panelOverview(companies);
  const loaded = catalog.status === "fulfilled";
  return (
    <div className="research-panel">
      <header className="app-header">
        <div>
          <span className="overline">
            TU PUNTO DE PARTIDA · FUENTES OFICIALES
          </span>
          <h1>Panel de investigación</h1>
          <p>
            Explora empresas, contrasta sus cifras y profundiza en sus notas.
          </p>
        </div>
        <Link className="panel-primary" href="/empresas">
          Explorar empresas →
        </Link>
      </header>
      <section className="panel-intro">
        <div>
          <span className="overline">CATÁLOGO SMV · ANÁLISIS BAJO DEMANDA</span>
          <h2>Una empresa. Sus cifras. Las preguntas que importan.</h2>
          <p>
            Abre un análisis disponible o solicita uno para un emisor
            compatible. Estados y métricas aparecen primero; la cobertura
            documental depende de las fuentes oficiales disponibles.
          </p>
        </div>
        <Link href="/empresas">Buscar por nombre, RUC o código SMV ↗</Link>
      </section>
      {!loaded && (
        <p className="panel-alert" role="alert">
          No pudimos consultar el catálogo. Los conteos no están disponibles;
          recarga la página para reintentar.
        </p>
      )}
      <section
        className="panel-stats"
        aria-label="Cobertura actual del catálogo">
        {[
          [
            companies.length,
            "Emisores catalogados",
            "No todos están dentro del alcance del MVP",
          ],
          [
            overview.compatible,
            "Compatibles con el MVP",
            "Minería y otros emisores no financieros",
          ],
          [
            overview.available.length,
            "Análisis disponibles",
            "Disponibilidad no equivale a revisión humana",
          ],
          [
            overview.active.length,
            "Análisis en curso",
            "Trabajos del catálogo, no sólo de tu cuenta",
          ],
        ].map(([count, label, detail]) => (
          <article key={String(label)}>
            <span>{label}</span>
            <strong>{loaded ? count : "—"}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </section>
      <section className="company-section">
        <div className="content-head">
          <div>
            <span className="overline">COMIENZA CON DATOS DISPONIBLES</span>
            <h2>Empresas para explorar</h2>
            <p>
              Ordenadas por fecha de finalización. No es un ranking de
              inversión.
            </p>
          </div>
          <Link href="/empresas">Ver catálogo completo ↗</Link>
        </div>
        <div className="panel-company-grid">
          {overview.available.slice(0, 6).map((company) => (
            <Link
              className="panel-company"
              key={company.smv_rpj}
              href={`/empresas/${company.smv_rpj}`}>
              <span className="overline">
                {company.sector || "Sector sin clasificar"}
              </span>
              <h3>{company.legal_name}</h3>
              <p>
                SMV {company.smv_rpj} ·{" "}
                {company.latest_fiscal_year ?? "Periodo por consultar"}
                {company.preferred_scope
                  ? ` · ${company.preferred_scope === "consolidated" ? "Consolidado" : "Individual"}`
                  : ""}
              </p>
              <div>
                <span>
                  {company.validation_tier === "verified"
                    ? "Revisión manual registrada"
                    : "Validación automática"}
                </span>
                <b>Ver análisis →</b>
              </div>
            </Link>
          ))}
        </div>
        {loaded && !overview.available.length && (
          <p className="panel-empty">
            Todavía no hay análisis completos disponibles. En el catálogo puedes
            consultar avances o solicitar un análisis compatible.
          </p>
        )}
      </section>
      {(overview.active.length > 0 || overview.attention > 0) && (
        <section className="panel-progress">
          <h2>Estado de los análisis</h2>
          {overview.active.slice(0, 4).map((company) => (
            <Link key={company.smv_rpj} href={`/empresas/${company.smv_rpj}`}>
              <b>{company.legal_name}</b>
              <span>
                {company.job_status === "queued" ||
                company.analysis_status === "queued"
                  ? "En cola"
                  : company.job_status === "retrying"
                    ? "Reintentando"
                    : "En proceso"}{" "}
                · Consultar avance →
              </span>
            </Link>
          ))}
          {overview.attention > 0 && (
            <p>
              {overview.attention} empresas tienen análisis parciales,
              pendientes de revisión o con errores.{" "}
              <Link href="/empresas">Revisar en el catálogo ↗</Link>
            </p>
          )}
          <small>
            Estado consultado al abrir esta página. Abre una empresa para seguir
            su progreso.
          </small>
        </section>
      )}
      <section className="company-section">
        <div className="content-head">
          <div>
            <span className="overline">DE LAS CIFRAS AL CONTEXTO</span>
            <h2>Herramientas para tu siguiente pregunta</h2>
          </div>
        </div>
        <div className="panel-tools">
          <Link href="/comparador">
            <span>01 · COMPARAR</span>
            <h3>¿Qué cambió y frente a quién?</h3>
            <p>
              Compara empresas con datos compatibles. Desde cada empresa,
              contrasta métricas y estados con el ejercicio anterior.
            </p>
            <b>Abrir comparador →</b>
          </Link>
          <Link href="/buscar">
            <span>02 · ENCONTRAR EVIDENCIA</span>
            <h3>¿Dónde lo dice el documento?</h3>
            <p>
              Busca en el texto oficial indexado y consulta sus referencias por
              página. La cobertura varía por empresa.
            </p>
            <b>Buscar en documentos →</b>
          </Link>
          <Link href="/empresas">
            <span>03 · INFORME DE NOTAS CON IA</span>
            <h3>¿Qué merece una lectura más profunda?</h3>
            <p>
              Desde Empresa → Notas, solicita riesgos y cambios sustentados. El
              informe analiza una selección priorizada, no todas las notas, y
              requiere revisión humana.
            </p>
            <b>Elegir empresa →</b>
          </Link>
        </div>
      </section>
      <section className="company-section">
        <div className="content-head">
          <div>
            <span className="overline">CONTEXTO OFICIAL</span>
            <h2>Eventos del catálogo</h2>
            <p>
              Últimos eventos registrados; no es un servicio de noticias en
              tiempo real.
            </p>
          </div>
          <Link href="/eventos">Ver eventos ↗</Link>
        </div>
        {events.status === "fulfilled" ? (
          <EventTimeline events={events.value} compact />
        ) : (
          <p className="panel-empty">
            Los eventos no están disponibles en este momento.
          </p>
        )}
      </section>
      <footer className="data-footer">
        La SMV es la fuente primordial. Verifica periodo, alcance y escala; las
        alertas y el contenido de IA no constituyen recomendaciones de
        inversión.
      </footer>
    </div>
  );
}
