import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Next 16.3 CLI capture returns an empty --showConfig stream under Node 24.
  // The stable TypeScript compiler API avoids that upstream subprocess issue.
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
