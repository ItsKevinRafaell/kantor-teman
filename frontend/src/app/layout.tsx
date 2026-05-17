import type { Metadata } from "next";
import "./globals.css";
import ClientLayout from "../components/ClientLayout";
import { ThemeProvider } from "../components/ThemeProvider";

export const metadata: Metadata = {
  title: "Kantor Teman",
  description: "CRM pribadi untuk prospek bisnis lokal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" suppressHydrationWarning>
      <body className="bg-[#fcfaf7] dark:bg-[#242423] text-gray-900 dark:text-[#fcfaf7] antialiased">
        <ThemeProvider>
          <ClientLayout>{children}</ClientLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}
