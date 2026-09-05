"use client";

import { useMemo, useState } from "react";
import type { Company } from "@/lib/types";
import { CompanyAnalysisAction } from "./CompanyAnalysisAction";

const statusNames: Record<Company["analysis_status"], string> = {
  available: "Disponible",
  partial: "Análisis parcial",
  queued: "En cola",
  processing: "Procesando",
  review_required: "Requiere revisión",
  failed: "Falló",
  not_analyzed: "No analizada",
  unsupported: "No compatible",
};

function companyInitials(legalName: string) {
  return legalName
    .split(" ")
    .filter((part) => part.length > 2)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");
}

export function CompanyDirectory({ companies }: { companies: Company[] }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return companies;
    return companies.filter((company) =>
      [company.legal_name, company.smv_rpj, company.ruc, company.sector]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term)),
    );
  }, [companies, query]);

  return <>
    <div className="directory-tools">
      <label><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por empresa, RUC o código SMV" /></label>
      <span>{filtered.length} {filtered.length === 1 ? "empresa" : "empresas"}</span>
    </div>
    <div className="company-list">
      {filtered.map((company) => <article className="company-row" key={company.smv_rpj}>
        <span className="company-code">{companyInitials(company.legal_name)}</span>
        <div className="company-identity"><span>{company.sector || "Sector sin clasificar"}</span><h2>{company.legal_name}</h2><p>SMV {company.smv_rpj}{company.ruc ? ` · RUC ${company.ruc}` : ""}</p></div>
        <div className="coverage"><span>Último periodo</span><b>{company.has_analysis && company.latest_fiscal_year ? `${company.latest_fiscal_year} · Anual` : "Por analizar"}</b></div>
        <div className="coverage"><span>Cobertura</span><b>{company.has_analysis ? `${company.filings_count}/3 estados` : company.support_level === "full" ? "Análisis completo" : company.support_level === "basic" ? "Análisis básico" : "Fuera del MVP"}</b></div>
        <div className={`data-status ${company.analysis_status}`}><i></i><span>{statusNames[company.analysis_status]}</span></div>
        <CompanyAnalysisAction company={company} />
      </article>)}
      {!filtered.length && <div className="empty-result"><b>Sin coincidencias</b><p>Prueba con el nombre legal, RUC o código SMV.</p></div>}
    </div>
  </>;
}
