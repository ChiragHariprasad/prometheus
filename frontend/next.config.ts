import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  images: {
    domains: ["prometheus.com", "api.prometheus.com", "cdn.prometheus.com"],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.prometheus.com",
      },
    ],
  },

  experimental: {
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },

  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `http://backend:8000/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;