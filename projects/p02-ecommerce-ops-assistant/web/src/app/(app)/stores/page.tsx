import { ArrowRight, Plus, Search, Store as StoreIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { Tag } from "@/components/ui/tag";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StoreSummaryCard, platformLabels } from "@/components/store-summary-card";
import { getCurrentUser, getProducts, getStores } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { canEdit as canEditFn } from "@/lib/permissions";
import type { Platform, Store } from "@/types";
import { cn } from "@/lib/cn";

const PAGE_SIZE = 12;

const platformFilters: Array<{ value: "all" | Platform; label: string }> = [
  { value: "all", label: "全部" },
  { value: "douyin", label: "抖音" },
  { value: "taobao", label: "淘宝" },
  { value: "tmall", label: "天猫" },
  { value: "pinduoduo", label: "拼多多" },
  { value: "jd", label: "京东" },
  { value: "tiktok_shop", label: "TikTok" },
  { value: "amazon", label: "Amazon" },
];

const statusFilters: Array<{ value: "all" | Store["status"]; label: string }> = [
  { value: "all", label: "全部状态" },
  { value: "active", label: "启用" },
  { value: "paused", label: "暂停" },
  { value: "closed", label: "关闭" },
];

type StoresPageProps = {
  searchParams?: Promise<{
    platform?: string;
    status?: string;
    q?: string;
    page?: string;
  }>;
};

