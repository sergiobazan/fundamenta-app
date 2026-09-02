"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/panel", icon: "⌂", label: "Resumen" },
  { href: "/empresas", icon: "▦", label: "Empresas" },
  { href: "/comparador", icon: "⇄", label: "Comparador" },
  { href: "/eventos", icon: "◷", label: "Eventos" },
];

export function AppNav() {
  const pathname = usePathname();
  return <nav aria-label="Navegación del panel">
    {items.map((item) => <Link className={pathname.startsWith(item.href) ? "active" : ""} href={item.href} key={item.href}><span>{item.icon}</span>{item.label}</Link>)}
  </nav>;
}
