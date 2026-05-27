import AdminGuard from "../../components/AdminGuard";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return <AdminGuard>{children}</AdminGuard>;
}
