import { cookies } from "next/headers";
import type { User } from "./types";

export const API_URL = process.env.API_URL || "http://localhost:8000";
export const SESSION_COOKIE = "fundamenta_session";

export async function getSessionToken(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value || null;
}

export async function backendFetch(path: string, init: RequestInit = {}) {
  const token = await getSessionToken();
  return fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
}

export async function getCurrentUser(): Promise<User | null> {
  const response = await backendFetch("/auth/me");
  if (!response.ok) return null;
  const payload = (await response.json()) as { user: User };
  return payload.user;
}
