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
      { url: "/favicon.ico" },
    ],
    apple: "/apple-touch-icon.png",
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
      </head>
      <body className="bg-[var(--bg-canvas)] dark:bg-[var(--bg-canvas)] text-gray-900 dark:text-neutral-50 antialiased">
        <ThemeProvider>
          <ClientLayout>{children}</ClientLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}
