"use client";
import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
export function ActivityTracker() {
  const path = usePathname();
  const params = useSearchParams();
  const previous = useRef("");
  const pair = `${params.get("left") || ""}|${params.get("right") || ""}`;
  const year = params.get("year") || params.get("currentYear"); const scope = params.get("scope");
  useEffect(() => {
    const signature = `${path}|${year}|${scope}|${pair}`;
    if (previous.current === signature) return;
    const changedPeriod = previous.current.split("|")[0] === path;
    previous.current = signature;
    const company = path.match(/^\/empresas\/([A-Za-z0-9]+)(?:\/|$)/)?.[1];
    const send = (action: string) => {
      void fetch("/api/activity", { method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true,
        body: JSON.stringify({ event_key: crypto.randomUUID(), action, company_rpj: company,
          fiscal_year: year && /^\d{4}$/.test(year) ? Number(year) : undefined,
          scope: ["individual", "consolidated"].includes(scope || "") ? scope : undefined })
      }).catch(() => { /* Navigation continues; errors remain observable in HTTP logs. */ });
    };
    if (path.includes("/comparar") || path === "/comparador") send("comparison.view");
    else if (company) send(changedPeriod ? "period.change" : "company.view");
    else if (path === "/buscar") send("search.view");
  }, [path, year, scope, pair]);
  useEffect(() => {
    function clicked(event: MouseEvent) {
      const anchor = event.target instanceof Element ? event.target.closest("a") : null;
      const company = anchor?.dataset.company || path.match(/^\/empresas\/([A-Za-z0-9]+)(?:\/|$)/)?.[1];
      if (!anchor || !company || !/^https?:/.test(anchor.href) || !(/\.pdf(?:[?#]|$)/i.test(anchor.href) || anchor.dataset.activity === "source")) return;
      void fetch("/api/activity", { method: "POST", headers: { "Content-Type": "application/json" }, keepalive: true,
        body: JSON.stringify({ event_key: crypto.randomUUID(), action: "source.open", company_rpj: company }) }).catch(() => {});
    }
    document.addEventListener("click", clicked);
    return () => document.removeEventListener("click", clicked);
  }, [path]);
  return null;
}
