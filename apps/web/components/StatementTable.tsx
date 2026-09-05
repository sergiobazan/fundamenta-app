"use client";

import { useMemo, useState } from "react";
import type { FinancialFact } from "@/lib/types";

function formatValue(value: string | number | null, kind: FinancialFact["value_kind"]) {
  if (value === null) return "—";
  const amount = Number(value);
  return new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: kind === "per_share" ? 2 : 0,
    maximumFractionDigits: kind === "per_share" ? 4 : 0,
  }).format(amount);
}

export function StatementTable({ facts, year, unverifiedScale = false, compare = false }: { facts: FinancialFact[]; year: number; unverifiedScale?: boolean; compare?: boolean }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return facts;
    return facts.filter((fact) =>
      [fact.original_label, fact.normalized_concept, fact.account_code]
        .filter(Boolean).some((value) => String(value).toLowerCase().includes(term)),
    );
  }, [facts, query]);

  return <>
    {compare && <div className="annual-comparison">
      {compare && <><p>Cifras de {year - 1} presentadas como comparativas en el informe de {year}; pueden incluir reclasificaciones o ajustes. Diferencia = actual − anterior. Variación = diferencia / anterior; se omite con base cero o negativa.</p>{unverifiedScale && <p className="metric-scale-warning">Escala no verificada: las diferencias conservan la magnitud reportada, sin asumir unidades, miles o millones.</p>}</>}
    </div>}
    <div className="statement-tools"><label><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar cuenta o concepto" /></label><span>{filtered.length} conceptos normalizados</span></div>
    <div className="statement-table-wrap"><table className="statement-table"><thead><tr><th>Cuenta reportada</th><th>Concepto normalizado</th><th>{year}</th><th>{year - 1} · Comparativo</th>{compare && <><th>Diferencia</th><th>Variación %</th></>}</tr></thead><tbody>{filtered.map((fact) => {
      const difference = fact.current_amount !== null && fact.comparative_amount !== null ? Number(fact.current_amount) - Number(fact.comparative_amount) : null;
      return <tr key={`${fact.account_code}-${fact.normalized_concept}`}><td><b>{fact.original_label}</b><small>{fact.account_code}</small></td><td><code>{fact.normalized_concept || "Sin mapear"}</code></td><td>{formatValue(fact.current_amount, fact.value_kind)}</td><td>{formatValue(fact.comparative_amount, fact.value_kind)}</td>{compare && <><td>{formatValue(difference, fact.value_kind)}</td><td>{difference !== null && Number(fact.comparative_amount) > 0 ? new Intl.NumberFormat("es-PE", { style: "percent", maximumFractionDigits: 1, signDisplay: "exceptZero" }).format(difference / Number(fact.comparative_amount)) : "—"}</td></>}</tr>;
    })}</tbody></table>{!filtered.length && <div className="empty-result"><b>Sin coincidencias</b><p>No hay conceptos que coincidan con la búsqueda.</p></div>}</div>
  </>;
}
