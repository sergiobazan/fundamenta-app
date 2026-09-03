import { Brand } from "@/components/Brand";
import { AppNav } from "@/components/AppNav";
import { LogoutButton } from "@/components/LogoutButton";
import { getCurrentUser } from "@/lib/backend";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function AppLayout({children}:{children:React.ReactNode}){const user=await getCurrentUser();if(!user)redirect('/login');const apiUrl=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';return <div className="app-shell"><aside className="sidebar"><Brand/><AppNav/><div className="sidebar-bottom"><Link className="user-chip" href="/perfil"><img src={user.avatar_url?`${apiUrl}${user.avatar_url}`:'/default-avatar.svg'} alt={user.avatar_url?`Foto de perfil de ${user.full_name}`:'Avatar predeterminado de Fundamenta'}/><div><b>{user.full_name}</b><span>Editar perfil</span></div></Link><LogoutButton/></div></aside><main className="app-main">{children}</main><nav className="mobile-tabs" aria-label="Navegación móvil"><Link href="/panel"><span>⌂</span>Resumen</Link><Link href="/empresas"><span>▦</span>Empresas</Link><Link href="/buscar"><span>⌕</span>Buscar</Link><Link href="/comparador"><span>⇄</span>Comparar</Link><Link href="/eventos"><span>◷</span>Eventos</Link><Link href="/perfil"><span>○</span>Perfil</Link><LogoutButton/></nav></div>}
