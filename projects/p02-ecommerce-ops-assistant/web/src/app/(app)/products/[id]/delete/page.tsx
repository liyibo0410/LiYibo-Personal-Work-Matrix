import { ArrowLeft, Trash2, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { getProduct, getCurrentUser } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { canEdit as canEditFn } from "@/lib/permissions";

type ProductDeletePageProps = {
  params: Promise<{ id: string }>;
};

/** 渲染商品删除确认页；删除不可恢复，改成服务端渲染的第二步确认，不依赖浏览器弹窗。 */
export default async function ProductDeletePage({ params }: ProductDeletePageProps) {
  const { id } = await params;
  const token = await getAuthToken();
  const [product, currentUser] = await Promise.all([
    getProduct(id),
    token ? getCurrentUser(token) : Promise.resolve(null),
  ]);

  if (!product) {
    notFound();
  }

  const canEdit = canEditFn(currentUser);
  const cascadeItems = [
    { label: "SKU", value: product.skus.length },
    { label: "平台映射", value: product.platform_mappings.length },
    { label: "竞品", value: product.competitors.length },
    { label: "竞品监控", value: product.competitor_monitors.length },
    { label: "创意方案", value: product.creative_plans.length },
    { label: "素材", value: product.generated_assets.length },
    { label: "生成任务", value: product.generation_jobs.length },
    { label: "推广链接", value: product.promotion_links.length },
    { label: "经营数据", value: product.performance_records.length },
    { label: "广告实验", value: product.ad_experiments.length },
    { label: "广告建议", value: product.ad_recommendations.length },
    { label: "复盘报告", value: product.review_reports.length },
    { label: "诊断结论", value: product.diagnoses.length },
    { label: "链接解析任务", value: product.public_link_parse_tasks.length },
  ].filter((item) => item.value > 0);

  return (
    <div className="mx-auto flex max-w-[860px] flex-col gap-6">
      <PageHeader
        title="删除商品"
        description={`即将删除「${product.name}」，此操作不可恢复`}
        actions={
          <Link
            href={`/products/${id}`}
            className={buttonVariants({ variant: "secondary" })}
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            返回商品
          </Link>
        }
      />

      <Card className="flex flex-col gap-4 p-5">
        <div className="flex items-start gap-3 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden="true" />
          <p className="text-sm text-danger">
            商品是单品运营闭环的聚合根，删除会把下面这些关联数据一并清除，
            <strong className="font-semibold">不会进入回收站</strong>。
          </p>
        </div>

        {cascadeItems.length === 0 ? (
          <p className="text-sm text-ink-2">
            该商品目前没有关联数据，删除只会移除商品本身。
          </p>
        ) : (
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {cascadeItems.map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-line bg-surface px-4 py-3"
              >
                <dt className="text-xs text-ink-3">{item.label}</dt>
                <dd className="mt-1 text-xl font-semibold text-ink-1">{item.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <p className="text-xs text-ink-3">
          库存档案与流水、推广链接点击、竞品监控快照随各自父级一并清除；
          Agent 运行记录与人工审批记录会保留，只解除与本商品的关联。
        </p>
      </Card>

      {canEdit ? (
        <Card className="flex flex-col items-start gap-3 p-5">
          <p className="text-sm font-medium text-ink-1">确认删除？</p>
          <form action={`/products/${id}/delete/confirm`} method="post">
            <button
              type="submit"
              className={buttonVariants({ variant: "danger" })}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              确认删除商品
            </button>
          </form>
        </Card>
      ) : (
        <Card className="p-5">
          <p className="text-sm text-warning">
            当前账号为只读权限，不能删除商品。上面的清单只展示这次会连带清除的数据范围。
          </p>
        </Card>
      )}
    </div>
  );
}
