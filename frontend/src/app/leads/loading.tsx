export default function LeadsLoading() {
  return (
    <div className="max-w-6xl space-y-6 animate-pulse">
      <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-48" />
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-card">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4 px-6 py-4 border-b border-[var(--border-subtle)] last:border-0">
            <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" />
            <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
            <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/5" />
            <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3 ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}
