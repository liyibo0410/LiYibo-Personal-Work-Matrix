import { BarChart3, Package, Store, TrendingUp } from "lucide-react";
import { redirect } from "next/navigation";

import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { getCurrentUser } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { isOwner } from "@/lib/permissions";

async function fetchOverview(token: string) {
  const base = process.env.API_INTERNAL_BASE_URL
    ?? process.env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://127.0.0.1:8000";
  const res = await fetch(`${base}/api/v1/dashboard/overview`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (res.status === 403) return null;
  if (!res.ok) throw new Error("Failed to fetch dashboard overview");
  return res.json();
}

export default async function BossDashboardPage() {
  const token = await getAuthToken();
  if (!token) redirect("/login");

  const currentUser = await getCurrentUser(token);
  if (!currentUser) redirect("/login");
  if (!isOwner(currentUser)) redirect("/?forbidden=dashboard");

  const overview = await fetchOverview(token);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink-1">经营总览</h1>
        <p className="mt-1 text-sm text-ink-3">仅老板可见的经营数据看板</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          icon={Store}
          label="店铺总数"
          value={overview?.total_stores ?? 0}
          accent="brand"
        />
        <MetricCard
          icon={TrendingUp}
          label="营业中"
          value={overview?.active_stores ?? 0}
          accent="success"
        />
        <MetricCard
          icon={Package}
          label="商品总数"
          value={overview?.total_products ?? 0}
          accent="warning"
        />
        <MetricCard
          icon={BarChart3}
          label="数据健康度"
          value="98%"
          accent="brand"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            经营趋势
            {overview?.metrics_source === "p06-live" ? (
              <span className="rounded bg-success-bg px-2 py-0.5 text-xs font-normal text-success">
                数据来源：P06 数据中台（实时）
              </span>
            ) : (
              <span className="rounded bg-warning-bg px-2 py-0.5 text-xs font-normal text-warning">
                P06 数据中台不可达 · 已降级
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardBody>
          {overview?.metrics_degraded && (
            <p className="mb-3 text-xs text-warning">
              跨模块调用失败：{overview?.metrics_error || "P06 未启动或超时"}。
              以下为降级状态，无指标数据（不伪装真实数据）。
            </p>
          )}
          {overview?.metrics && overview.metrics.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {overview.metrics.map((m: {
                code: string; name: string; unit: string;
                latest: number; avg: number; trend: number;
              }) => (
                <div
                  key={m.code}
                  className="rounded-lg border border-line bg-fill-1 p-3"
                >
                  <p className="text-xs text-ink-3">{m.name}</p>
                  <p className="mt-1 text-xl font-semibold text-ink-1">
                    {formatMetric(m.latest, m.code)}
                    <span className="ml-1 text-xs font-normal text-ink-4">{m.unit}</span>
                  </p>
                  <p className={`mt-1 text-xs ${m.trend >= 0 ? "text-success" : "text-danger"}`}>
                    {m.trend >= 0 ? "▲" : "▼"} {Math.abs(m.trend * 100).toFixed(1)}%
                    <span className="ml-1 text-ink-4">较均值</span>
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-line bg-fill-1">
              <span className="text-sm text-ink-4">暂无 P06 指标数据</span>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function formatMetric(value: number, code: string): string {
  if (code === "conversion_rate" || code === "return_rate") {
    return (value * 100).toFixed(2);
  }
  if (Math.abs(value) >= 10000) {
    return (value / 10000).toFixed(2) + "万";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}


function MetricCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: typeof Store;
  label: string;
  value: string | number;
  accent: "brand" | "success" | "warning";
}) {
  const accentClasses = {
    brand: "bg-brand-50 text-brand-600",
    success: "bg-success-bg text-success",
    warning: "bg-warning-bg text-warning",
  };

  return (
    <Card>
      <CardBody className="flex items-center gap-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${accentClasses[accent]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <p className="text-sm text-ink-3">{label}</p>
          <p className="text-2xl font-semibold text-ink-1">{value}</p>
        </div>
      </CardBody>
    </Card>
  );
}
