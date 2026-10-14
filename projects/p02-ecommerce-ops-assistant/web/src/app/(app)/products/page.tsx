import { ArrowRight, Boxes, Package, Plus, Search } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { Tag } from "@/components/ui/tag";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { ProductRow } from "@/components/product-row";
import { platformLabels } from "@/components/store-summary-card";
import { getCurrentUser, getProducts, getStores } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { canEdit as canEditFn } from "@/lib/permissions";
import type { Platform, Product, Store } from "@/types";
import { cn } from "@/lib/cn";

const PAGE_SIZE = 20;

type ProductsPageProps = {
  searchParams?: Promise<{
    store?: string;
    platform?: string;
    q?: string;
    page?: string;
    product?: string;
  }>;
};

export default async function ProductsPage({ searchParams }: ProductsPageProps) {
  const query = searchParams ? await searchParams : {};
  const [products, stores, token] = await Promise.all([
    getProducts(),
    getStores(),
    getAuthToken(),
  ]);
  const currentUser = token ? await getCurrentUser(token) : null;
  const editable = canEditFn(currentUser);

  const filterStoreId = parseStoreId(query.store);
  const filterPlatform = parsePlatform(query.platform);
  const searchQuery = (query.q ?? "").trim().toLowerCase();
  const currentPage = parsePage(query.page);

  const storeById = new Map(stores.map((s) => [s.id, s]));

  const filtered = products.filter((product) => {
    if (filterStoreId !== null && product.store_id !== filterStoreId) return false;
    if (filterPlatform !== "all" && product.platform !== filterPlatform) return false;
    if (searchQuery) {
      const haystack = `${product.name} ${product.category ?? ""} ${(product.selling_points ?? []).join(" ")}`.toLowerCase();
      if (!haystack.includes(searchQuery)) return false;
    }
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const paged = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const unboundCount = products.filter((p) => p.store_id === null).length;
  const categoryCount = new Set(products.map((p) => p.category).filter(Boolean)).size;

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-6">
      <PageHeader
        title="商品池"
        description="围绕每个商品打通诊断、创意、素材、投放与复盘的全链路运营"
        actions={
          <div className="grid grid-cols-3 gap-3">
            <MetricPill label="商品总数" value={products.length} />
            <MetricPill label="店铺绑定" value={products.length - unboundCount} />
            <MetricPill label="类目" value={categoryCount} />
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
              placeholder="搜索商品名称、类目、卖点…"
              className="h-10 w-full rounded-lg border border-line bg-surface pl-9 pr-3 text-sm text-ink-1 outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
            />
          </form>
          <div className="flex flex-wrap gap-2">
            <StoreFilter stores={stores} selectedStoreId={filterStoreId} filterPlatform={filterPlatform} searchQuery={searchQuery} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <PlatformFilter filterPlatform={filterPlatform} filterStoreId={filterStoreId} searchQuery={searchQuery} />
          {searchQuery || filterStoreId !== null || filterPlatform !== "all" ? (
            <Link
              href="/products"
              className="inline-flex h-7 items-center rounded-lg border border-line bg-surface px-2.5 text-xs text-ink-2 hover:bg-fill-2"
            >
              清除全部筛选
            </Link>
          ) : null}
          <span className="ml-auto text-xs text-ink-3">
            {filtered.length} / {products.length} 件商品
          </span>
        </div>
      </Card>

      {query.product === "deleted" ? (
        <p className="text-xs font-medium text-success">
          商品已删除，关联的诊断、创意、素材、投放与库存数据已一并清除。
        </p>
      ) : null}
      {query.product === "delete_failed" ? (
        <p className="text-xs font-medium text-danger">
          商品删除失败，请确认当前账号有编辑权限或稍后重试。
        </p>
      ) : null}

      {unboundCount > 0 ? (
        <div className="rounded-lg border border-warning/30 bg-warning-bg px-4 py-3">
          <div className="flex items-center gap-3">
            <Package className="h-4 w-4 text-warning" aria-hidden="true" />
            <p className="text-sm text-warning">
              {unboundCount} 个商品未绑定店铺，建议先归属店铺再进入运营流程。
            </p>
            <Link
              href={`/?store=`}
              className="ml-auto text-xs font-medium text-warning underline hover:no-underline"
            >
              去工作台处理
            </Link>
          </div>
        </div>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Boxes className="h-6 w-6" />}
          title={products.length === 0 ? "还没有商品" : "当前筛选下没有匹配商品"}
          description={
            products.length === 0
              ? "先在工作台创建第一个商品，或从导入中心批量导入。"
              : "可以切换店铺、平台筛选或清除搜索关键词。"
          }
          action={
            editable && products.length === 0 ? (
              <Link href="/" className={buttonVariants({ variant: "primary" })}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                创建商品
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <Card className="overflow-hidden p-0">
            <div className="hidden grid-cols-[1.3fr_0.9fr_0.8fr_0.7fr_1fr_144px] bg-fill-2 px-4 py-3 text-xs font-semibold text-ink-3 lg:grid">
              <span>商品</span>
              <span>店铺</span>
              <span>平台</span>
              <span>售价</span>
              <span>卖点</span>
              <span>动作</span>
            </div>
            <div className="divide-y divide-line">
              {paged.map((product) => (
                <ProductRow
                  key={product.id}
                  product={product}
                  store={product.store_id ? storeById.get(product.store_id) : null}
                  canDelete={editable}
                />
              ))}
            </div>
          </Card>

          {totalPages > 1 ? (
            <Pagination
              currentPage={safePage}
              totalPages={totalPages}
              filterStoreId={filterStoreId}
              filterPlatform={filterPlatform}
              searchQuery={searchQuery}
            />
          ) : null}
        </>
      )}
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <p className="text-xs text-ink-3">{label}</p>
      <p className="mt-1 text-xl font-semibold text-ink-1">{value}</p>
    </div>
  );
}

function StoreFilter({
  stores,
  selectedStoreId,
  filterPlatform,
  searchQuery,
}: {
  stores: Store[];
  selectedStoreId: number | null;
  filterPlatform: "all" | Platform;
  searchQuery: string;
}) {
  return (
    <>
      <Link
        href={buildHref({ storeId: null, platform: filterPlatform, q: searchQuery, page: 1 })}
        className={cn(
          "inline-flex h-8 items-center rounded-lg border px-2.5 text-xs font-medium transition",
          selectedStoreId === null
            ? "border-brand-700 bg-brand-600 text-white"
            : "border-line bg-surface text-ink-2 hover:bg-fill-2"
        )}
      >
        全部店铺
      </Link>
      {stores.map((store) => (
        <Link
          key={store.id}
          href={buildHref({ storeId: store.id, platform: filterPlatform, q: searchQuery, page: 1 })}
          className={cn(
            "inline-flex h-8 items-center rounded-lg border px-2.5 text-xs font-medium transition",
            selectedStoreId === store.id
              ? "border-brand-700 bg-brand-600 text-white"
              : "border-line bg-surface text-ink-2 hover:bg-fill-2"
          )}
        >
          {store.name}
        </Link>
      ))}
    </>
  );
}

function PlatformFilter({
  filterPlatform,
  filterStoreId,
  searchQuery,
}: {
  filterPlatform: "all" | Platform;
  filterStoreId: number | null;
  searchQuery: string;
}) {
  const platforms: Array<{ value: "all" | Platform; label: string }> = [
    { value: "all", label: "全部平台" },
    { value: "douyin", label: "抖音" },
    { value: "taobao", label: "淘宝" },
    { value: "tmall", label: "天猫" },
    { value: "pinduoduo", label: "拼多多" },
    { value: "jd", label: "京东" },
    { value: "tiktok_shop", label: "TikTok" },
    { value: "amazon", label: "Amazon" },
  ];

  return (
    <>
      {platforms.map((p) => (
        <Link
          key={p.value}
          href={buildHref({ storeId: filterStoreId, platform: p.value, q: searchQuery, page: 1 })}
          className={cn(
            "inline-flex h-7 items-center rounded-lg border px-2.5 text-xs font-medium transition",
            filterPlatform === p.value
              ? "border-brand-700 bg-brand-600 text-white"
              : "border-line bg-surface text-ink-2 hover:bg-fill-2"
          )}
        >
          {p.label}
        </Link>
      ))}
    </>
  );
}

function Pagination({
  currentPage,
  totalPages,
  filterStoreId,
  filterPlatform,
  searchQuery,
}: {
  currentPage: number;
  totalPages: number;
  filterStoreId: number | null;
  filterPlatform: "all" | Platform;
  searchQuery: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3">
      {currentPage <= 1 ? (
        <span className="text-xs text-ink-3">上一页</span>
      ) : (
        <Link
          href={buildHref({ storeId: filterStoreId, platform: filterPlatform, q: searchQuery, page: currentPage - 1 })}
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
          href={buildHref({ storeId: filterStoreId, platform: filterPlatform, q: searchQuery, page: currentPage + 1 })}
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
  storeId: number | null;
  platform: "all" | Platform;
  q: string;
  page: number;
}): string {
  const params = new URLSearchParams();
  if (opts.storeId !== null) params.set("store", String(opts.storeId));
  if (opts.platform !== "all") params.set("platform", opts.platform);
  if (opts.q) params.set("q", opts.q);
  if (opts.page > 1) params.set("page", String(opts.page));
  const qs = params.toString();
  return qs ? `/products?${qs}` : "/products";
}

function parseStoreId(value: string | undefined): number | null {
  if (!value) return null;
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
}

function parsePlatform(value: string | undefined): "all" | Platform {
  if (!value || value === "all") return "all";
  return Object.hasOwn(platformLabels, value) ? (value as Platform) : "all";
}

function parsePage(value: string | undefined): number {
  if (!value) return 1;
  const page = Number(value);
  return Number.isInteger(page) && page > 0 ? page : 1;
}
