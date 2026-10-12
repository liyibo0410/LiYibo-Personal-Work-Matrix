import { Save } from "lucide-react";

import type { ProductDetail } from "@/types";

const platforms = [
  { label: "抖音电商", value: "douyin" },
  { label: "淘宝", value: "taobao" },
  { label: "天猫", value: "tmall" },
  { label: "拼多多", value: "pinduoduo" },
  { label: "京东", value: "jd" },
  { label: "TikTok Shop", value: "tiktok_shop" },
  { label: "Amazon", value: "amazon" },
  { label: "其他", value: "other" },
] as const;

type ProductEditFormProps = {
  canEdit?: boolean;
  product: ProductDetail;
};

/** 渲染 ProductEditForm 组件，集中展示商品编辑表单所需的数据、状态和操作入口。 */
export function ProductEditForm({ canEdit = true, product }: ProductEditFormProps) {
  return (
    <form action={`/products/${product.id}/update`} method="post" className="space-y-4">
      <div>
        <h2 className="text-base font-semibold text-ink-1">商品信息</h2>
        <p className="mt-1 text-sm text-ink-2">调整基础信息后，再重新生成诊断和素材方向</p>
      </div>

      <label className="block">
        <span className="text-sm font-medium text-ink-1">商品名称</span>
        <input
          name="name"
          required
          defaultValue={product.name}
          className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
        />
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-ink-1">平台</span>
          <select
            name="platform"
            defaultValue={product.platform}
            className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
          >
            {platforms.map((platform) => (
              <option key={platform.value} value={platform.value}>
                {platform.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm font-medium text-ink-1">类目</span>
          <input
            name="category"
            defaultValue={product.category ?? ""}
            className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
          />
        </label>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-ink-1">售价</span>
          <input
            name="price"
            inputMode="decimal"
            defaultValue={product.price ?? ""}
            className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-ink-1">成本</span>
          <input
            name="cost"
            inputMode="decimal"
            defaultValue={product.cost ?? ""}
            className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
          />
        </label>
      </div>

      <label className="block">
        <span className="text-sm font-medium text-ink-1">目标人群</span>
        <input
          name="target_audience"
          defaultValue={product.target_audience ?? ""}
          className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
        />
      </label>

      <label className="block">
        <span className="text-sm font-medium text-ink-1">核心卖点</span>
        <textarea
          name="selling_points"
          defaultValue={product.selling_points.join("\n")}
          rows={4}
          className="mt-2 w-full resize-y rounded-lg border border-line bg-surface px-3 py-3 text-sm leading-6 text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
        />
      </label>

      <label className="block">
        <span className="text-sm font-medium text-ink-1">商品链接</span>
        <input
          name="product_url"
          defaultValue={product.product_url ?? ""}
          className="mt-2 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink-1 outline-none transition focus:border-success focus:ring-4 focus:ring-success-bg"
        />
      </label>

      {canEdit ? (
        <button
        type="submit"
        className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-ink-1 px-4 text-sm font-semibold text-white transition hover:bg-ink-1"
      >
        <Save className="h-4 w-4" aria-hidden="true" />
        保存商品
        </button>
      ) : null}
    </form>
  );
}
