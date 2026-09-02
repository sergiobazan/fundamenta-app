"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setLoading(true);
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form.entries());
    try {
      const response = await fetch(`/api/auth/${mode}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "No pudimos completar la solicitud");
      router.push("/panel"); router.refresh();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Ocurrió un error"); }
    finally { setLoading(false); }
  }

  const register = mode === "register";
  return <form className="auth-form" onSubmit={submit}>
    {register && <label>Nombre completo<input name="full_name" type="text" autoComplete="name" minLength={2} maxLength={100} placeholder="María Torres" required /></label>}
    <label>Correo electrónico<input name="email" type="email" autoComplete="email" placeholder="tu@correo.com" required /></label>
    <label>Contraseña<input name="password" type="password" autoComplete={register ? "new-password" : "current-password"} minLength={register ? 10 : 1} maxLength={128} placeholder={register ? "10 caracteres como mínimo" : "Tu contraseña"} required /></label>
    {error && <div className="form-error" role="alert">{error}</div>}
    <button className="primary-button" type="submit" disabled={loading}>{loading ? "Procesando…" : register ? "Crear cuenta" : "Ingresar"}<span>→</span></button>
    {register && <small>Al registrarte aceptas que esta es una versión piloto y nuestra <a href={`${process.env.NEXT_PUBLIC_LANDING_URL || "http://localhost:4321"}/privacidad`}>política de privacidad</a>.</small>}
  </form>;
}
