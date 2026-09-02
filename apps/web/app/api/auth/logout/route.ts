import { API_URL, SESSION_COOKIE } from "@/lib/backend";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
export async function POST(){const jar=await cookies();const token=jar.get(SESSION_COOKIE)?.value;if(token)await fetch(`${API_URL}/auth/logout`,{method:'POST',headers:{Authorization:`Bearer ${token}`}}).catch(()=>null);jar.delete(SESSION_COOKIE);return new NextResponse(null,{status:204})}
