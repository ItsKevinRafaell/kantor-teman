"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface Crumb {
  label: string;
  href?: string;
}

interface Props {
  items: Crumb[];
}

export default function Breadcrumb({ items }: Props) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 mb-3">
      {items.map((c, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={i} className="flex items-center gap-1.5">
            {c.href && !isLast ? (
              <Link href={c.href} className="hover:text-amber-600 transition-colors">{c.label}</Link>
            ) : (
              <span className={isLast ? "font-semibold text-gray-700 dark:text-gray-200" : ""}>{c.label}</span>
            )}
            {!isLast && <ChevronRight size={12} className="text-gray-300 dark:text-gray-600" />}
          </span>
        );
      })}
    </nav>
  );
}
