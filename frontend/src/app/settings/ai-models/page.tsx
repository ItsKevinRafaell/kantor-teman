"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AIModelsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/settings?tab=ai-engine");
  }, [router]);
  return null;
}
