import AdminGuard from "../../../components/AdminGuard";

export default function BrandKitLayout({ children }: { children: React.ReactNode }) {
  return <AdminGuard>{children}</AdminGuard>;
}
