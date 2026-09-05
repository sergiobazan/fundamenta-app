import type { CompanyAnalysis } from "./types";

export function pollAnalysis(rpj: string, update: (value: CompanyAnalysis) => void) {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout>;
  let controller: AbortController | undefined;
  let signature = "";
  let delay = 3000;
  async function poll() {
    if (stopped) return;
    if (document.hidden) { timer = setTimeout(poll, 15000); return; }
    controller = new AbortController();
    const timeout = setTimeout(() => controller?.abort(), 15000);
    let active = true;
    try {
      const response = await fetch(`/api/companies/${encodeURIComponent(rpj)}/analysis`, {
        cache: "no-store", signal: controller.signal,
      });
      if (!response.ok) throw new Error("No se pudo consultar el estado");
      const value = await response.json() as CompanyAnalysis;
      if (stopped) return;
      const nextSignature = JSON.stringify(value.job);
      delay = nextSignature === signature ? Math.min(delay * 1.5, 15000) : 3000;
      signature = nextSignature;
      active = Boolean(value.job && ["queued", "running", "retrying"].includes(value.job.status));
      update(value);
    } catch {
      delay = Math.min(delay * 2, 15000);
    } finally {
      clearTimeout(timeout);
      if (!stopped && active) timer = setTimeout(poll, delay);
    }
  }
  timer = setTimeout(poll, delay);
  return () => { stopped = true; clearTimeout(timer); controller?.abort(); };
}
