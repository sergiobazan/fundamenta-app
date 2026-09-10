"use client";

import { useCallback, useEffect, useState } from "react";
import "@/app/notes-report.css";

type Citation = { fragment_id: number; quote: string; year: number; page: number;
  note: number; source_url: string; document_name: string };
type Finding = { kind: "risk" | "change" | "context"; priority: "high" | "medium" | "low";
  title: string; observed_fact: string; interpretation: string; question: string;
  citations: Citation[] };
type Report = { id: number; status: string; model: string; prompt_version: string;
  attempts: number; error_message: string | null; completed_at: string | null;
  result: { findings: Finding[]; limitations: string[]; comparison_available: boolean;
    status: string; coverage: { fragments: number; documents: { id: number; document_name: string;
      source_url: string; fiscal_year: number; notes_count: number; version: number }[] } } | null };
type State = { configured: boolean; stale: boolean; report: Report | null };
const active = (report?: Report | null) => !!report && ["queued", "running", "retrying"].includes(report.status);
const labels: Record<string, string> = { queued: "En cola", running: "Analizando las notas y preparando el informe",
  retrying: "Esperando para reintentar", completed: "Informe disponible", failed: "No se pudo completar" };
const priorities = { high: "Revisión prioritaria", medium: "Revisión importante", low: "Seguimiento" };

export default function NotesReport({ smvRpj, year, scope }: {
  smvRpj: string; year: number; scope: string;
}) {
  const [data, setData] = useState<State | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("all");
  const endpoint = `/api/companies/${encodeURIComponent(smvRpj)}/notes-report`;
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const response = await fetch(`${endpoint}?year=${year}&scope=${scope}`, {
      cache: "no-store", signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(25000)]) : AbortSignal.timeout(25000),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "No se pudo consultar el informe");
    setData(payload); setError("");
    return payload as State;
  }, [endpoint, year, scope]);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [refresh]);

  const processing = active(data?.report);
  useEffect(() => {
    if (!processing) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    let polls = 0;
    const poll = async () => {
      if (controller.signal.aborted) return;
      try {
        const next = await refresh(controller.signal);
        failures = 0;
        if (!active(next.report)) return;
      } catch {
        if (controller.signal.aborted) return;
        failures++;
        if (failures >= 3) { setError("Se pausó la consulta por problemas de conexión. Puedes actualizar el estado."); return; }
      }
      if (++polls >= 180) { setError("La consulta automática se pausó. El trabajo sigue guardado; actualiza el estado más tarde."); return; }
      timer = setTimeout(poll, Math.min(5000 * 2 ** failures, 30000));
    };
    timer = setTimeout(poll, 5000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [processing, refresh]);

  async function request() {
    setBusy(true); setError("");
    try {
      const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year, scope }), signal: AbortSignal.timeout(25000) });
      const payload = await response.json();
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "No se pudo solicitar el informe");
      setData({ configured: true, stale: false, report: payload.report });
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo solicitar el informe"); }
    finally { setBusy(false); }
  }

  const report = data?.report;
  const result = report?.result;
  const findings = result?.findings.filter(item => filter === "all" || item.kind === filter) ?? [];
  return <div className="ai-report">
    <section className="ai-report-intro">
      <div><span className="overline">{report?.prompt_version === "notes-preview-v2" ? "PRUEBA BREVE DE NOTAS · IA · COBERTURA LIMITADA" : "INFORME DE NOTAS · IA"}</span>
        <h2>{report ? labels[report.status] : "Una lectura guiada, con evidencia"}</h2>
        <p>Identifica asuntos que merecen revisión y consulta el fragmento original que los respalda. No modifica las métricas financieras.</p>
      </div>
      {!processing && data?.configured && (!report || data.stale || report.status === "failed") &&
        <button disabled={busy} onClick={request}>{busy ? "Solicitando…" : data.stale ? "Actualizar informe" : report ? "Reintentar informe" : "Generar informe"}</button>}
    </section>
    <div aria-live="polite">
      {!data && !error && <p>Cargando el estado del informe…</p>}
      {data && !data.configured && <p className="ai-report-notice">El informe está preparado. Falta configurar NVIDIA_API_KEY en el backend y reiniciarlo.</p>}
      {processing && <p className="ai-report-notice">Puedes salir de esta página. El informe se guarda en segundo plano. Intento {report?.attempts || 1} de 3; no hay un porcentaje estimado.</p>}
      {data?.stale && <p className="ai-report-notice">Este informe corresponde a una versión anterior de las fuentes o del modelo. Genera una actualización antes de usar sus conclusiones.</p>}
      {report?.error_message && <p className="ai-report-notice">{report.error_message}</p>}
    </div>
    {error && <div className="ai-report-notice" role="alert"><p>{error}</p><button onClick={() => refresh().catch(e => setError(e.message))}>Actualizar estado</button></div>}
    {result && <>
      <section className="ai-report-coverage"><h2>Fuentes y alcance</h2>
        <p>{result.coverage.fragments} fragmentos incluidos · {result.comparison_available ? `Documentos de ${year} y ${year - 1}` : "Sin comparación interanual disponible"}</p>
        {result.coverage.documents.map(doc => <a key={doc.id} href={doc.source_url} target="_blank" rel="noreferrer">{doc.document_name} · versión {doc.version} ↗</a>)}
      </section>
      <div className="ai-report-filters" aria-label="Filtrar hallazgos">
        {[["all", "Todos"], ["risk", "Riesgos y alertas"], ["change", "Cambios interanuales"], ["context", "Contexto"]].map(([value, label]) =>
          <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label} ({result.findings.filter(f => value === "all" || f.kind === value).length})</button>)}
      </div>
      {!findings.length && <p className="ai-report-notice">No hay hallazgos publicables en esta sección. Esto no significa que la empresa esté libre de riesgos.</p>}
      <div className="ai-report-grid">{findings.map((finding, index) => <article className={`ai-finding ai-finding-${finding.priority}`} key={`${finding.title}-${index}`}>
        <span className="overline">{priorities[finding.priority]} · {finding.kind === "change" ? "Cambio" : finding.kind === "risk" ? "Alerta" : "Contexto"}</span>
        <h2>{finding.title}</h2>
        <h3>Hecho reportado</h3><p>{finding.observed_fact}</p>
        <h3>Interpretación de IA · por verificar</h3><p>{finding.interpretation}</p>
        <details><summary>Ver evidencia ({finding.citations.length})</summary>{finding.citations.map((citation, i) =>
          <figure key={`${citation.fragment_id}-${i}`}><blockquote>{citation.quote}</blockquote><figcaption>
            <a href={`${citation.source_url.split("#")[0]}#page=${citation.page}`} target="_blank" rel="noreferrer">{citation.year} · Nota {citation.note} · Página {citation.page} ↗</a>
          </figcaption></figure>)}</details>
        <div className="ai-finding-question"><h3>Pregunta para profundizar</h3><p>{finding.question}</p></div>
      </article>)}</div>
      <section className="ai-report-coverage"><h2>Limitaciones del informe</h2><ul>{result.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul></section>
      <p className="ai-report-meta">NVIDIA · {report?.model} · {report?.prompt_version} · {report?.completed_at ? new Date(report.completed_at).toLocaleString("es-PE") : ""}</p>
    </>}
    <footer className="data-footer">Contenido generado con IA, no auditado. No constituye asesoría financiera ni recomendación de compra o venta. Verifica las fuentes oficiales.</footer>
  </div>;
}
