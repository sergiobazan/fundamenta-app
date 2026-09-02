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

export function StatementTable({ facts, year }: { facts: FinancialFact[]; year: number }) {
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
    <div className="statement-tools"><label><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar cuenta o concepto" /></label><span>{filtered.length} conceptos normalizados</span></div>
    <div className="statement-table-wrap"><table className="statement-table"><thead><tr><th>Cuenta reportada</th><th>Concepto normalizado</th><th>{year}</th><th>Comparativo</th></tr></thead><tbody>{filtered.map((fact) => <tr key={`${fact.account_code}-${fact.normalized_concept}`}><td><b>{fact.original_label}</b><small>{fact.account_code}</small></td><td><code>{fact.normalized_concept || "Sin mapear"}</code></td><td>{formatValue(fact.current_amount, fact.value_kind)}</td><td>{formatValue(fact.comparative_amount, fact.value_kind)}</td></tr>)}</tbody></table>{!filtered.length && <div className="empty-result"><b>Sin coincidencias</b><p>No hay conceptos que coincidan con la búsqueda.</p></div>}</div>
  </>;
}
