import type { NextConfig } from "next";
const config: NextConfig = {
  skipTrailingSlashRedirect: true,
  distDir: process.env.SALUD_DEMO_BUILD === "1" ? ".next-demo" : ".next",
  ...(process.env.SALUD_DEMO_BUILD === "1" ? { experimental: { cpus: 2 } } : {}),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/:path*/`,
      },
    ];
  },
};
export default config;
