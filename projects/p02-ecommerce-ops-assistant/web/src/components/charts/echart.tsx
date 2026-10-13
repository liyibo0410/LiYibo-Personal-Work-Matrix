"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { ECharts, EChartsOption } from "echarts";

/* ECharts 画在 canvas 上，吃不到 CSS 变量，所以这里的字面值必须与
   shared/ui-kit/tokens.css 的白底态令牌保持一致（改令牌要同步改这里）。 */
const lightTheme = {
  color: ["#3370FF", "#12B76A", "#F79009", "#E4474B", "#7B5CFA", "#98A2B3", "#245AE0", "#B4690E"],
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
