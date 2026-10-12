/**
 * 工作台区加载骨架屏：深色主题灰块占位，避免空白闪烁。
 */
export default function AppLoading() {
  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-6 lg:px-8">
      <div className="animate-pulse space-y-6">
        <div className="h-8 w-48 rounded-lg bg-fill-2" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="rounded-lg border border-line bg-surface p-4 shadow-card"
            >
              <div className="h-3 w-20 rounded bg-fill-2" />
              <div className="mt-3 h-6 w-16 rounded bg-fill-2" />
            </div>
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-64 rounded-lg border border-line bg-surface shadow-card" />
          <div className="h-64 rounded-lg border border-line bg-surface shadow-card" />
        </div>
      </div>
    </div>
  );
}
