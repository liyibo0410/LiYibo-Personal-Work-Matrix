"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Download,
  LayoutDashboard,
  Package,
  Settings,
  Sparkles,
  Store,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/cn";
import { buttonVariants } from "@/components/ui/button";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** 是否精确匹配（用于首页 "/"，避免 /products 也被高亮） */
  exact?: boolean;
};

const navItems: NavItem[] = [
  { href: "/", label: "工作台", icon: LayoutDashboard, exact: true },
  { href: "/stores", label: "店铺", icon: Store },
  { href: "/products", label: "商品", icon: Package },
  { href: "/agent", label: "Agent 中心", icon: Bot },
  { href: "/imports", label: "数据导入", icon: Download },
  { href: "/settings", label: "模型配置", icon: Settings },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-500 text-white">
        <Sparkles className="h-4 w-4" aria-hidden="true" />
      </div>
      {!compact ? (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink-1">
            电商运营助手
          </p>
          <p className="truncate text-xs text-ink-3">AI 单品运营工作台</p>
        </div>
      ) : null}
    </div>
  );
}

/** 深色应用外壳：左侧固定导航 Sider + 顶部用户栏 + 内容区。 */
export function AppShell({
  user,
  children,
}: {
  user: { display_name: string } | null;
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-fill-1">
      {/* 左侧导航（lg 及以上显示） */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-16 items-center border-b border-line px-5">
          <Brand />
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {navItems.map((item) => {
            const active = isActive(pathname, item);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition",
                  active
                    ? "bg-brand-50 text-brand-600"
                    : "text-ink-2 hover:bg-fill-2 hover:text-ink-1"
                )}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-line px-5 py-3 text-xs text-ink-3">
          v0.1.0 · AI 运营工作台
        </div>
      </aside>

      {/* 内容列 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-line bg-surface/80 px-5 backdrop-blur">
          <div className="lg:hidden">
            <Brand compact />
          </div>
          <div className="ml-auto flex items-center gap-2">
            {user ? (
              <span className="inline-flex h-9 items-center rounded-lg border border-line bg-fill-2 px-3 text-sm text-ink-2">
                {user.display_name}
              </span>
            ) : null}
            <Link
              href="/settings"
              className={buttonVariants({ variant: "secondary", size: "sm" })}
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
              模型配置
            </Link>
            {user ? (
              <form action="/logout" method="post">
                <button
                  type="submit"
                  className={buttonVariants({ variant: "secondary", size: "sm" })}
                >
                  退出
                </button>
              </form>
            ) : (
              <Link
                href="/login"
                className={buttonVariants({ variant: "secondary", size: "sm" })}
              >
                登录
              </Link>
            )}
          </div>
        </header>

        <main className="flex-1 p-5 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
