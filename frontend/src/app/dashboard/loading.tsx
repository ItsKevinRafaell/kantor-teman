export default function DashboardLoading() {
  return (
    <div className="max-w-6xl space-y-6 animate-pulse">
      <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-56" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5">
            <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-20 mb-3" />
            <div className="h-7 bg-gray-100 dark:bg-gray-800 rounded w-32" />
          </div>
        ))}
      </div>
    </div>
  );
}
