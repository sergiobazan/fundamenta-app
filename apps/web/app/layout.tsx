import type { Metadata } from "next";
import "./globals.css";
import "./search.css";

export const metadata:Metadata={title:{default:'Fundamenta App',template:'%s | Fundamenta'},description:'Panel de investigación financiera verificable para empresas peruanas.',robots:{index:false,follow:false}};

export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="es-PE"><body>{children}</body></html>}
