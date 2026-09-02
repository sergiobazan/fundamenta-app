import { CompanyDirectory, type CompanyWithCoverage } from "@/components/CompanyDirectory";
import { getCompanies, getFilings } from "@/lib/financial";

export const metadata = { title: "Empresas" };

export default async function CompaniesPage() {
  const landingUrl = process.env.NEXT_PUBLIC_LANDING_URL || "http://localhost:4321";
  const companies = await getCompanies();
  const companiesWithCoverage: CompanyWithCoverage[] = await Promise.all(
    companies.map(async (company) => ({ ...company, filings: await getFilings(company.smv_rpj) })),
  );

  return <>
    <header className="app-header directory-header"><div><span className="overline">UNIVERSO DEL MVP</span><h1>Empresas</h1><p>Información oficial disponible, estado de cobertura y última actualización.</p></div><div className="directory-count"><strong>{companies.length}</strong><span>de 8 empresas<br/>incorporadas</span></div></header>
    <section className="coverage-note"><span>02</span><div><b>Cobertura deliberadamente pequeña</b><p>Una empresa sólo aparece cuando sus datos han sido ingeridos, normalizados y validados. Las seis restantes se incorporarán progresivamente.</p></div></section>
    <section className="directory-section"><CompanyDirectory companies={companiesWithCoverage} /></section>
    <footer className="data-footer"><span>Universo objetivo: ocho mineras no financieras supervisadas por la SMV.</span><a href={`${landingUrl}/como-funciona`}>Conocer el proceso de incorporación ↗</a></footer>
  </>;
}
