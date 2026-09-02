import { ProfileForm } from "@/components/ProfileForm";
import { getCurrentUser } from "@/lib/backend";
import { redirect } from "next/navigation";
export const metadata={title:'Mi perfil'};
export default async function Profile(){const user=await getCurrentUser();if(!user)redirect('/login');return <><header className="app-header"><div><span className="overline">CUENTA</span><h1>Mi perfil</h1><p>Administra cómo apareces dentro de Fundamenta.</p></div></header><section className="profile-card"><ProfileForm user={user}/></section><section className="account-note"><h2>Seguridad de la cuenta</h2><p>Tu contraseña se almacena con Argon2. Las sesiones tienen una vigencia máxima de 30 días y cerrar sesión revoca la sesión activa.</p></section></>}
