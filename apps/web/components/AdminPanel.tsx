"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const labels: Record<string, string> = {
  queued: "En cola", running: "Procesando", retrying: "Reintento programado",
  completed: "Completado", review_required: "Requiere revisión", failed: "Fallido",
  pending: "Pendiente", skipped: "Sin fuente verificada",
  statements: "Estados financieros", metrics: "Métricas", documents: "Notas y búsqueda",
  summaries: "Resúmenes", complete: "Análisis completo",
};
const text = (value: string | null) => value ? labels[value] || value : "—";
const date = (value: string | null) => value ? new Date(value).toLocaleString("es-PE") : "—";
function duration(value: string | number | null) {
  if (value == null) return "—";
  const seconds = Math.max(0, Math.round(Number(value)));
  return seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}
type Job = {
  id: number; smv_rpj: string; legal_name: string; fiscal_year: number; period_code: string;
  scope: string; status: string; current_step: string | null; progress: number;
  attempts: number; max_attempts: number; duration_seconds: string | null;
  error_message: string | null; started_at: string | null; completed_at: string | null;
  next_retry_at: string | null; created_at: string; requested_by_name?: string | null;
};
type Step = { step_code: string; status: string; duration_seconds: string | null;
  error_message: string | null; details: Record<string, unknown> };
type HistoryEvent = { id: number; kind: string; step_code: string | null; created_at: string;
  snapshot: { status: string; attempts?: number; error_message?: string;
    details?: Record<string, unknown> } };
type Action = { id: number; actor_label: string; action: string; reason: string; created_at: string };
type Detail = { job: Job; steps: Step[]; events: HistoryEvent[]; actions: Action[] };
type Listing = { jobs: Job[]; total: number; page_size: number; counts: Record<string, number> };
async function read<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "No se pudo completar la solicitud.");
  return payload as T;
}
function Badge({ status }: { status: string }) {
  return <span className={`admin-badge ${status}`}>{text(status)}</span>;
}
function SafeDetails({ details }: { details: Record<string, unknown> }) {
  if (!Object.keys(details).length) return null;
  return <details className="admin-raw"><summary>Ver evidencia y actividad</summary><pre>{JSON.stringify(details, null, 2)}</pre></details>;
}

