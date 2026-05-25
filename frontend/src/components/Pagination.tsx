"use client";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  itemLabel?: string;
}

export default function Pagination({ page, pageSize, total, onPageChange, itemLabel = "item" }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3 border-t border-[var(--border-subtle)] text-xs">
      <span className="text-neutral-400">
        {start}–{end} dari {total} {itemLabel}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          className="px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-neutral-800 transition"
          title="Halaman pertama"
        >«</button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="px-3 py-1 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-neutral-800 transition"
        >Prev</button>
        <span className="px-3 py-1 text-neutral-500 dark:text-neutral-400">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="px-3 py-1 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-neutral-800 transition"
        >Next</button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          className="px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-neutral-800 transition"
          title="Halaman terakhir"
        >»</button>
      </div>
    </div>
  );
}

export function usePaginated<T>(items: T[], pageSize: number = 20) {
  return {
    paginate: (page: number) => items.slice((page - 1) * pageSize, page * pageSize),
    total: items.length,
    pageSize,
  };
}
