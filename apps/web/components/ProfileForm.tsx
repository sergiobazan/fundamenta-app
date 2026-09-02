"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { User } from "@/lib/types";

export function ProfileForm({ user }: { user: User }) {
  const router=useRouter(); const fileRef=useRef<HTMLInputElement>(null); const [avatar,setAvatar]=useState(user.avatar_url); const [message,setMessage]=useState(""); const [error,setError]=useState(""); const [loading,setLoading]=useState(false);
  const apiUrl=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
  async function save(event:FormEvent<HTMLFormElement>){event.preventDefault();setLoading(true);setError('');setMessage('');const data=new FormData(event.currentTarget);const response=await fetch('/api/profile',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(data.entries()))});const payload=await response.json().catch(()=>({}));if(response.ok){setMessage('Perfil actualizado.');router.refresh()}else setError(payload.detail||'No se pudo actualizar');setLoading(false)}
  async function upload(){const file=fileRef.current?.files?.[0];if(!file)return;setLoading(true);setError('');const data=new FormData();data.append('avatar',file);const response=await fetch('/api/profile/avatar',{method:'POST',body:data});const payload=await response.json().catch(()=>({}));if(response.ok){setAvatar(payload.user.avatar_url);setMessage('Imagen actualizada.');router.refresh()}else setError(payload.detail||'No se pudo subir la imagen');setLoading(false)}
  return <div className="profile-editor">
    <div className="avatar-editor"><img src={avatar?`${apiUrl}${avatar}`:'/default-avatar.svg'} alt={avatar?`Foto de perfil de ${user.full_name}`:'Avatar predeterminado de Fundamenta'} /><div><label className="secondary-button" htmlFor="avatar">Elegir imagen</label><input ref={fileRef} id="avatar" type="file" accept="image/jpeg,image/png,image/webp" onChange={upload} hidden/><p>JPG, PNG o WebP · máximo 2 MB</p></div></div>
    <form onSubmit={save} className="profile-form"><label>Nombre completo<input name="full_name" defaultValue={user.full_name} minLength={2} maxLength={100} required /></label><label>Correo electrónico<input value={user.email} disabled /><small>El cambio de correo no forma parte de este MVP.</small></label><label>Sobre ti<textarea name="bio" defaultValue={user.bio} maxLength={280} rows={4} placeholder="Cuéntanos cómo utilizas información financiera." /></label>{message&&<div className="form-success" role="status">{message}</div>}{error&&<div className="form-error" role="alert">{error}</div>}<button className="primary-button" disabled={loading}>{loading?'Guardando…':'Guardar cambios'}</button></form>
  </div>;
}