export default async function StoresPage({ searchParams }: StoresPageProps) {
  const query = searchParams ? await searchParams : {};
  const [stores, products, token] = await Promise.all([
    getStores(),
    getProducts(),
    getAuthToken(),
  ]);
  const currentUser = token ? await getCurrentUser(token) : null;
  const editable = canEditFn(currentUser);

  const filterPlatform = parsePlatform(query.platform);
  const filterStatus = parseStatus(query.status);
  const searchQuery = (query.q ?? "").trim().toLowerCase();
  const currentPage = parsePage(query.page);

  const productCountByStore = countProductsByStore(products);

  const filtered = stores.filter((store) => {
    if (filterPlatform !== "all" && store.platform !== filterPlatform) return false;
    if (filterStatus !== "all" && store.status !== filterStatus) return false;
    if (searchQuery) {
      const haystack = `${store.name} ${store.owner_name ?? ""} ${store.external_store_id ?? ""}`.toLowerCase();
      if (!haystack.includes(searchQuery)) return false;
    }
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const paged = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const activeCount = stores.filter((s) => s.status === "active").length;
  const pausedCount = stores.filter((s) => s.status === "paused").length;

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-6">
      <PageHeader
        title="店铺管理"
        description="按平台与状态归拢所有店铺，进入单店运营闭环"
        actions={
          <div className="grid grid-cols-3 gap-3">
            <MetricPill label="店铺总数" value={stores.length} />
            <MetricPill label="启用" value={activeCount} tone="text-success" />
            <MetricPill label="暂停" value={pausedCount} tone="text-warning" />
          </div>
        }
      />

      <Card className="flex flex-col gap-4 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <form className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden="true" />
            <input
              name="q"
              defaultValue={searchQuery || undefined}
              placeholder="搜索店铺名称、负责人…"
              className="h-10 w-full rounded-lg border border-line bg-surface pl-9 pr-3 text-sm text-ink-1 outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
            />
          </form>
          <div className="flex flex-wrap gap-2">
            {platformFilters.map((f) => (
              <Link
                key={f.value}
                href={buildHref({ platform: f.value, status: filterStatus, q: searchQuery, page: 1 })}
                className={buttonVariants({
                  variant: filterPlatform === f.value ? "primary" : "secondary",
                  size: "sm",
                })}
              >
                {f.label}
              </Link>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {statusFilters.map((f) => (
            <Link
              key={f.value}
              href={buildHref({ platform: filterPlatform, status: f.value, q: searchQuery, page: 1 })}
              className={cn(
                "inline-flex h-7 items-center rounded-lg border px-2.5 text-xs font-medium transition",
                filterStatus === f.value
                  ? "border-brand-700 bg-brand-600 text-white"
                  : "border-line bg-surface text-ink-2 hover:bg-fill-2"
              )}
            >
              {f.label}
            </Link>
          ))}
          {searchQuery ? (
            <Link
              href={buildHref({ platform: filterPlatform, status: filterStatus, q: "", page: 1 })}
              className="inline-flex h-7 items-center rounded-lg border border-line bg-surface px-2.5 text-xs text-ink-2 hover:bg-fill-2"
            >
              清除搜索
            </Link>
          ) : null}
          <span className="ml-auto text-xs text-ink-3">
            {filtered.length} / {stores.length} 家店铺
          </span>
        </div>
      </Card>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<StoreIcon className="h-6 w-6" />}
          title={stores.length === 0 ? "还没有店铺" : "当前筛选下没有匹配店铺"}
          description={
            stores.length === 0
              ? "先在工作台创建一个平台店铺，或从导入中心批量导入。"
              : "可以切换平台、状态筛选或清除搜索关键词。"
          }
          action={
            editable && stores.length === 0 ? (
              <Link href="/" className={buttonVariants({ variant: "primary" })}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                创建店铺
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {paged.map((store) => (
              <StoreSummaryCard
                key={store.id}
                store={store}
                productCount={productCountByStore.get(store.id) ?? 0}
                selected={false}
                canDelete={editable}
              />
            ))}
          </div>

          {totalPages > 1 ? (
            <Pagination currentPage={safePage} totalPages={totalPages} filterPlatform={filterPlatform} filterStatus={filterStatus} searchQuery={searchQuery} />
          ) : null}
        </>
      )}
    </div>
  );
}

function MetricPill({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <p className="text-xs text-ink-3">{label}</p>
      <p className={cn("mt-1 text-xl font-semibold text-ink-1", tone)}>{value}</p>
    </div>
  );
}

function Pagination({
  currentPage,
  totalPages,
  filterPlatform,
  filterStatus,
  searchQuery,
}: {
  currentPage: number;
  totalPages: number;
  filterPlatform: "all" | Platform;
  filterStatus: "all" | Store["status"];
  searchQuery: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3">
      {currentPage <= 1 ? (
        <span className="text-xs text-ink-3">上一页</span>
      ) : (
        <Link
          href={buildHref({ platform: filterPlatform, status: filterStatus, q: searchQuery, page: currentPage - 1 })}
          className="text-xs font-medium text-brand-600 hover:text-brand-700"
        >
          上一页
        </Link>
      )}
      <span className="text-xs text-ink-3">
        第 {currentPage} / {totalPages} 页
      </span>
      {currentPage >= totalPages ? (
        <span className="text-xs text-ink-3">下一页</span>
      ) : (
        <Link
          href={buildHref({ platform: filterPlatform, status: filterStatus, q: searchQuery, page: currentPage + 1 })}
          className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
        >
          下一页
          <ArrowRight className="h-3 w-3" aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}

function buildHref(opts: {
  platform: "all" | Platform;
  status: "all" | Store["status"];
  q: string;
  page: number;
}): string {
  const params = new URLSearchParams();
  if (opts.platform !== "all") params.set("platform", opts.platform);
  if (opts.status !== "all") params.set("status", opts.status);
  if (opts.q) params.set("q", opts.q);
  if (opts.page > 1) params.set("page", String(opts.page));
  const qs = params.toString();
  return qs ? `/stores?${qs}` : "/stores";
}

function countProductsByStore(products: { store_id: number | null }[]): Map<number, number> {
  return products.reduce((counts, product) => {
    if (product.store_id !== null) {
      counts.set(product.store_id, (counts.get(product.store_id) ?? 0) + 1);
    }
    return counts;
  }, new Map<number, number>());
}

function parsePlatform(value: string | undefined): "all" | Platform {
  if (!value || value === "all") return "all";
  return Object.hasOwn(platformLabels, value) ? (value as Platform) : "all";
}

function parseStatus(value: string | undefined): "all" | Store["status"] {
  if (!value || value === "all") return "all";
  const valid: Store["status"][] = ["active", "paused", "closed"];
  return valid.includes(value as Store["status"]) ? (value as Store["status"]) : "all";
}

function parsePage(value: string | undefined): number {
  if (!value) return 1;
  const page = Number(value);
  return Number.isInteger(page) && page > 0 ? page : 1;
}
