import { CompanyDirectory } from "@/components/CompanyDirectory";
import { getCompanies } from "@/lib/financial";

export const metadata = { title: "Empresas" };

export default async function CompaniesPage() {
  const landingUrl = process.env.NEXT_PUBLIC_LANDING_URL || "http://localhost:4321";
  const companies = await getCompanies();
  const analyzed = companies.filter((company) => company.has_analysis).length;
  const compatible = companies.filter((company) => company.support_level !== "unsupported").length;

  return <>
    <header className="app-header directory-header"><div><span className="overline">CATÁLOGO SMV</span><h1>Empresas</h1><p>Busca un emisor y abre o genera su análisis con fuentes oficiales.</p></div><div className="directory-count"><strong>{analyzed}</strong><span>con análisis<br/>de {companies.length} catalogadas</span></div></header>
    <section className="coverage-note"><span>↗</span><div><b>La cobertura crece con cada solicitud</b><p>{compatible} empresas tienen un formato compatible con el alcance actual. Los estados y métricas aparecen primero; las notas se publican sólo cuando verificamos su fuente.</p></div></section>
    <section className="directory-section"><CompanyDirectory companies={companies} /></section>
    <footer className="data-footer"><span>Minería tiene cobertura completa; otros emisores no financieros reciben métricas compatibles.</span><a href={`${landingUrl}/como-funciona`}>Conocer el proceso de incorporación ↗</a></footer>
  </>;
}
