import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

/**
 * 全局 404：未匹配到任何路由时展示，保持飞书风格并提供返回入口。
 */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-fill-1 px-5 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-fill-2 text-ink-3">
        <FileQuestion className="h-6 w-6" aria-hidden="true" />
      </div>
      <h1 className="mt-4 text-lg font-medium text-ink-1">页面不存在</h1>
      <p className="mt-2 max-w-md text-sm leading-6 text-ink-2">
        你访问的页面已被移除，或链接有误。
      </p>
      <div className="mt-6">
        <Link href="/" className={buttonVariants({ variant: "primary" })}>
          返回工作台
        </Link>
      </div>
    </div>
  );
}
