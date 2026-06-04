/** @type {import('next').NextConfig} */
const withPWA = require("@ducanh2912/next-pwa").default({
  dest: "public",
  cacheOnFrontEndNav: true,
  aggressiveFrontEndNavCaching: true,
  reloadOnOnline: true,
  disable: process.env.NODE_ENV === "development",
  workboxOptions: {
    runtimeCaching: [
      {
        urlPattern: /^https:\/\/api\.kantorteman\.my\.id\/api\/(documents\/preview|documents\/generate|generated-documents)/,
        handler: 'NetworkOnly',
      },
    ],
  },
});

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.kantorteman.my.id";

const nextConfig = {
  trailingSlash: true,
  images: {
    unoptimized: false,
  },
  async rewrites() {
    return [
      { source: "/r/:slug", destination: `${BACKEND_URL}/r/:slug` },
      { source: "/r/:slug/", destination: `${BACKEND_URL}/r/:slug` },
      { source: "/p/:slug", destination: `${BACKEND_URL}/p/:slug` },
      { source: "/p/:slug/", destination: `${BACKEND_URL}/p/:slug` },
    ];
  },
  async redirects() {
    return [
      { source: "/map", destination: "/leads?tab=peta", permanent: true },
      { source: "/map/", destination: "/leads?tab=peta", permanent: true },
      { source: "/scraper", destination: "/leads?tab=scrape", permanent: true },
      { source: "/scraper/", destination: "/leads?tab=scrape", permanent: true },
    ];
  },
};

module.exports = withPWA(nextConfig);
