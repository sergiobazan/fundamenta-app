"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Company, Filing } from "@/lib/types";

export type CompanyWithCoverage = Company & {
  filings: Filing[];
};

export function CompanyDirectory({ companies }: { companies: CompanyWithCoverage[] }) {
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
      {filtered.map((company) => {
        const years = company.filings.map((filing) => filing.fiscal_year);
        const latestYear = years.length ? Math.max(...years) : null;
        const currentFilings = company.filings.filter(
          (filing) => filing.fiscal_year === latestYear && filing.scope === "consolidated",
        );
        const failed = currentFilings.reduce((total, filing) => total + Number(filing.failed_validations), 0);
        return <Link className="company-row" href={`/empresas/${company.smv_rpj}`} key={company.smv_rpj}>
          <span className="company-code">{company.legal_name.split(" ").filter((part) => part.length > 2).slice(0, 2).map((part) => part[0]).join("")}</span>
          <div className="company-identity"><span>{company.sector || "Sector sin clasificar"}</span><h2>{company.legal_name}</h2><p>SMV {company.smv_rpj}{company.ruc ? ` · RUC ${company.ruc}` : ""}</p></div>
          <div className="coverage"><span>Último periodo</span><b>{latestYear || "Pendiente"} · Anual</b></div>
          <div className="coverage"><span>Cobertura</span><b>{currentFilings.length}/3 estados</b></div>
          <div className={`data-status ${failed ? "partial" : "verified"}`}><i></i><span>{failed ? "Revisión necesaria" : "Verificado"}</span></div>
          <b className="row-arrow">→</b>
        </Link>;
      })}
      {!filtered.length && <div className="empty-result"><b>Sin coincidencias</b><p>Prueba con el nombre legal, RUC o código SMV.</p></div>}
    </div>
  </>;
}
