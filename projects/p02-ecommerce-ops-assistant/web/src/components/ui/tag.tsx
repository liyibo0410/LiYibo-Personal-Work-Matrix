import { cn } from "@/lib/cn";

export type TagTone = "neutral" | "blue" | "green" | "amber" | "red" | "purple";

const tones: Record<TagTone, string> = {
  neutral: "bg-fill-2 text-ink-2 border border-line",
  blue: "bg-brand-50 text-brand-600",
  green: "bg-success-bg text-success",
  amber: "bg-warning-bg text-warning",
  red: "bg-danger-bg text-danger",
  purple: "bg-brand-50 text-brand-700",
};

/** 状态标签：柔和底色 + 同色文字，用于状态/分类/计数。 */
export function Tag({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: TagTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
