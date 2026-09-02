import { backendFetch } from "@/lib/backend";
import { NextRequest, NextResponse } from "next/server";
export async function PATCH(request:NextRequest){const response=await backendFetch('/auth/profile',{method:'PATCH',body:await request.text()});const payload=await response.json().catch(()=>({detail:'Respuesta inválida'}));return NextResponse.json(payload,{status:response.status})}
