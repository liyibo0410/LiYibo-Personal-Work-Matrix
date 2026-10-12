import { cn } from "@/lib/cn";
import * as React from "react";

const controlBase =
  "w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 placeholder:text-ink-4 outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-500/20 disabled:bg-fill-2 disabled:text-ink-3";

/** 文本输入：统一飞书焦点环（品牌蓝）与圆角。 */
export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(function Input({ className, ...props }, ref) {
  return (
    <input ref={ref} className={cn(controlBase, "h-11", className)} {...props} />
  );
});

/** 多行输入。 */
export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(controlBase, "min-h-24 resize-y py-2.5", className)}
      {...props}
    />
  );
});

/** 下拉选择。 */
export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className, ...props }, ref) {
  return (
    <select
      ref={ref}
      className={cn(controlBase, "h-11 appearance-none", className)}
      {...props}
    />
  );
});

/** 表单字段容器：标签 + 控件 + 提示，统一间距与必填标记。 */
export function Field({
  label,
  hint,
  required,
  className,
  children,
}: {
  label?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <label className={cn("block", className)}>
      {label ? (
        <span className="text-sm font-medium text-ink-2">
          {label}
          {required ? <span className="text-danger"> *</span> : null}
        </span>
      ) : null}
      <div className="mt-2">{children}</div>
      {hint ? <p className="mt-1.5 text-xs text-ink-3">{hint}</p> : null}
    </label>
  );
}
