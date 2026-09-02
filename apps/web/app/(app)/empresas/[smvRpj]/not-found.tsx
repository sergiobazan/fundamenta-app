import Link from "next/link";

export default function CompanyNotFound() {
  return <section className="app-not-found"><span>404</span><h1>Empresa o estado no disponible.</h1><p>El recurso todavía no forma parte de la cobertura verificada del MVP.</p><Link className="document-button" href="/empresas">Volver a empresas →</Link></section>;
}
