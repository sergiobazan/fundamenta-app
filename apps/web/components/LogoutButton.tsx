"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LogoutButton() {
  const router = useRouter(); const [loading,setLoading]=useState(false);
  return <button className="logout" disabled={loading} onClick={async()=>{setLoading(true);await fetch('/api/auth/logout',{method:'POST'});router.push('/login');router.refresh();}}><span>↪</span>{loading?'Saliendo…':'Cerrar sesión'}</button>;
}
