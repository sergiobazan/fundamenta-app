import Link from "next/link";
import NotesReport from "@/components/notes-report";

export const metadata = { title: "Informe de notas con IA" };

export default async function ReportPage({ params, searchParams }: {
  params: Promise<{ smvRpj: string }>;
  searchParams: Promise<{ year?: string; scope?: string }>;
}) {
  const { smvRpj } = await params;
  const query = await searchParams;
  const value = Number(query.year);
  const year = Number.isInteger(value) && value >= 2000 && value <= 2100 ? value : 2025;
  const scope = query.scope === "individual" ? "individual" : "consolidated";
  return <>
    <nav className="app-breadcrumbs" aria-label="Migas de pan">
      <Link href={`/empresas/${smvRpj}`}>{smvRpj}</Link><span>/</span>
      <Link href={`/empresas/${smvRpj}/notas?year=${year}&scope=${scope}`}>Notas</Link>
      <span>/</span><b>Informe con IA</b>
    </nav>
    <header className="app-header notes-header"><div>
      <span className="overline">INVESTIGACIÓN ASISTIDA · {smvRpj}</span>
      <h1>Lo que cuentan las notas</h1>
      <p>Riesgos, alertas y cambios entre ejercicios · {year} · {scope === "individual" ? "Individual" : "Consolidado"}</p>
    </div></header>
    <NotesReport key={`${smvRpj}-${year}-${scope}`} smvRpj={smvRpj} year={year} scope={scope} />
  </>;
}
