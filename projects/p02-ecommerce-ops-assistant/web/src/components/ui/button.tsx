import { cn } from "@/lib/cn";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "link";
export type ButtonSize = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition select-none disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-4";

const variants: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-500 text-white hover:bg-brand-600 active:bg-brand-700 focus-visible:ring-brand-500/20 shadow-sm",
  secondary:
    "bg-surface text-ink-1 border border-line hover:bg-fill-2 active:bg-fill-3 focus-visible:ring-brand-500/20",
  ghost:
    "bg-transparent text-ink-1 hover:bg-fill-2 active:bg-fill-3 focus-visible:ring-brand-500/20",
  danger:
    "bg-danger text-white hover:opacity-90 active:opacity-80 focus-visible:ring-danger/20",
  link: "bg-transparent text-brand-500 hover:underline px-0 focus-visible:ring-brand-500/20",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-9 px-3.5 text-sm",
  lg: "h-11 px-4 text-sm",
};

/** 生成按钮 className，供 <Link>/<button> 复用，保证全站按钮外观一致。 */
export function buttonVariants(opts: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
} = {}): string {
  const { variant = "primary", size = "md", className } = opts;
  return cn(base, variants[variant], sizes[size], className);
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  return (
    <button className={buttonVariants({ variant, size, className })} {...props} />
  );
}
