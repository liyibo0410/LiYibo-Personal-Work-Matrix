import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { ProductDeleteButton } from "@/components/product-delete-button";
import { buttonVariants } from "@/components/ui/button";
import { Tag } from "@/components/ui/tag";
import type { Platform, Product, Store } from "@/types";
import { platformLabels } from "@/components/store-summary-card";

export function ProductRow({
  product,
  store,
  canDelete = false,
}: {
  product: Product;
  store: Store | null | undefined;
  canDelete?: boolean;
}) {
  return (
    <div className="grid gap-3 px-4 py-4 text-sm lg:min-h-16 lg:grid-cols-[1.3fr_0.9fr_0.8fr_0.7fr_1fr_144px] lg:items-center lg:gap-0 lg:py-3">
      <div>
        <p className="font-medium text-ink-1">{product.name}</p>
        <p className="mt-1 text-xs text-ink-3">{product.category ?? "未分类"}</p>
      </div>
      <span className="text-ink-2">{store?.name ?? "未绑定"}</span>
      <span className="text-ink-2">{platformLabels[product.platform as Platform]}</span>
      <span className="font-medium text-ink-1">
        {product.price ? `¥${product.price}` : "-"}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {product.selling_points.slice(0, 3).map((point) => (
          <Tag key={point} tone="green">
            {point}
          </Tag>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <Link
          href={`/products/${product.id}`}
          className={buttonVariants({ variant: "secondary", size: "sm", className: "w-24" })}
        >
          进入
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
        {canDelete ? (
          <ProductDeleteButton productId={product.id} productName={product.name} compact />
        ) : null}
      </div>
    </div>
  );
}
