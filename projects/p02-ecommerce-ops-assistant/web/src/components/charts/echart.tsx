"use client";

import { useEffect, useRef } from "react";
// 按需引入：只打包首页用到的饼图/柱状图 + 画布渲染器 + 必要组件，
// 避免把整个 echarts（含所有图表类型/渲染器/组件 + zrender）全量打进首屏 chunk。
// 对 `next dev`（当前公网演示形态，发的是未压缩未 minify 的代码）尤其关键：
// 全量 echarts 未压缩后数 MB，按需后仅数百 KB 级。
import * as echarts from "echarts/core";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
// echarts 6 起网格 containment 从 GridComponent 拆出：
// 柱状图 option 用了 grid.containLabel，必须显式注册该特性，否则
// dev 下告警 "Specified grid.containLabel but no use(LegacyGridContainLabel)"
// 且标签布局降级（轴标签可能溢出裁切）。
import { LegacyGridContainLabel } from "echarts/features";
import type { ECharts, EChartsOption } from "echarts";

echarts.use([
  PieChart,
  BarChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  LegacyGridContainLabel,
  CanvasRenderer,
]);

/* ECharts 画在 canvas 上，吃不到 CSS 变量，所以这里的字面值必须与
   shared/ui-kit/tokens.css 的白底态令牌保持一致（改令牌要同步改这里）。 */
const lightTheme = {
  color: ["#1D4ED8", "#12B76A", "#F79009", "#E4474B", "#7B5CFA", "#98A2B3", "#245AE0", "#B4690E"],
  backgroundColor: "transparent",
  textStyle: { color: "#5A6472" },
  title: { textStyle: { color: "#1A1F2B" }, subtextStyle: { color: "#8A94A3" } },
  legend: { textStyle: { color: "#5A6472" } },
  tooltip: {
    backgroundColor: "#FFFFFF",
    borderColor: "#DDE2EA",
    textStyle: { color: "#1A1F2B" },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#DDE2EA" } },
    axisTick: { lineStyle: { color: "#DDE2EA" } },
    axisLabel: { color: "#8A94A3" },
    splitLine: { lineStyle: { color: "#EEF1F6" } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: "#DDE2EA" } },
    axisTick: { lineStyle: { color: "#DDE2EA" } },
    axisLabel: { color: "#8A94A3" },
    splitLine: { lineStyle: { color: "#EEF1F6" } },
  },
};

echarts.registerTheme("cp-light", lightTheme);

/** 轻量 ECharts 封装：客户端初始化、白底主题、自适应容器尺寸、卸载时销毁。 */
export function EChart({
  option,
  height = 280,
  className,
}: {
  option: EChartsOption;
  height?: number;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el, "cp-light", { renderer: "canvas" });
    chartRef.current = chart;

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(el);

    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: "100%", height }}
    />
  );
}
