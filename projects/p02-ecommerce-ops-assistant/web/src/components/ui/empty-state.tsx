import { cn } from "@/lib/cn";

/** 空状态：图标 + 标题 + 描述 + 可选操作，用于无数据占位。 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-line px-4 py-12 text-center",
        className
      )}
    >
      {icon ? (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-fill-2 text-ink-3">
          {icon}
        </div>
      ) : null}
      <p className="text-sm font-medium text-ink-2">{title}</p>
      {description ? (
        <p className="max-w-sm text-xs text-ink-3">{description}</p>
      ) : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