export function AdminPanel() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [listing, setListing] = useState<Listing | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("jobId");
    if (value && /^\d+$/.test(value) && Number.isSafeInteger(Number(value))) setSelected(Number(value));
  }, []);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [older, setOlder] = useState<HistoryEvent[]>([]);
  const [hasOlder, setHasOlder] = useState(true);
  const [loadingOlder, setLoadingOlder] = useState(false);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    setListing(null); setError("");
    const load = async () => {
      try {
        const params = new URLSearchParams({ page: String(page), q: query });
        if (status) params.set("status", status);
        const result = await read<Listing>(`/api/admin/analysis-jobs?${params}`);
        if (!stopped) { setListing(result); setError(""); }
      } catch (err) { if (!stopped) setError((err as Error).message); }
      finally { if (!stopped) timer = setTimeout(load, 10000); }
    };
    void load();
    return () => { stopped = true; clearTimeout(timer); };
  }, [status, query, page, refresh]);

  useEffect(() => {
    if (selected === null) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    setDetail(null); setDetailError(""); setReason(""); setOlder([]); setHasOlder(true);
    const load = async () => {
      try {
        const result = await read<Detail>(`/api/admin/analysis-jobs/${selected}`);
        if (!stopped) { setDetail(result); setDetailError(""); }
      } catch (err) { if (!stopped) setDetailError((err as Error).message); }
      finally { if (!stopped) timer = setTimeout(load, 5000); }
    };
    void load();
    return () => { stopped = true; clearTimeout(timer); };
  }, [selected, refresh]);

  async function retry(event: React.FormEvent) {
    event.preventDefault();
    if (!detail || busy) return;
    const jobId = detail.job.id;
    setBusy(true); setNotice(""); setDetailError("");
    try {
      await read(`/api/admin/analysis-jobs/${jobId}/retry`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: reason.trim() }),
      });
      setNotice(`Trabajo #${jobId} en cola. Se conservaron las etapas completadas.`);
      setRefresh(value => value + 1);
    } catch (err) { setDetailError((err as Error).message); }
    finally { setBusy(false); }
  }

  const history = [...new Map([...(detail?.events || []), ...older].map(e => [e.id, e])).values()].sort((a, b) => b.id - a.id);
  async function loadOlder() {
    if (!detail || !history.length) return;
    setLoadingOlder(true);
    try {
      const result = await read<{ events: HistoryEvent[] }>(`/api/admin/analysis-jobs/${detail.job.id}/events?before=${history[history.length - 1].id}`);
      setOlder(current => [...current, ...result.events]);
      setHasOlder(result.events.length === 100);
    } catch (err) { setDetailError((err as Error).message); }
    finally { setLoadingOlder(false); }
  }
  return <div className="admin-panel">
    <header className="app-header"><div><span className="overline">OPERACIÓN INTERNA</span><h1>Administración</h1><p>Supervisa los análisis y resuelve los trabajos pendientes.</p></div><button className="admin-button" disabled={busy} onClick={() => setRefresh(v => v + 1)}>Actualizar</button></header>
    <div className="admin-counts" aria-label="Resumen de trabajos">
      {[["running", "En proceso"], ["queued", "En cola"], ["retrying", "Reintentando"], ["failed", "Fallidos"], ["review_required", "En revisión"], ["completed", "Completados"]].map(([key, label]) =>
        <button key={key} aria-pressed={status === key} onClick={() => { setStatus(status === key ? "" : key); setPage(1); }}><b>{listing?.counts[key] ?? "—"}</b><span>{label}</span></button>)}
    </div>
    <form className="admin-filters" onSubmit={event => { event.preventDefault(); setQuery(search.trim()); setPage(1); }}>
      <label>Empresa o código SMV<input value={search} maxLength={100} onChange={event => setSearch(event.target.value)} placeholder="Ej. Nexa o B20010" /></label>
      <label>Estado<select value={status} onChange={event => { setStatus(event.target.value); setPage(1); }}><option value="">Todos los estados</option>{["queued", "running", "retrying", "failed", "review_required", "completed"].map(s => <option key={s} value={s}>{text(s)}</option>)}</select></label>
      <button className="admin-button" type="submit">Buscar</button>
    </form>
    <p className="admin-meta">Trabajos de análisis financiero · Actualización automática cada 10 segundos. Los contadores muestran el total general.</p>
    {notice && <p className="admin-success" role="status">{notice}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="admin-card" aria-label="Trabajos de análisis">
      {!listing && !error && <p role="status">Cargando trabajos…</p>}
      {listing && <><div className="admin-table-wrap"><table><thead><tr><th>Empresa / trabajo</th><th>Periodo</th><th>Estado / etapa</th><th>Intentos totales</th><th>Duración del intento</th><th>Detalle</th></tr></thead><tbody>
        {listing.jobs.map(job => <tr key={job.id} className={selected === job.id ? "selected" : ""}><td><Link href={`/empresas/${job.smv_rpj}`}>{job.legal_name}</Link><small>{job.smv_rpj} · #{job.id}</small></td><td>{job.fiscal_year} · {job.period_code}<small>{job.scope === "individual" ? "Individual" : "Consolidado"}</small></td><td><Badge status={job.status}/><small>{text(job.current_step)} · {job.progress}%</small></td><td>{job.attempts} / {job.max_attempts}</td><td>{duration(job.duration_seconds)}</td><td><button className="admin-button" disabled={busy || loadingOlder} onClick={() => { setSelected(job.id); setNotice(""); }}>Inspeccionar #{job.id}</button></td></tr>)}
      </tbody></table></div>{listing.jobs.length === 0 && <p className="admin-empty">No hay trabajos con estos filtros.</p>}
      <div className="admin-pagination"><span>{listing.total} trabajos · Página {page}</span><button disabled={page === 1} onClick={() => setPage(v => v - 1)}>Anterior</button><button disabled={page * listing.page_size >= listing.total} onClick={() => setPage(v => v + 1)}>Siguiente</button></div></>}
    </section>
    {selected !== null && <section className="admin-card admin-inspector" aria-labelledby="admin-detail-title">
      <header><div><span className="overline">INSPECCIÓN DEL TRABAJO</span><h2 id="admin-detail-title">{detail?.job.legal_name || `Trabajo #${selected}`}</h2></div><button className="admin-button" disabled={busy || loadingOlder} onClick={() => setSelected(null)}>Cerrar detalle</button></header>
      {detailError && <p className="form-error" role="alert">{detailError}</p>}
      {!detail && !detailError && <p role="status">Cargando detalle…</p>}
      {detail && <><Badge status={detail.job.status}/><dl className="admin-facts">
        <div><dt>Trabajo</dt><dd>#{detail.job.id} · {detail.job.fiscal_year} · {detail.job.scope === "individual" ? "Individual" : "Consolidado"}</dd></div>
        <div><dt>Solicitante</dt><dd>{detail.job.requested_by_name || "Proceso automático / cuenta eliminada"}</dd></div>
        <div><dt>Creado</dt><dd>{date(detail.job.created_at)}</dd></div><div><dt>Inicio del último intento</dt><dd>{date(detail.job.started_at)}</dd></div>
        <div><dt>Intentos totales / límite actual</dt><dd>{detail.job.attempts} / {detail.job.max_attempts}</dd></div><div><dt>Próximo reintento</dt><dd>{date(detail.job.next_retry_at)}</dd></div>
      </dl>
      {detail.job.error_message && <div className="admin-error"><b>Último error registrado</b><p>{detail.job.error_message}</p>{detail.job.status === "failed" && <strong>El trabajo terminó. No hay un reintento automático pendiente.</strong>}</div>}
      <ol className="admin-steps">{detail.steps.map(step => <li key={step.step_code}><div><b>{text(step.step_code)}</b><Badge status={step.status}/><span>{duration(step.duration_seconds)}</span></div>{typeof step.details.activity === "string" && <p>{step.details.activity}</p>}{step.error_message && <p className="admin-error-text">{step.error_message}</p>}<SafeDetails details={step.details}/></li>)}</ol>
      {["failed", "review_required"].includes(detail.job.status) && <form className="admin-retry" onSubmit={retry}><h3>Reintentar etapas pendientes</h3><p>Conserva las etapas completadas y abre un nuevo ciclo de intentos. El motivo quedará registrado con tu cuenta.</p><label htmlFor="admin-reason">Motivo del reintento</label><textarea id="admin-reason" required minLength={10} maxLength={500} value={reason} onChange={event => setReason(event.target.value)} placeholder="Ej. Se corrigió la lectura duplicada del PDF de notas."/><button className="admin-primary" disabled={busy || reason.trim().length < 10}>{busy ? "Registrando…" : "Registrar y reintentar"}</button></form>}
      <h3>Historial de actividad</h3><p className="admin-meta">Los intentos anteriores a la instalación del panel solo tienen una captura del estado disponible. Fechas en tu zona horaria.</p>
      <ol className="admin-history">{history.map(event => <li key={event.id}><time>{date(event.created_at)}</time><div><b>{event.kind === "baseline" ? "Estado previo al panel" : event.step_code ? text(event.step_code) : `Trabajo · intento ${event.snapshot.attempts ?? "—"}`}</b><span>{text(event.snapshot.status)}</span>{event.snapshot.error_message && <p>{event.snapshot.error_message}</p>}<SafeDetails details={event.snapshot.details || {}}/></div></li>)}</ol>
      {hasOlder && history.length >= 100 && <button className="admin-button" disabled={loadingOlder} onClick={loadOlder}>{loadingOlder ? "Cargando…" : "Cargar actividad anterior"}</button>}
      <h3>Acciones administrativas</h3>{detail.actions.length === 0 ? <p className="admin-meta">Sin acciones administrativas para este trabajo.</p> : <ul className="admin-history">{detail.actions.map(action => <li key={action.id}><time>{date(action.created_at)}</time><div><b>{action.actor_label}</b><span>{action.action === "analysis.retry" ? "Reintento manual" : action.action}</span><p>{action.reason}</p></div></li>)}</ul>}
      </>}
    </section>}
  </div>;
}
