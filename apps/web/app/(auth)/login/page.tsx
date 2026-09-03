import { AuthForm } from "@/components/AuthForm";
import Link from "next/link";
export const metadata={title:'Ingresar'};
export default function Login(){return <div className="auth-card"><span className="mobile-brand">fundamenta</span><div className="auth-heading"><span>Bienvenido de vuelta</span><h1>Ingresa a tu panel.</h1><p>Continúa investigando con datos y fuentes visibles.</p></div><AuthForm mode="login"/><p className="auth-switch">¿Aún no tienes cuenta? <Link href="/registro">Regístrate</Link></p></div>}
