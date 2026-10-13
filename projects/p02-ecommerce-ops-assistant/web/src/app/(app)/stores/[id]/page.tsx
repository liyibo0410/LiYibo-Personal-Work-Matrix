import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Boxes,
  CheckCircle2,
  ClipboardList,
  Package,
  Store as StoreIcon,
  Warehouse,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { InventoryAdvicePanel } from "@/components/inventory-advice-panel";
import { StoreDeleteButton } from "@/components/store-delete-button";
import { getCurrentUser, getProducts, getStore, getStoreInventoryMovements, getStoreInventorySummary } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { canEdit as canEditFn } from "@/lib/permissions";
import type { StoreInventoryMovementRow, StoreInventoryRow } from "@/types";
import type { Platform, Product } from "@/types";
import { platformLabels } from "@/components/store-summary-card";

type StorePageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{ inventory?: string }>;
};

/** 渲染stores页面；在服务端加载业务数据，并把交互交给对应表单或客户端组件。 */
export default async function StorePage({ params, searchParams }: StorePageProps) {
  const { id } = await params;
  const query = searchParams ? await searchParams : {};
  const [store, products, inventorySummary, inventoryMovements, token] = await Promise.all([
    getStore(id),
    getProducts(),
    getStoreInventorySummary(id),
    getStoreInventoryMovements(id),
    getAuthToken(),
  ]);

  if (!store) {
    notFound();
  }

  const storeProducts = products.filter((product) => product.store_id === store.id);
  const activeProducts = storeProducts.filter((product) => product.platform_status !== "offline").length;
  const unmappedProducts = storeProducts.filter((product) => !product.external_product_id).length;
  const lowStockRows = inventorySummary?.rows.filter((row) => row.is_low_stock) ?? [];
  const inventoryRows = query.inventory === "low" ? lowStockRows : inventorySummary?.rows ?? [];
  const workflowSteps = buildStoreWorkflowSteps(store.id, storeProducts, inventorySummary?.rows ?? [], lowStockRows, unmappedProducts);
  const currentUser = token ? await getCurrentUser(token) : null;
  const canEdit = canEditFn(currentUser);

  return (
    <main className="min-h-screen bg-fill-1 px-5 py-6 text-ink-1 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <div>
          <Link
            href="/"
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-1 hover:bg-fill-1"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            返回工作台
          </Link>
        </div>

        <header className="rounded-lg border border-line bg-surface p-5">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
                <StoreIcon className="h-6 w-6" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium text-brand-600">{platformLabels[store.platform]}</p>
                <h1 className="mt-1 text-2xl font-semibold tracking-normal text-ink-1">{store.name}</h1>
                <p className="mt-2 text-sm text-ink-2">
                  {store.owner_name ? `负责人：${store.owner_name}` : "未设置负责人"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-fit items-center rounded-lg bg-fill-2 px-3 text-xs font-medium text-ink-1">
                {store.status === "active" ? "启用" : store.status === "paused" ? "暂停" : "关闭"}
              </span>
              {canEdit ? (
                <StoreDeleteButton storeId={store.id} storeName={store.name} />
              ) : null}
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-4">
          <MetricCard label="店铺商品" value={storeProducts.length} icon={Package} />
          <MetricCard label="在营商品" value={activeProducts} icon={Boxes} />
          <MetricCard label="待补平台映射" value={unmappedProducts} icon={ArrowRight} />
          <MetricCard label="可用库存" value={inventorySummary?.total_available_quantity ?? 0} icon={Warehouse} />
        </section>

        <StoreWorkflowPanel steps={workflowSteps} />

        {lowStockRows.length > 0 ? (
          <section className="rounded-lg border border-warning-bg bg-warning-bg p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="flex gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-warning-bg text-warning">
                  <AlertTriangle className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-ink-1">库存异常提示</h2>
                  <p className="mt-1 text-sm text-warning">
                    {lowStockRows.length} 个 SKU 可用库存已低于或等于预警线，建议优先补货或调整投放节奏。
                  </p>
                </div>
              </div>
              <Link
                href={`/stores/${store.id}?inventory=low`}
                className="inline-flex h-9 w-fit items-center rounded-lg bg-warning px-3 text-sm font-medium text-white hover:bg-warning"
              >
                只看低库存
              </Link>
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-2">
              {lowStockRows.slice(0, 4).map((row) => (
                <Link
                  key={row.sku_id}
                  href={`/products/${row.product_id}?tab=overview`}
                  className="rounded-lg border border-warning-bg bg-surface px-3 py-2 text-sm hover:bg-warning-bg"
                >
                  <span className="font-medium text-ink-1">{row.product_name}</span>
                  <span className="ml-2 text-ink-1">{row.sku_code}</span>
                  <span className="ml-2 text-warning">可用 {row.available_quantity}</span>
                </Link>
              ))}
            </div>
          </section>
        ) : null}

        <InventoryWorkflowPanel storeId={store.id} inventoryRows={inventorySummary?.rows ?? []} lowStockRows={lowStockRows} />

        <InventoryAdvicePanel storeId={store.id} canEdit={canEdit} />

        <section className="rounded-lg border border-line bg-surface p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">店铺商品</h2>
              <p className="mt-1 text-sm text-ink-2">从店铺维度进入单品运营闭环</p>
            </div>
            <Link
              href={`/?store=${store.id}`}
              className="inline-flex h-9 items-center rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-1 hover:bg-fill-1"
            >
              回首页筛选
            </Link>
          </div>

          <div className="mt-5 overflow-hidden rounded-lg border border-line">
            <div className="hidden grid-cols-[1.4fr_0.8fr_0.8fr_1fr_96px] bg-fill-1 px-4 py-3 text-xs font-semibold text-ink-2 lg:grid">
              <span>商品</span>
              <span>平台状态</span>
              <span>售价</span>
              <span>卖点</span>
              <span>动作</span>
            </div>
            {storeProducts.length === 0 ? (
              <div className="px-4 py-12 text-center text-sm text-ink-2">
                这个店铺还没有绑定商品，可以回到首页创建商品并选择该店铺。
              </div>
            ) : (
              <div className="divide-y divide-line">
                {storeProducts.map((product) => (
                  <StoreProductRow key={product.id} product={product} />
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-surface p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">库存概览</h2>
              <p className="mt-1 text-sm text-ink-2">按 SKU 汇总库存、锁定量、可用量和低库存风险</p>
            </div>
            <span className="inline-flex h-8 items-center rounded-lg bg-fill-2 px-3 text-xs font-medium text-ink-1">
              低库存 {inventorySummary?.low_stock_count ?? 0}
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href={`/stores/${store.id}`}
              className={`inline-flex h-8 items-center rounded-lg border px-3 text-xs font-medium ${
                query.inventory === "low"
                  ? "border-line bg-surface text-ink-1 hover:bg-fill-1"
                  : "border-brand-700 bg-brand-600 text-white"
              }`}
            >
              全部库存
            </Link>
            <Link
              href={`/stores/${store.id}?inventory=low`}
              className={`inline-flex h-8 items-center rounded-lg border px-3 text-xs font-medium ${
                query.inventory === "low"
                  ? "border-brand-700 bg-brand-600 text-white"
                  : "border-line bg-surface text-ink-1 hover:bg-fill-1"
              }`}
            >
              低库存
            </Link>
          </div>

          <div className="mt-5 overflow-hidden rounded-lg border border-line">
            <div className="hidden grid-cols-[1.2fr_0.9fr_0.7fr_0.7fr_0.7fr_0.8fr] bg-fill-1 px-4 py-3 text-xs font-semibold text-ink-2 lg:grid">
              <span>SKU</span>
              <span>商品</span>
              <span>现货</span>
              <span>锁定</span>
              <span>可用</span>
              <span>状态</span>
            </div>
            {!inventorySummary || inventoryRows.length === 0 ? (
              <div className="px-4 py-12 text-center text-sm text-ink-2">
                {query.inventory === "low"
                  ? "当前没有低库存 SKU。"
                  : "这个店铺还没有 SKU 库存数据，后续可从商品详情创建 SKU 并登记库存。"}
              </div>
            ) : (
              <div className="divide-y divide-line">
                {inventoryRows.map((row) => (
                  <InventoryRow key={row.sku_id} row={row} />
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-line bg-surface p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">库存流水</h2>
              <p className="mt-1 text-sm text-ink-2">集中查看店铺最近库存变化</p>
            </div>
            <span className="inline-flex h-8 items-center rounded-lg bg-fill-2 px-3 text-xs font-medium text-ink-1">
              最近 {inventoryMovements.length}
            </span>
          </div>

          <div className="mt-5 overflow-hidden rounded-lg border border-line">
            <div className="hidden grid-cols-[0.8fr_1fr_0.9fr_0.7fr_0.7fr_1fr] bg-fill-1 px-4 py-3 text-xs font-semibold text-ink-2 lg:grid">
              <span>类型</span>
              <span>商品</span>
              <span>SKU</span>
              <span>现货变化</span>
              <span>锁定变化</span>
              <span>原因</span>
            </div>
            {inventoryMovements.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-ink-2">暂无库存流水。</div>
            ) : (
              <div className="divide-y divide-line">
                {inventoryMovements.map((movement) => (
                  <InventoryMovementRow key={movement.id} movement={movement} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

/** 渲染 MetricCard 组件，集中展示指标卡片所需的数据、状态和操作入口。 */
function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-ink-2">{label}</p>
        <Icon className="h-4 w-4 text-ink-3" aria-hidden="true" />
      </div>
      <p className="mt-2 text-xl font-semibold text-ink-1">{value}</p>
    </div>
  );
}

type StoreWorkflowStep = {
  key: string;
  title: string;
  href: string;
  done: boolean;
  hint: string;
};

/** 渲染 StoreWorkflowPanel 组件，集中展示店铺工作流面板所需的数据、状态和操作入口。 */
function StoreWorkflowPanel({ steps }: { steps: StoreWorkflowStep[] }) {
  const nextStep = steps.find((step) => !step.done) ?? steps[steps.length - 1];

  return (
    <section className="rounded-lg border border-line bg-surface p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
            <ClipboardList className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-ink-1">店铺运营流程</h2>
            <p className="mt-1 text-sm text-ink-2">{nextStep.done ? "店铺基础流程已跑通。" : `下一步：${nextStep.title}`}</p>
          </div>
        </div>
        <Link
          href={nextStep.href}
          className="inline-flex h-9 w-fit items-center gap-2 rounded-lg bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700"
        >
          继续处理
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-5">
        {steps.map((step) => (
          <Link
            key={step.key}
            href={step.href}
            className={`rounded-lg border px-3 py-3 transition ${
              step.done ? "border-success-bg bg-success-bg" : "border-line bg-surface hover:bg-fill-1"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-ink-1">{step.title}</p>
              {step.done ? (
                <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />
              ) : (
                <span className="h-2 w-2 rounded-full bg-warning" aria-hidden="true" />
              )}
            </div>
            <p className="mt-2 text-xs leading-5 text-ink-2">{step.hint}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

/** 构建店铺工作流steps，从现有业务数据推导稳定的页面展示模型，不在渲染阶段修改源数据。 */
function buildStoreWorkflowSteps(
  storeId: number,
  products: Product[],
  inventoryRows: StoreInventoryRow[],
  lowStockRows: StoreInventoryRow[],
  unmappedProducts: number,
): StoreWorkflowStep[] {
  return [
    {
      key: "store",
      title: "建店",
      href: `/stores/${storeId}`,
      done: true,
      hint: "店铺档案已创建",
    },
    {
      key: "products",
      title: "商品",
      href: `/?store=${storeId}`,
      done: products.length > 0,
      hint: products.length > 0 ? `${products.length} 个商品已归属店铺` : "创建或导入商品",
    },
    {
      key: "inventory",
      title: "SKU/库存",
      href: `/stores/${storeId}`,
      done: inventoryRows.length > 0,
      hint: inventoryRows.length > 0 ? `${inventoryRows.length} 个 SKU 有库存记录` : "进入商品维护 SKU 和库存",
    },
    {
      key: "mapping",
      title: "数据映射",
      href: "/imports",
      done: products.length > 0 && unmappedProducts === 0,
      hint: unmappedProducts > 0 ? `${unmappedProducts} 个商品待补平台映射` : "导入经营数据或字段映射",
    },
    {
      key: "risk",
      title: "异常处理",
      href: lowStockRows.length > 0 ? `/stores/${storeId}?inventory=low` : `/stores/${storeId}`,
      done: inventoryRows.length > 0 && lowStockRows.length === 0,
      hint: lowStockRows.length > 0 ? `${lowStockRows.length} 个 SKU 低库存` : "库存异常入口",
    },
  ];
}

/** 渲染 InventoryWorkflowPanel 组件，集中展示库存工作流面板所需的数据、状态和操作入口。 */
function InventoryWorkflowPanel({
  storeId,
  inventoryRows,
  lowStockRows,
}: {
  storeId: number;
  inventoryRows: StoreInventoryRow[];
  lowStockRows: StoreInventoryRow[];
}) {
  const hasInventory = inventoryRows.length > 0;
  const hasLowStock = lowStockRows.length > 0;
  const steps = [
    {
      title: "发现低库存",
      done: hasInventory,
      hint: hasLowStock ? `${lowStockRows.length} 个 SKU 需要处理` : "当前无低库存风险",
      href: hasLowStock ? `/stores/${storeId}?inventory=low` : `/stores/${storeId}`,
    },
    {
      title: "分析销量",
      done: false,
      hint: "导入经营数据后判断补货优先级",
      href: "/imports",
    },
    {
      title: "生成建议",
      done: false,
      hint: "使用库存异常 AI/规则建议",
      href: `/stores/${storeId}`,
    },
    {
      title: "人工确认",
      done: !hasLowStock && hasInventory,
      hint: "补货、调拨和投放节奏由人工确认",
      href: `/stores/${storeId}`,
    },
  ];

  return (
    <section className="rounded-lg border border-line bg-surface p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink-1">库存处理流程</h2>
          <p className="mt-1 text-sm text-ink-2">围绕低库存、销量数据、补货建议和人工确认推进</p>
        </div>
        <Link
          href={hasLowStock ? `/stores/${storeId}?inventory=low` : "/imports"}
          className="inline-flex h-9 w-fit items-center gap-2 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-1 hover:bg-fill-1"
        >
          {hasLowStock ? "查看低库存" : "导入经营数据"}
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-4">
        {steps.map((step) => (
          <Link
            key={step.title}
            href={step.href}
            className={`rounded-lg border px-3 py-3 transition ${
              step.done ? "border-success-bg bg-success-bg" : "border-line bg-surface hover:bg-fill-1"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-ink-1">{step.title}</p>
              {step.done ? (
                <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />
              ) : (
                <span className="h-2 w-2 rounded-full bg-warning" aria-hidden="true" />
              )}
            </div>
            <p className="mt-2 text-xs leading-5 text-ink-2">{step.hint}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

/** 渲染 StoreProductRow 组件，集中展示店铺商品行所需的数据、状态和操作入口。 */
function StoreProductRow({ product }: { product: Product }) {
  return (
    <div className="grid gap-3 px-4 py-4 text-sm lg:min-h-16 lg:grid-cols-[1.4fr_0.8fr_0.8fr_1fr_96px] lg:items-center lg:gap-0 lg:py-3">
      <div>
        <p className="font-medium text-ink-1">{product.name}</p>
        <p className="mt-1 text-xs text-ink-2">{product.category ?? "未分类"}</p>
      </div>
      <span className="text-ink-1">{product.platform_status ?? "未同步"}</span>
      <span className="font-medium text-ink-1">{product.price ? `¥${product.price}` : "-"}</span>
      <div className="flex flex-wrap gap-1.5">
        {product.selling_points.slice(0, 3).map((point) => (
          <span key={point} className="rounded-lg bg-success-bg px-2 py-1 text-xs text-success">
            {point}
          </span>
        ))}
      </div>
      <Link
        href={`/products/${product.id}`}
        className="inline-flex h-9 w-24 items-center justify-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-xs font-medium text-ink-1 hover:bg-fill-1"
      >
        进入
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </Link>
    </div>
  );
}

/** 渲染 InventoryRow 组件，集中展示库存行所需的数据、状态和操作入口。 */
function InventoryRow({ row }: { row: StoreInventoryRow }) {
  return (
    <div className="grid gap-3 px-4 py-4 text-sm lg:min-h-16 lg:grid-cols-[1.2fr_0.9fr_0.7fr_0.7fr_0.7fr_0.8fr] lg:items-center lg:gap-0 lg:py-3">
      <div>
        <p className="font-medium text-ink-1">{row.sku_name}</p>
        <p className="mt-1 text-xs text-ink-2">{row.sku_code}</p>
      </div>
      <span className="text-ink-1">{row.product_name}</span>
      <span className="font-medium text-ink-1">{row.quantity}</span>
      <span className="text-ink-1">{row.locked_quantity}</span>
      <span className="font-medium text-ink-1">{row.available_quantity}</span>
      <span
        className={`inline-flex h-7 w-fit items-center rounded-lg px-2 text-xs font-medium ${
          row.is_low_stock ? "bg-warning-bg text-warning" : "bg-success-bg text-success"
        }`}
      >
        {row.is_low_stock ? `低库存 <= ${row.warning_threshold}` : "正常"}
      </span>
    </div>
  );
}

/** 渲染 InventoryMovementRow 组件，集中展示库存流水行所需的数据、状态和操作入口。 */
function InventoryMovementRow({ movement }: { movement: StoreInventoryMovementRow }) {
  return (
    <div className="grid gap-3 px-4 py-3 text-sm lg:min-h-14 lg:grid-cols-[0.8fr_1fr_0.9fr_0.7fr_0.7fr_1fr] lg:items-center lg:gap-0">
      <span className="font-medium text-ink-1">{movementTypeLabel(movement.movement_type)}</span>
      <Link href={`/products/${movement.product_id}?tab=overview`} className="text-brand-700 hover:text-brand-700">
        {movement.product_name}
      </Link>
      <span className="text-ink-1">{movement.sku_code}</span>
      <span className="font-medium text-ink-1">{formatSigned(movement.quantity_delta)}</span>
      <span className="text-ink-1">{formatSigned(movement.locked_delta)}</span>
      <span className="truncate text-ink-1">{movement.reason ?? movement.created_at}</span>
    </div>
  );
}

/** 把流水type状态映射为中文显示文本，保持页面口径一致。 */
function movementTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    inbound: "入库",
    outbound: "出库",
    adjustment: "盘点",
    lock: "锁定",
    release: "释放",
  };
  return labels[type] ?? type;
}

/** 格式化带符号，统一空值、本地化和页面展示规则，避免各组件重复格式化。 */
function formatSigned(value: number): string {
  if (value > 0) {
    return `+${value}`;
  }
  return String(value);
}
