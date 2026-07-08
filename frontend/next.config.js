/** @type {import('next').NextConfig} */
const localApiUrl = process.env.NEXT_PUBLIC_API_URL || "";
const isLocalApi = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/.test(localApiUrl);

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.kantorteman.my.id";
const backendOrigin = (() => {
  try {
    return new URL(BACKEND_URL).origin;
  } catch {
    return "https://api.kantorteman.my.id";
  }
})();
const FALLBACK_PROD = "https://api.kantorteman.my.id";
const connectSrc = ["'self'", backendOrigin, FALLBACK_PROD, "wss:", "https://maps.googleapis.com", "https://maps.gstatic.com", "https://*.googleapis.com", "https://*.gstatic.com"];
const imgSrc = ["'self'", "data:", backendOrigin, FALLBACK_PROD, "blob:", "https://maps.googleapis.com", "https://maps.gstatic.com", "https://*.tile.openstreetmap.org", "https://*.openstreetmap.org", "https://*.gstatic.com", "https://*.google.com"];
const fontSrc = ["'self'", "https://fonts.gstatic.com", "https://*.gstatic.com"];
const scriptSrc = ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://static.cloudflareinsights.com"];
if (process.env.NODE_ENV === "development") {
  connectSrc.push("http://localhost:8000", "http://127.0.0.1:8000");
  imgSrc.push("http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000");
}

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
              `script-src ${scriptSrc.join(" ")}`,
              "style-src 'self' 'unsafe-inline'",
              `img-src ${imgSrc.join(" ")}`,
              "frame-src 'self' data: blob:",
              `font-src ${fontSrc.join(" ")}`,
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
      // Public report links (already served as HTML)
      { source: "/r/:slug", destination: `${BACKEND_URL}/r/:slug` },
      { source: "/r/:slug/", destination: `${BACKEND_URL}/r/:slug` },
      { source: "/p/:slug", destination: `${BACKEND_URL}/p/:slug` },
      { source: "/p/:slug/", destination: `${BACKEND_URL}/p/:slug` },
      // Proxy every JSON API call through Vercel so dashboard fetches are
      // same-origin. Backend cookies (samesite=lax, domain=.kantorteman.my.id)
      // would otherwise be blocked by browsers because the SPA lives on
      // a different registrable domain (kantor-teman-five.vercel.app) than
      // the API (api.kantorteman.my.id). Same-origin /api/* keeps the
      // cookie chain intact without re-architecting to samesite=none.
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
      // Public OG-image, og-meta, favicon, pwa manifest, sw.js go
      // through too so trailing-slash redirects from cross-site SSR
      // self-fetch don't 308-loop.
      { source: "/og-image/:slug", destination: `${BACKEND_URL}/api/og-image/:slug` },
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

module.exports = nextConfig;
