import { LockKeyhole } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { readBrandFromDisk } from "@/lib/brand-server";
import { cn } from "@/lib/cn";

type LoginPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

const DEMO_PASSWORD = "Test123456";

/** 四角色演示账号；点击即填充，省掉手输。口令与 bootstrap_demo_users.py 一致。 */
const DEMO_ACCOUNTS = [
  { key: "boss", email: "boss@example.com", role: "老板" },
  { key: "ops", email: "ops@example.com", role: "运营" },
  { key: "design", email: "design@example.com", role: "美工" },
  { key: "cs", email: "cs@example.com", role: "客服" },
] as const;

/** 渲染登录页面；服务端读取错误参数，表单提交到 /login/submit。 */
export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = (await searchParams) ?? {};
  const error = Array.isArray(params.error) ? params.error[0] : params.error;
  const demoKey = Array.isArray(params.demo) ? params.demo[0] : params.demo;
  const picked = DEMO_ACCOUNTS.find((a) => a.key === demoKey);
  // 公司名与 logo 由 shared/config/brand.json 决定（外壳 ⚙ 品牌设置里改），服务端直接读
  const brand = readBrandFromDisk();

  return (
    <main className="flex min-h-screen items-center justify-center bg-fill-1 px-5 py-10 text-ink-1">
      <section className="w-full max-w-md rounded-lg border border-line bg-surface p-6 shadow-card">
        <div className="flex items-center gap-3">
          {brand.logo ? (
            <img
              src={brand.logo}
              alt={`${brand.company} 标识`}
              className="h-10 w-10 shrink-0 rounded-lg object-contain"
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500 text-white">
              <LockKeyhole className="h-5 w-5" aria-hidden="true" />
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-brand-600">
              电商运营助手
            </p>
            <h1 className="text-xl font-semibold">登录工作台</h1>
            <p className="text-xs text-ink-3">{brand.company}</p>
          </div>
        </div>

        {error ? (
          <div className="mt-5 rounded-lg border border-danger/30 bg-danger-bg px-3 py-2 text-sm text-danger">
            {error === "backend"
              ? "无法连接后端服务，请确认后端已启动（默认 http://127.0.0.1:8000）。"
              : "邮箱或密码不正确，或者账号已停用。"}
          </div>
        ) : null}

        <div className="mt-5 rounded-lg border border-brand-500/20 bg-brand-500/5 px-3 py-2.5 text-sm text-ink-2">
          <p className="mb-1.5 font-medium text-ink-1">
            演示账号（密码均为 {DEMO_PASSWORD}）
          </p>
          <p className="mb-2 text-xs text-ink-3">点一下就把账号和密码填进下面的表单</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((account) => (
              <Link
                key={account.key}
                href={{ pathname: "/login", query: { demo: account.key } }}
                scroll={false}
                className={cn(
                  "rounded-lg border px-2.5 py-1.5 text-left text-xs transition",
                  picked?.key === account.key
                    ? "border-brand-500 bg-brand-500/10 text-brand-600"
                    : "border-line bg-surface text-ink-2 hover:border-brand-500/50 hover:text-ink-1"
                )}
              >
                <span className="block font-medium">{account.role}</span>
                <span className="block truncate text-ink-3">{account.email}</span>
              </Link>
            ))}
          </div>
        </div>

        {/* key 绑定所选账号：换演示账号时强制重挂载，否则 defaultValue 只在首次挂载生效，
            点了第二个账号输入框却还是第一个的邮箱。 */}
        <form
          action="/login/submit"
          method="post"
          key={picked?.key ?? "empty"}
          className="mt-6 space-y-4"
        >
          <Field label="邮箱" required>
            <Input
              name="email"
              type="email"
              required
              defaultValue={picked?.email}
              placeholder="boss@example.com"
              autoComplete="username"
            />
          </Field>
          <Field label="密码" required>
            <Input
              name="password"
              type="password"
              required
              defaultValue={picked ? DEMO_PASSWORD : undefined}
              placeholder="输入密码"
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit" size="lg" className="w-full">
            登录
          </Button>
        </form>

        <Link
          href="/"
          className="mt-4 inline-flex text-sm text-ink-3 hover:text-ink-1"
        >
          返回首页
        </Link>
      </section>
    </main>
  );
}
