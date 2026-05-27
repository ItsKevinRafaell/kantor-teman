"use client";

import { useState, useEffect } from "react";

export function useUserRole() {
  const [role, setRole] = useState<"admin" | "member">("admin");

  useEffect(() => {
    const stored = localStorage.getItem("kt_role");
    setRole(stored === "member" ? "member" : "admin");
  }, []);

  return { role, isAdmin: role === "admin", isMember: role === "member" };
}
