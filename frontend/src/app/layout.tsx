import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import ClientLayout from "../components/ClientLayout";
import { ThemeProvider } from "../components/ThemeProvider";

export const metadata: Metadata = {
  title: "Kantor Teman",
  description: "CRM pribadi untuk prospek bisnis lokal",
  icons: {
    icon: [
      { url: "/api/favicon" },
      { url: "/brand/derived/favicon.ico", type: "image/x-icon" },
      { url: "/brand/derived/favicon-32.png", type: "image/png", sizes: "32x32" },
      { url: "/brand/derived/favicon-48.png", type: "image/png", sizes: "48x48" },
      { url: "/brand/derived/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    apple: "/brand/derived/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Kantor Teman",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#f5a700" />
        <meta name="mobile-web-app-capable" content="yes" />
        <script dangerouslySetInnerHTML={{ __html: `
if('serviceWorker' in navigator){
  navigator.serviceWorker.getRegistrations().then(function(r){
    r.forEach(function(reg){
      if(!reg.active || !reg.active.scriptURL || reg.active.scriptURL.indexOf('swe-worker-')===-1 || reg.active.scriptURL.indexOf('5c72df51bb1f6ee0')!==-1)
        reg.unregister();
    });
  });
}` }} />
      </head>
      <body className="bg-[var(--bg-canvas)] dark:bg-[var(--bg-canvas)] text-gray-900 dark:text-neutral-50 antialiased">
        <ThemeProvider>
          <ClientLayout>{children}</ClientLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}
