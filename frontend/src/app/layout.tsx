import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import ClientLayout from "../components/ClientLayout";
import { ThemeProvider } from "../components/ThemeProvider";

export const metadata: Metadata = {
  title: "Kantor Teman",
  description: "CRM pribadi untuk prospek bisnis lokal",
  icons: { icon: "/logo-brandmark.png", apple: "/icons/icon-152x152.png" },
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
      <body className="bg-[#fcfaf7] dark:bg-[#242423] text-gray-900 dark:text-[#fcfaf7] antialiased">
        <ThemeProvider>
          <ClientLayout>{children}</ClientLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}
