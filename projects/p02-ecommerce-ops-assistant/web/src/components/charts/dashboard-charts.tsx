"use client";

import type { EChartsOption } from "echarts";

import { Card, CardBody, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { BarChart3 } from "lucide-react";
import { EChart } from "./echart";

export type NameValue = { name: string; value: number };

/** 深色主题调色板：品牌蓝为主，辅以绿/橙/红/灰。 */
const palette = [
  "#3370FF",
  "#4ADE80",
  "#FB923C",
  "#F87171",
  "#6B9BFF",
  "#A1C0FF",
  "#34D399",
  "#FBBF24",
];
const axisText = "#6b7280";
const axisLine = "#2a3040";

function donutOption(data: NameValue[], colors: string[] = palette): EChartsOption {
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: {
      bottom: 0,
      left: "center",
      icon: "circle",
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: axisText, fontSize: 12 },
    },
    series: [
      {
        type: "pie",
        radius: ["45%", "70%"],
        center: ["50%", "44%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: "#141820", borderWidth: 2 },
        label: { show: false },
        data: data.map((d) => ({ name: d.name, value: d.value })),
        color: colors,
      },
    ],
  };
}

function hBarOption(data: NameValue[]): EChartsOption {
  const sorted = [...data].sort((a, b) => a.value - b.value);
  return {
    grid: { left: 8, right: 28, top: 10, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "value",
      axisLabel: { color: axisText },
      splitLine: { lineStyle: { color: axisLine } },
    },
    yAxis: {
      type: "category",
      data: sorted.map((d) => d.name),
      axisLabel: { color: axisText },
      axisLine: { lineStyle: { color: axisLine } },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: sorted.map((d) => d.value),
        barWidth: 14,
        itemStyle: { color: "#3370FF", borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: "right", color: axisText, fontSize: 12 },
      },
    ],
  };
}

function vBarOption(data: NameValue[]): EChartsOption {
  return {
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: {
      type: "category",
      data: data.map((d) => d.name),
      axisLabel: { color: axisText, interval: 0, rotate: data.length > 4 ? 28 : 0 },
      axisLine: { lineStyle: { color: axisLine } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: axisText },
      splitLine: { lineStyle: { color: axisLine } },
    },
    series: [
      {
        type: "bar",
        data: data.map((d) => d.value),
        barWidth: "46%",
        itemStyle: { color: "#3370FF", borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: "top", color: axisText, fontSize: 12 },
      },
    ],
  };
}

function ChartCard({
  title,
  description,
  data,
  children,
}: {
  title: string;
  description: string;
  data: NameValue[];
  children: React.ReactNode;
}) {
  const hasData = data.some((d) => d.value > 0);
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </div>
      </CardHeader>
      <CardBody className="pt-2">
        {hasData ? (
          children
        ) : (
          <EmptyState
            icon={<BarChart3 className="h-5 w-5" aria-hidden="true" />}
            title="暂无数据"
            description="创建商品或店铺后这里会展示分布。"
            className="border-0 py-10"
          />
        )}
      </CardBody>
    </Card>
  );
}

/** 工作台数据概览图表区：平台分布、店铺状态、各店铺商品数、类目分布。 */
export function DashboardCharts({
  productsByPlatform,
  storeStatus,
  storeProductCounts,
  categoryCounts,
}: {
  productsByPlatform: NameValue[];
  storeStatus: NameValue[];
  storeProductCounts: NameValue[];
  categoryCounts: NameValue[];
}) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="平台商品分布" description="各平台在售商品数量" data={productsByPlatform}>
        <EChart option={donutOption(productsByPlatform)} height={260} />
      </ChartCard>

      <ChartCard title="店铺状态分布" description="启用 / 暂停 / 关闭" data={storeStatus}>
        <EChart
          option={donutOption(storeStatus, ["#4ADE80", "#FB923C", "#4B5563"])}
          height={260}
        />
      </ChartCard>

      <ChartCard title="各店铺商品数" description="商品归属最多的店铺" data={storeProductCounts}>
        <EChart option={hBarOption(storeProductCounts)} height={260} />
      </ChartCard>

      <ChartCard title="商品类目分布" description="按类目聚合的商品数量" data={categoryCounts}>
        <EChart option={vBarOption(categoryCounts)} height={260} />
      </ChartCard>
    </section>
  );
}
