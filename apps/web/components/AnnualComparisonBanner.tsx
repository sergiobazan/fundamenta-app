import Link from "next/link";

export function AnnualComparisonBanner({ title, year, scope, href, sourceUrl }: {
  title: string; year: number; scope: string; href: string; sourceUrl?: string | null;
}) {
  return <section className="note-source-bar">
    <div><span aria-hidden="true">↔</span><p><b>{title}</b><small>{year} · {scope === "individual" ? "Individual" : "Consolidado"} · Comparación anual</small></p></div>
    <div className="note-source-actions">
      <Link href={href}>Comparar {year} vs. {year - 1} →</Link>
      {sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer">Abrir PDF oficial ↗</a>}
    </div>
  </section>;
}
