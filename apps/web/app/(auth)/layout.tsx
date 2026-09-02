import { Brand } from "@/components/Brand";
import { getCurrentUser } from "@/lib/backend";
import { redirect } from "next/navigation";

export default async function AuthLayout({children}:{children:React.ReactNode}){if(await getCurrentUser())redirect('/panel');return <main className="auth-shell"><section className="auth-aside"><Brand/><div><span className="eyebrow">Información que se puede cuestionar</span><h2>Los números primero.<br/><em>La fuente siempre.</em></h2><div className="auth-stat"><strong>15</strong><span>indicadores calculados<br/>en el caso piloto</span></div></div><p>Fundamenta no recomienda comprar ni vender valores.</p></section><section className="auth-content">{children}</section></main>}
