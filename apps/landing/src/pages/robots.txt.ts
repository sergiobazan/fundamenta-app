import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const base = site || new URL("http://localhost:4321");
  return new Response(
    `User-agent: *\nAllow: /\nDisallow: /gracias\n\nSitemap: ${new URL("sitemap-index.xml", base)}\n`,
    { headers: { "Content-Type": "text/plain; charset=utf-8" } },
  );
};
