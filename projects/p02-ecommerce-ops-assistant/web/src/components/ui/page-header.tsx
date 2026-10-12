import { cn } from "@/lib/cn";

/** 页面级标题：标题 + 描述 + 右侧操作区，统一下边距与排版。 */
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "flex flex-col gap-3 border-b border-line pb-4 lg:flex-row lg:items-end lg:justify-between",
        className
      )}
    >
      <div className="min-w-0">
        <h1 className="text-xl font-semibold text-ink-1 sm:text-2xl">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 text-sm text-ink-3">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}
