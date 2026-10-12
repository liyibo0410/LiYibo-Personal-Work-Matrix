import {
  Boxes,
  Building2,
  ClipboardList,
  Database,
  Download,
  FileText,
  ImageIcon,
  Megaphone,
  Package,
} from "lucide-react";
import Link from "next/link";

import { getCurrentUser, getProducts, getStores } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { canEdit as canEditFn } from "@/lib/permissions";
import { ProductCreateForm } from "@/components/product-create-form";
import { StoreCreateForm } from "@/components/store-create-form";
import { StoreSummaryCard } from "@/components/store-summary-card";
import { ProductRow } from "@/components/product-row";
import { DashboardCharts, type NameValue } from "@/components/charts/dashboard-charts";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Tag } from "@/components/ui/tag";
import { cn } from "@/lib/cn";
import type { Platform, Product, Store } from "@/types";
import { platformLabels } from "@/components/store-summary-card";

const platformFilters: Array<{ value: "all" | Platform; label: string }> = [
  { value: "all", label: "全部平台" },
  { value: "douyin", label: "抖音" },
  { value: "taobao", label: "淘宝" },
  { value: "tmall", label: "天猫" },
  { value: "pinduoduo", label: "拼多多" },
  { value: "jd", label: "京东" },
];

const workflow = [
  { title: "建店建档", icon: Building2, tone: "bg-brand-50 text-brand-600", href: "/" },
  { title: "导入数据", icon: ClipboardList, tone: "bg-brand-50 text-brand-600", href: "/imports" },
  { title: "补商品信息", icon: ImageIcon, tone: "bg-success-bg text-success", href: "/?workflow=product" },
  { title: "投放建议", icon: Megaphone, tone: "bg-warning-bg text-warning", href: "/?workflow=ads" },
  { title: "周期复盘", icon: FileText, tone: "bg-danger-bg text-danger", href: "/?workflow=review" },
];

type HomeProps = {
  searchParams?: Promise<{ platform?: string; store?: string; demo?: string }>;
};

