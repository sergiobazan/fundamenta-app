import { AuthForm } from "@/components/AuthForm";
import Link from "next/link";
export const metadata={title:'Crear cuenta'};
export default function Register(){return <div className="auth-card"><span className="mobile-brand">fundamenta</span><div className="auth-heading"><span>Acceso al piloto</span><h1>Crea tu cuenta.</h1><p>Empieza con el caso financiero de Buenaventura 2025.</p></div><AuthForm mode="register"/><p className="auth-switch">¿Ya tienes cuenta? <Link href="/login">Ingresa</Link></p></div>}
