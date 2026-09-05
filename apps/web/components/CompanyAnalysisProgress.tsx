"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import type { AnalysisStepCode, CompanyAnalysis } from "@/lib/types";
import { AnalysisReadingCards } from "./AnalysisReadingCards";

const stepNames: Record<AnalysisStepCode, string> = {
  statements: "Estados financieros",
  metrics: "Métricas compatibles",
  documents: "Notas y búsqueda",
  summaries: "Resúmenes y comparaciones",
};

const activeStatuses = new Set(["queued", "running", "retrying"]);

export function CompanyAnalysisProgress({ initial }: { initial: CompanyAnalysis }) {
  const router = useRouter();
  const [analysis, setAnalysis] = useState(initial);
  const [error, setError] = useState("");
  const [pending, startTransition] = useTransition();
  const job = analysis.job;
  const active = Boolean(job && activeStatuses.has(job.status));

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(async () => {
      const response = await fetch(
        `/api/companies/${encodeURIComponent(analysis.company.smv_rpj)}/analysis`,
        { cache: "no-store" },
      );
      if (!response.ok) return;
      const next = await response.json() as CompanyAnalysis;
      setAnalysis(next);
      if (next.company.has_analysis && next.job && !activeStatuses.has(next.job.status)) {
        router.refresh();
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [active, analysis.company.smv_rpj, router]);

  function requestAnalysis() {
    setError("");
    startTransition(async () => {
      const response = await fetch(
        `/api/companies/${encodeURIComponent(analysis.company.smv_rpj)}/analysis`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
      );
      const payload = await response.json().catch(() => null) as CompanyAnalysis | { detail?: string } | null;
      if (!response.ok) {
        setError(payload && "detail" in payload ? payload.detail || "No pudimos iniciar el análisis." : "No pudimos iniciar el análisis.");
        return;
      }
      setAnalysis(payload as CompanyAnalysis);
    });
  }

  const progress = job?.progress || 0;
  const waitingForReview = analysis.company.analysis_status === "review_required";
  const failed = analysis.company.analysis_status === "failed";

  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan"><Link href="/empresas">Empresas</Link><span>/</span><b>{analysis.company.legal_name}</b></nav>
    <header className="analysis-progress-header"><span className="overline">ANÁLISIS BAJO DEMANDA</span><h1>{analysis.company.legal_name}</h1><p>SMV {analysis.company.smv_rpj}{analysis.company.ruc ? ` · RUC ${analysis.company.ruc}` : ""}</p></header>
    <section className="analysis-progress-card">
      <div className="analysis-progress-copy">
        <span>{active ? "Estamos trabajando" : waitingForReview ? "Revisión necesaria" : failed ? "No se pudo completar" : "Lista para analizar"}</span>
        <h2>{active ? "Puedes volver cuando quieras." : waitingForReview ? "Los resultados seguros se conservaron." : failed ? "Puedes volver a intentarlo." : "Genera el primer análisis."}</h2>
        <p>{active ? "El trabajo continúa en segundo plano aunque cierres esta página." : waitingForReview ? analysis.company.last_error : failed ? analysis.company.last_error : "Procesaremos primero los estados y métricas; los documentos aparecerán cuando exista una fuente oficial verificada."}</p>
      </div>
      {job && <div className="analysis-progress-meter" aria-label={`Progreso ${progress}%`}><div><span style={{ width: `${progress}%` }} /></div><b>{progress}%</b></div>}
      <ol className="analysis-steps">
        {(Object.keys(stepNames) as AnalysisStepCode[]).map((code, index) => {
          const step = job?.steps.find((item) => item.step_code === code);
          const status = step?.status || "pending";
          return <li className={status} key={code}><i>{status === "completed" ? "✓" : status === "skipped" ? "–" : index + 1}</i><div><b>{stepNames[code]}</b><span>{status === "running" ? "Procesando" : status === "completed" ? "Disponible" : status === "skipped" ? "Pendiente de fuente verificada" : status === "failed" ? "Requiere atención" : "Pendiente"}</span></div></li>;
        })}
      </ol>
      {!active && !waitingForReview && analysis.company.support_level !== "unsupported" && <button className="primary-button analysis-request-large" type="button" disabled={pending} onClick={requestAnalysis}>{pending ? "Registrando solicitud…" : failed ? "Reintentar análisis" : "Generar análisis"}<span>→</span></button>}
      {analysis.company.support_level === "unsupported" && <div className="coverage-note"><span>!</span><div><b>Sector todavía no compatible</b><p>La empresa permanece visible en el catálogo, pero sus estados requieren reglas sectoriales que no forman parte de este MVP.</p></div></div>}
      {error && <div className="form-error" role="alert">{error}</div>}
    </section>
    {active && <AnalysisReadingCards />}
    <footer className="data-footer"><span>Nunca publicamos cifras que fallen una validación crítica.</span><Link href="/empresas">Volver al catálogo ↗</Link></footer>
  </>;
}
