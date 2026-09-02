import { backendFetch } from "@/lib/backend";
import { NextRequest, NextResponse } from "next/server";
export async function POST(request:NextRequest){const data=await request.formData();const response=await backendFetch('/auth/profile/avatar',{method:'POST',body:data});const payload=await response.json().catch(()=>({detail:'Respuesta inválida'}));return NextResponse.json(payload,{status:response.status})}
