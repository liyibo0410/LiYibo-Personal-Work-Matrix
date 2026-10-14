import { Trash2 } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

/**
 * 删除商品入口：跳到服务端渲染的确认页，而不是用 window.confirm。
 * 统一外壳把模块挂在 sandbox iframe 里，没有 allow-modals 时 window.confirm() 直接返回 false，
 * 依赖它的「取消即中止」写法会让删除按钮看起来完全没反应。
 */
export function ProductDeleteButton({
  productId,
  productName,
  compact = false,
}: {
  productId: number;
  productName: string;
  compact?: boolean;
}) {
  const label = `删除商品 ${productName}`;

  return (
    <Link
      href={`/products/${productId}/delete`}
      aria-label={compact ? label : undefined}
      title={compact ? label : undefined}
      className={buttonVariants({
        variant: "danger",
        size: "sm",
        className: compact ? "w-8 px-0" : undefined,
      })}
    >
      <Trash2 className="h-4 w-4" aria-hidden="true" />
      {compact ? null : "删除商品"}
    </Link>
  );
}
