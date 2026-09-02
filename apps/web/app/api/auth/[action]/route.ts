import { API_URL, SESSION_COOKIE } from "@/lib/backend";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const allowed=new Set(['login','register']);
export async function POST(request:NextRequest,{params}:{params:Promise<{action:string}>}){const {action}=await params;if(!allowed.has(action))return NextResponse.json({detail:'Ruta no encontrada'},{status:404});const body=await request.text();let upstream:Response;try{upstream=await fetch(`${API_URL}/auth/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body,cache:'no-store'})}catch{return NextResponse.json({detail:'El servicio de autenticación no está disponible'},{status:503})}const payload=await upstream.json().catch(()=>({detail:'Respuesta inválida'}));if(!upstream.ok)return NextResponse.json(payload,{status:upstream.status});const jar=await cookies();jar.set(SESSION_COOKIE,payload.session_token,{httpOnly:true,sameSite:'lax',secure:process.env.NODE_ENV==='production',path:'/',expires:new Date(payload.expires_at)});return NextResponse.json({user:payload.user},{status:action==='register'?201:200})}
