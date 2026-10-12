"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { ECharts, EChartsOption } from "echarts";

const darkTheme = {
  color: ["#3370FF", "#4ADE80", "#FB923C", "#F87171", "#6B9BFF", "#A1C0FF", "#34D399", "#FBBF24"],
  backgroundColor: "transparent",
  textStyle: { color: "#9ba3b0" },
  title: { textStyle: { color: "#e8eaf0" }, subtextStyle: { color: "#6b7280" } },
  legend: { textStyle: { color: "#9ba3b0" } },
  tooltip: {
    backgroundColor: "#1a1f2b",
    borderColor: "#2a3040",
    textStyle: { color: "#e8eaf0" },
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#2a3040" } },
    axisTick: { lineStyle: { color: "#2a3040" } },
    axisLabel: { color: "#6b7280" },
    splitLine: { lineStyle: { color: "#1e2430" } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: "#2a3040" } },
    axisTick: { lineStyle: { color: "#2a3040" } },
    axisLabel: { color: "#6b7280" },
    splitLine: { lineStyle: { color: "#1e2430" } },
  },
};

echarts.registerTheme("dark-pivot", darkTheme);

/** 轻量 ECharts 封装：客户端初始化、深色主题、自适应容器尺寸、卸载时销毁。 */
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
    const chart = echarts.init(el, "dark-pivot", { renderer: "canvas" });
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
