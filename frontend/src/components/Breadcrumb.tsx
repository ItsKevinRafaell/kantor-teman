"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight, ArrowLeft } from "lucide-react";

interface Crumb {
  label: string;
  href?: string;
}

interface Props {
  items: Crumb[];
  showBack?: boolean;
  backHref?: string;
}

export default function Breadcrumb({ items, showBack, backHref }: Props) {
  const router = useRouter();

  function handleBack() {
    if (backHref) {
      router.push(backHref);
    } else {
      router.back();
    }
  }

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 mb-3">
      {showBack && (
        <button
          onClick={handleBack}
          className="flex items-center gap-1 mr-1 text-neutral-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors shrink-0"
          title="Kembali"
        >
          <ArrowLeft size={13} />
        </button>
      )}
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
