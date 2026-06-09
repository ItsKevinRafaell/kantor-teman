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
const backendOrigin = (() => {
  try {
    return new URL(BACKEND_URL).origin;
  } catch {
    return "https://api.kantorteman.my.id";
  }
})();
const connectSrc = ["'self'", backendOrigin, "wss:"];
const imgSrc = ["'self'", "data:", backendOrigin, "blob:"];

const nextConfig = {
  trailingSlash: true,
  images: {
    unoptimized: false,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              // Note: 'unsafe-inline' required for Next.js App Router dynamic styles/scripts
              // 'unsafe-eval' removed — not needed by App Router
              "style-src 'self' 'unsafe-inline'",
              // Note: 'unsafe-inline' required; Next.js generates inline styles dynamically
              `img-src ${imgSrc.join(" ")}`,
              "frame-src 'self' data: blob:",
              "font-src 'self'",
              `connect-src ${connectSrc.join(" ")}`,
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
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
