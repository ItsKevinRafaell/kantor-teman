"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useUserRole } from "../lib/useUserRole";

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useUserRole();
  const router = useRouter();

  useEffect(() => {
    if (!isAdmin) {
      router.replace("/dashboard");
    }
  }, [isAdmin, router]);

  if (!isAdmin) return null;
  return <>{children}</>;
}
