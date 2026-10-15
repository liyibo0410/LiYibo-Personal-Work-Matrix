// 静态验证：复刻 echart.tsx 的按需注册与 dashboard-charts.tsx 的四个 option，
// 用 SSR(svg) 模式跑 init/setOption，验证注册项是否齐全（不依赖浏览器）。
import * as echarts from "echarts/core";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer, SVGRenderer } from "echarts/renderers";

echarts.use([
  PieChart,
  BarChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
  SVGRenderer, // 仅测试用：ssr 模式需要 svg 渲染器
]);

const palette = ["#1D4ED8", "#12B76A", "#F79009", "#E4474B"];
const axisText = "#8A94A3";
const axisLine = "#DDE2EA";

function donutOption(data) {
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, textStyle: { color: axisText, fontSize: 12 } },
    series: [{ type: "pie", radius: ["45%", "70%"], center: ["50%", "44%"], avoidLabelOverlap: true, itemStyle: { borderColor: "#FFFFFF", borderWidth: 2 }, label: { show: false }, data: data.map((d) => ({ name: d.name, value: d.value })), color: palette }],
  };
}
function hBarOption(data) {
  const sorted = [...data].sort((a, b) => a.value - b.value);
  return {
    grid: { left: 8, right: 28, top: 10, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", axisLabel: { color: axisText }, splitLine: { lineStyle: { color: axisLine } } },
    yAxis: { type: "category", data: sorted.map((d) => d.name), axisLabel: { color: axisText }, axisLine: { lineStyle: { color: axisLine } }, axisTick: { show: false } },
    series: [{ type: "bar", data: sorted.map((d) => d.value), barWidth: 14, itemStyle: { color: "#1D4ED8", borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", color: axisText, fontSize: 12 } }],
  };
}
function vBarOption(data) {
  return {
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "category", data: data.map((d) => d.name), axisLabel: { color: axisText, interval: 0, rotate: data.length > 4 ? 28 : 0 }, axisLine: { lineStyle: { color: axisLine } }, axisTick: { show: false } },
    yAxis: { type: "value", axisLabel: { color: axisText }, splitLine: { lineStyle: { color: axisLine } } },
    series: [{ type: "bar", data: data.map((d) => d.value), barWidth: "46%", itemStyle: { color: "#1D4ED8", borderRadius: [4, 4, 0, 0] }, label: { show: true, position: "top", color: axisText, fontSize: 12 } }],
  };
}

const cases = {
  donut: donutOption([{ name: "抖音", value: 3 }, { name: "淘宝", value: 2 }]),
  hBar: hBarOption([{ name: "店铺A", value: 5 }, { name: "店铺B", value: 2 }]),
  vBar: vBarOption([{ name: "类目1", value: 4 }, { name: "类目2", value: 1 }]),
};

let failed = false;
for (const [name, option] of Object.entries(cases)) {
  try {
    const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: 400, height: 260 });
    chart.setOption(option);
    const svg = chart.renderToSVGString();
    const empty = svg.length < 200 || !/<(rect|path|circle)/.test(svg);
    console.log(`[OK] ${name}: setOption 无异常, svg len=${svg.length}${empty ? " (疑似空图!)" : ""}`);
    chart.dispose();
  } catch (e) {
    failed = true;
    console.error(`[FAIL] ${name}:`, e && e.message);
  }
}
process.exit(failed ? 1 : 0);
