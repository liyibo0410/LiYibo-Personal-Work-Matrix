import { Store as StoreIcon } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { Tag } from "@/components/ui/tag";
import { cn } from "@/lib/cn";
import type { Platform, Store } from "@/types";
import { StoreDeleteButton } from "@/components/store-delete-button";

export const platformLabels: Record<Platform, string> = {
  douyin: "抖音",
  taobao: "淘宝",
  tmall: "天猫",
  pinduoduo: "拼多多",
  jd: "京东",
  tiktok_shop: "TikTok",
  amazon: "Amazon",
  other: "其他",
};

export function StoreSummaryCard({
  store,
  productCount,
  selected,
  canDelete,
}: {
  store: Store;
  productCount: number;
  selected: boolean;
  canDelete?: boolean;
}) {
  const statusTone =
    store.status === "active"
      ? "green"
      : store.status === "paused"
        ? "amber"
        : "neutral";
  const statusLabel =
    store.status === "active"
      ? "启用"
      : store.status === "paused"
        ? "暂停"
        : "关闭";
  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-4 transition",
        selected
          ? "border-brand-500 bg-brand-50/50"
          : "border-line bg-surface hover:bg-fill-2"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-fill-2 text-ink-2">
            <StoreIcon className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-ink-1">
              {store.name}
            </p>
            <p className="mt-1 text-xs text-ink-3">
              {platformLabels[store.platform]}
            </p>
          </div>
        </div>
        <Tag tone={statusTone}>{statusLabel}</Tag>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-ink-3">商品数</p>
          <p className="mt-1 font-semibold text-ink-1">{productCount}</p>
        </div>
        <div>
          <p className="text-xs text-ink-3">负责人</p>
          <p className="mt-1 truncate font-semibold text-ink-1">
            {store.owner_name ?? "-"}
          </p>
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <Link
          href={`/?store=${store.id}`}
          className={buttonVariants({ variant: "secondary", size: "sm" })}
        >
          筛选商品
        </Link>
        <Link
          href={`/stores/${store.id}`}
          className={buttonVariants({ variant: "primary", size: "sm" })}
        >
          店铺详情
        </Link>
        {canDelete ? (
          <StoreDeleteButton storeId={store.id} storeName={store.name} />
        ) : null}
      </div>
    </div>
  );
}