/** 渲染首页（工作台）；服务端聚合商品、店铺与当前用户权限，交互交给表单或客户端组件。 */
export default async function Home({ searchParams }: HomeProps) {
  const query = searchParams ? await searchParams : {};
  const selectedPlatform = parsePlatform(query.platform);
  const selectedStoreId = parseStoreId(query.store);
  const [products, stores, token] = await Promise.all([
    getProducts(),
    getStores(),
    getAuthToken(),
  ]);
  const currentUser = token ? await getCurrentUser(token) : null;
  const canEdit = canEditFn(currentUser);

  const storeById = new Map(stores.map((store) => [store.id, store]));
  const productsByStore = countProductsByStore(products);
  const activeStores = stores.filter((store) => store.status === "active").length;
  const platformCount = new Set([
    ...stores.map((store) => store.platform),
    ...products.map((product) => product.platform),
  ]).size;
  const unboundProducts = products.filter(
    (product) => product.store_id === null
  ).length;
  const workflowItems = buildHomeWorkflow(products, stores, unboundProducts);

  // 图表聚合：平台商品分布、店铺状态、各店铺商品数、类目分布。
  const productsByPlatform = buildPlatformDistribution(products);
  const storeStatusDistribution = buildStoreStatusDistribution(stores);
  const storeProductTop = buildStoreProductTop(stores, productsByStore);
  const categoryDistribution = buildCategoryDistribution(products);
  const filteredProducts = products.filter((product) => {
    if (selectedPlatform !== "all" && product.platform !== selectedPlatform) {
      return false;
    }
    if (selectedStoreId !== null && product.store_id !== selectedStoreId) {
      return false;
    }
    return true;
  });

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-6">
      <PageHeader
        title="多平台店铺运营工作台"
        description="围绕单品打通诊断、创意、素材、投放与复盘的全链路运营"
        actions={
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MetricCard label="店铺" value={stores.length} />
            <MetricCard label="活跃店铺" value={activeStores} />
            <MetricCard label="商品" value={products.length} />
            <MetricCard label="平台" value={platformCount} />
          </div>
        }
      />

      <Card className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-ink-1">演示和导入</h2>
          <p className="mt-1 text-sm text-ink-3">
            用演示数据快速跑通店铺、库存、投放实验和复盘链路，或下载绩效数据导入模板。
          </p>
            {query.demo === "created" ? (
              <p className="mt-2 text-xs font-medium text-success">演示数据已准备好。</p>
            ) : null}
            {query.demo === "failed" ? (
              <p className="mt-2 text-xs font-medium text-danger">
                演示数据创建失败，请确认当前账号有编辑权限。
              </p>
            ) : null}
            {query.store === "deleted" ? (
              <p className="mt-2 text-xs font-medium text-success">店铺已删除。</p>
            ) : null}
            {query.store === "delete_failed" ? (
              <p className="mt-2 text-xs font-medium text-danger">
                店铺删除失败，请确认当前账号有编辑权限或稍后重试。
              </p>
            ) : null}
            {!canEdit ? (
            <p className="mt-2 text-xs font-medium text-warning">
              当前账号为只读权限，只能查看数据，不能创建或导入。
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {canEdit ? (
            <form action="/workspace/demo-data" method="post">
              <button
                type="submit"
                className={buttonVariants({ variant: "primary" })}
              >
                <Database className="h-4 w-4" aria-hidden="true" />
                生成演示数据
              </button>
            </form>
          ) : null}
          <Link
            href="/workspace/templates/performance-records"
            className={buttonVariants({ variant: "secondary" })}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            下载导入模板
          </Link>
          {canEdit ? (
            <Link href="/imports" className={buttonVariants({ variant: "secondary" })}>
              <Package className="h-4 w-4" aria-hidden="true" />
              导入中心
            </Link>
          ) : null}
        </div>
      </Card>

      <DashboardCharts
        productsByPlatform={productsByPlatform}
        storeStatus={storeStatusDistribution}
        storeProductCounts={storeProductTop}
        categoryCounts={categoryDistribution}
      />

      <section
        className={cn("grid gap-6", canEdit ? "xl:grid-cols-[360px_1fr]" : "")}
      >
        {canEdit ? (
          <div className="flex flex-col gap-6">
            <Card className="p-5">
              <StoreCreateForm />
            </Card>
            <Card className="p-5">
              <ProductCreateForm stores={stores} />
            </Card>
          </div>
        ) : null}

        <div className="flex flex-col gap-6">
          <Card className="p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-ink-1">店铺视图</h2>
                <p className="mt-1 text-sm text-ink-3">
                  按平台和店铺归拢商品，先把多平台运营入口铺出来
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {platformFilters.map((platform) => (
                  <Link
                    key={platform.value}
                    href={
                      platform.value === "all"
                        ? "/"
                        : `/?platform=${platform.value}`
                    }
                    className={buttonVariants({
                      variant:
                        selectedPlatform === platform.value ? "primary" : "secondary",
                      size: "sm",
                    })}
                  >
                    {platform.label}
                  </Link>
                ))}
              </div>
            </div>

            <div className="mt-5 grid gap-3 lg:grid-cols-2">
              {stores.length === 0 ? (
                <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm text-ink-3">
                  还没有店铺，先在左侧创建一个平台店铺。
                </div>
              ) : (
                stores.map((store) => (
                  <StoreSummaryCard
                    key={store.id}
                    store={store}
                    productCount={productsByStore.get(store.id) ?? 0}
                    selected={store.id === selectedStoreId}
                    canDelete={canEdit}
                  />
                ))
              )}
              {unboundProducts > 0 ? (
                <div className="rounded-lg border border-warning/30 bg-warning-bg px-4 py-4">
                  <div className="flex items-center gap-3">
                    <Package className="h-5 w-5 text-warning" aria-hidden="true" />
                    <div>
                      <p className="text-sm font-semibold text-ink-1">
                        未绑定店铺商品
                      </p>
                      <p className="mt-1 text-xs text-warning">
                        {unboundProducts} 个商品需要补店铺归属
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-ink-1">商品池</h2>
                <p className="mt-1 text-sm text-ink-3">
                  围绕每个商品补竞品、出素材、做投放实验和复盘
                </p>
              </div>
              <Tag tone="neutral">
                <Boxes className="h-3.5 w-3.5" aria-hidden="true" />
                {filteredProducts.length} / {products.length}
              </Tag>
            </div>

            <div className="mt-5 overflow-hidden rounded-lg border border-line">
              <div className="hidden grid-cols-[1.3fr_0.9fr_0.8fr_0.7fr_1fr_96px] bg-fill-2 px-4 py-3 text-xs font-semibold text-ink-3 lg:grid">
                <span>商品</span>
                <span>店铺</span>
                <span>平台</span>
                <span>售价</span>
                <span>卖点</span>
                <span>动作</span>
              </div>

              {filteredProducts.length === 0 ? (
                <div className="px-4 py-12 text-center text-sm text-ink-3">
                  当前筛选下没有商品，可以新建商品或切换平台。
                </div>
              ) : (
                <div className="divide-y divide-line">
                  {filteredProducts.map((product) => (
                    <ProductRow
                      key={product.id}
                      product={product}
                      store={
                        product.store_id ? storeById.get(product.store_id) : null
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-5">
        {workflow.map((item) => {
          const Icon = item.icon;
          const workflowItem = workflowItems.get(item.title);
          return (
            <Link
              key={item.title}
              href={workflowItem?.href ?? item.href}
              className="group rounded-lg border border-line bg-surface p-4 shadow-card transition hover:border-brand-500/30 hover:bg-brand-50/40"
            >
              <div className="flex items-start justify-between gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-lg",
                    item.tone
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <Tag tone="neutral">{workflowItem?.count ?? 0}</Tag>
              </div>
              <h3 className="mt-4 text-sm font-semibold text-ink-1">
                {item.title}
              </h3>
              <p className="mt-1 text-xs leading-5 text-ink-3">
                {workflowItem?.hint ?? "查看下一步"}
              </p>
            </Link>
          );
        })}
      </section>
    </div>
  );
}

/** 按平台聚合商品数量（用于平台分布环形图）。 */
function buildPlatformDistribution(products: Product[]): NameValue[] {
  const counts = new Map<Platform, number>();
  for (const product of products) {
    counts.set(
      product.platform,
      (counts.get(product.platform) ?? 0) + 1
    );
  }
  return [...counts.entries()]
    .map(([key, value]) => ({ name: platformLabels[key] ?? key, value }))
    .sort((a, b) => b.value - a.value);
}

/** 按状态聚合店铺数量（启用 / 暂停 / 关闭）。 */
function buildStoreStatusDistribution(stores: Store[]): NameValue[] {
  const order: Store["status"][] = ["active", "paused", "closed"];
  const labels: Record<Store["status"], string> = {
    active: "启用",
    paused: "暂停",
    closed: "关闭",
  };
  const counts: Record<Store["status"], number> = {
    active: 0,
    paused: 0,
    closed: 0,
  };
  for (const store of stores) {
    counts[store.status] = (counts[store.status] ?? 0) + 1;
  }
  return order.map((status) => ({ name: labels[status], value: counts[status] }));
}

/** 各店铺商品数 Top（横向柱状图数据）。 */
function buildStoreProductTop(
  stores: Store[],
  byStore: Map<number, number>
): NameValue[] {
  return stores
    .map((store) => ({ name: store.name, value: byStore.get(store.id) ?? 0 }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

/** 按类目聚合商品数量（柱状图数据），忽略空类目。 */
function buildCategoryDistribution(products: Product[]): NameValue[] {
  const counts = new Map<string, number>();
  for (const product of products) {
    const category = product.category?.trim();
    if (!category) continue;
    counts.set(category, (counts.get(category) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
}

/** 构建首页工作流提示，仅用已有数据推导下一步，不在渲染阶段修改源数据。 */
function buildHomeWorkflow(
  products: Product[],
  stores: Store[],
  unboundProducts: number
): Map<string, { count: number; hint: string; href: string }> {
  const missingSellingPoints = products.filter(
    (product) => product.selling_points.length === 0
  ).length;
  const missingPlatformIds = products.filter(
    (product) => !product.external_product_id
  ).length;
  const productsReadyForOps = products.filter(
    (product) => product.store_id !== null && product.selling_points.length > 0
  ).length;

  return new Map([
    [
      "建店建档",
      {
        count: stores.length + products.length,
        hint: unboundProducts > 0 ? `${unboundProducts} 个商品待绑定店铺` : "店铺和商品入口",
        href: "/",
      },
    ],
    [
      "导入数据",
      {
        count: missingPlatformIds,
        hint: missingPlatformIds > 0 ? `${missingPlatformIds} 个商品待补平台 ID` : "导入商品/SKU/经营数据",
        href: "/imports",
      },
    ],
    [
      "补商品信息",
      {
        count: missingSellingPoints,
        hint: missingSellingPoints > 0 ? `${missingSellingPoints} 个商品待补卖点` : "进入单品运营闭环",
        href: firstProductHref(products, "overview"),
      },
    ],
    [
      "投放建议",
      {
        count: productsReadyForOps,
        hint: productsReadyForOps > 0 ? "从素材和链接生成投放建议" : "先补商品基础信息",
        href: firstProductHref(products, "ads"),
      },
    ],
    [
      "周期复盘",
      {
        count: products.length,
        hint: products.length > 0 ? "回填经营数据后生成复盘" : "先创建商品",
        href: firstProductHref(products, "review"),
      },
    ],
  ]);
}

function firstProductHref(products: Product[], tab: string): string {
  return products[0] ? `/products/${products[0].id}?tab=${tab}` : "/";
}

function MetricCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3">
      <p className="text-xs text-ink-3">{label}</p>
      <p className="mt-1 text-xl font-semibold text-ink-1">{value}</p>
    </div>
  );
}

function countProductsByStore(products: Product[]): Map<number, number> {
  return products.reduce((counts, product) => {
    if (product.store_id !== null) {
      counts.set(product.store_id, (counts.get(product.store_id) ?? 0) + 1);
    }
    return counts;
  }, new Map<number, number>());
}

function parsePlatform(value: string | undefined): "all" | Platform {
  if (!value || value === "all") {
    return "all";
  }
  return Object.hasOwn(platformLabels, value) ? (value as Platform) : "all";
}

function parseStoreId(value: string | undefined): number | null {
  if (!value) {
    return null;
  }
  const storeId = Number(value);
  return Number.isInteger(storeId) && storeId > 0 ? storeId : null;
}
