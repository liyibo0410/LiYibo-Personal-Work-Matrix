"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * 工作台区错误边界：捕获渲染/数据异常，给出可读提示与重试入口。
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-center px-5 py-20 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-bg text-danger">
        <AlertTriangle className="h-6 w-6" aria-hidden="true" />
      </div>
      <h2 className="mt-4 text-lg font-medium text-ink-1">页面加载出错</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-ink-2">
        请求未能完成。可以重试；若持续失败，请检查后端服务与登录态是否正常。
      </p>
      {error.digest ? (
        <p className="mt-2 text-xs text-ink-3">错误标识：{error.digest}</p>
      ) : null}
      <div className="mt-6">
        <Button variant="primary" onClick={reset}>
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          重试
        </Button>
      </div>
    </div>
  );
}
