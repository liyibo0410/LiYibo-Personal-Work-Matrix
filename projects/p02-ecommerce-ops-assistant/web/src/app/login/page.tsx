import { LockKeyhole } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";

type LoginPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

/** 渲染登录页面；服务端读取错误参数，表单提交到 /login/submit。 */
export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = (await searchParams) ?? {};
  const error = Array.isArray(params.error) ? params.error[0] : params.error;

  return (
    <main className="flex min-h-screen items-center justify-center bg-fill-1 px-5 py-10 text-ink-1">
      <section className="w-full max-w-md rounded-lg border border-line bg-surface p-6 shadow-card">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500 text-white">
            <LockKeyhole className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-medium text-brand-600">
              Ecommerce Operation Assistant
            </p>
            <h1 className="text-xl font-semibold">登录工作台</h1>
          </div>
        </div>

        {error ? (
          <div className="mt-5 rounded-lg border border-danger/30 bg-danger-bg px-3 py-2 text-sm text-danger">
            {error === "backend"
              ? "无法连接后端服务，请确认后端已启动（默认 http://127.0.0.1:8000）。"
              : "邮箱或密码不正确，或者账号已停用。"}
          </div>
        ) : null}

        <form action="/login/submit" method="post" className="mt-6 space-y-4">
          <Field label="邮箱" required>
            <Input
              name="email"
              type="email"
              required
              placeholder="owner@example.com"
            />
          </Field>
          <Field label="密码" required>
            <Input
              name="password"
              type="password"
              required
              placeholder="输入密码"
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
