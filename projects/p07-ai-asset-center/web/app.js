const API = '/api/v1';
let currentPage = 'dashboard';
let statusCache = { configured: false, model: '', reason: '', cost: {} };

const TYPE_LABEL = { image: '图片', video: '视频', copy: '文案' };
const PLATFORM_LABEL = { douyin: '抖音', taobao: '淘宝', tmall: '天猫', pinduoduo: '拼多多', jd: '京东', kuaishou: '快手', other: '其他' };
const SOURCE_LABEL = { demo: '演示数据', upload: '本地上传', generated: 'AI/程序生成' };

const NAV = [
  { page: 'dashboard', label: '概览', icon: 'grid' },
  { page: 'library', label: '素材库', icon: 'image' },
  { page: 'search', label: '以文搜图', icon: 'search' },
  { page: 'generate', label: 'AI 生成', icon: 'brain' },
  { page: 'report', label: '效果关联', icon: 'chart' }
];

/* ---------- 基础工具 ---------- */
// 素材名/标签/描述都来自用户上传或跨模块推送，插进 DOM 前必须转义
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (m) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
const tagsOf = (v) => Array.isArray(v) ? v : (typeof v === 'string' && v ? v.split(/[,，]/).map(t => t.trim()).filter(Boolean) : []);
const fmtDate = (s) => (s || '').replace('T', ' ');
const kb = (n) => n ? (n > 1024 * 1024 ? (n / 1048576).toFixed(1) + ' MB' : (n / 1024).toFixed(0) + ' KB') : '0 KB';

async function req(path, { method = 'GET', body, form } = {}) {
  const opt = { method, headers: {} };
  if (form) opt.body = form;
  else if (body) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  const r = await fetch(API + path, opt);
  if (!r.ok) {
    let msg = 'HTTP ' + r.status;
    try {
      const d = await r.json();
      msg = typeof d.detail === 'string' ? d.detail
        : (Array.isArray(d.detail) && d.detail[0] && (d.detail[0].msg || d.detail[0].detail)) || d.error && d.error.message || msg;
    } catch (e) { /* 非 JSON 错误体，保留状态码 */ }
    throw new Error(msg);
  }
  return r.status === 204 ? null : r.json();
}

function toast(msg, kind) {
  const t = document.getElementById('toast');
  const colors = { ok: ['var(--cp-success-bg)', 'var(--success)'], warn: ['var(--cp-warning-bg)', 'var(--warning)'], err: ['var(--cp-danger-bg)', 'var(--danger)'] };
  const [bg, fg] = colors[kind || 'ok'];
  t.style.background = bg; t.style.color = fg; t.textContent = msg;
  t.style.display = 'block';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.style.display = 'none'; }, 3200);
}

function errorBox(e, hint) {
  return `<div class="card p-6 text-sm text-[var(--ink2)]">请求失败：${esc(e.message || e)}
    <div class="mt-2 text-xs text-[var(--ink3)]">${hint || '确认 P07 服务在跑：<code>python _tools\\supervisor.py status</code>'}</div></div>`;
}

const NAV_TITLES = { dashboard: '素材概览', library: '素材库', search: '以文搜图', generate: 'AI 生成', report: '投放效果关联' };
const LOADERS = { dashboard: loadDashboard, library: loadLibrary, search: loadSearch, generate: loadGenerate, report: loadReport };

function showPage(page, param) {
  currentPage = page;
  document.querySelectorAll('#nav .tab').forEach(t => t.classList.toggle('active', t.dataset.page === page));
  document.getElementById('page-title').textContent = NAV_TITLES[page] || '';
  (LOADERS[page] || (() => { }))();
  // 深链：#library / #asset/AST-001 / #search/夏天清爽的防晒霜 / #generate/618海报|copy
  // 既方便浏览器前进后退，也让无头截图能定位到具体页面
  if (param !== undefined) location.hash = page + (param ? '/' + encodeURIComponent(param) : '');
}

function routeFromHash() {
  const raw = decodeURIComponent((location.hash || '').replace(/^#/, ''));
  if (!raw) return showPage('dashboard');
  const i = raw.indexOf('/');
  const page = i < 0 ? raw : raw.slice(0, i);
  const param = i < 0 ? '' : raw.slice(i + 1);
  if (page === 'asset') return showAssetDetail(param);
  showPage(page, param);
  if (page === 'search' && param) {
    document.getElementById('search-q').value = param;
    doSearch();
  }
  if (page === 'generate' && param) {
    const [prompt, type] = param.split('|');
    document.getElementById('gen-prompt').value = prompt;
    if (type) document.getElementById('gen-type').value = type;
    const btn = Array.from(document.querySelectorAll('.btn')).find(b => b.textContent.trim() === '生成');
    doGenerate(btn);
  }
}

window.addEventListener('hashchange', routeFromHash);
document.getElementById('nav').innerHTML = NAV.map(n =>
  `<a class="tab" data-page="${n.page}" onclick="showPage('${n.page}','')">${CP.icon(n.icon, 16)}<span>${n.label}</span></a>`
).join('');

/* ---------- 顶部状态徽章：真实接入还是规则兜底，由后端说了算 ---------- */
function sourceBadge(source, extra) {
  const map = {
    llm: ['badge-success', 'LLM 真实生成'],
    rule: ['badge-warning', '规则模板兜底'],
    programmatic: ['badge-warning', '程序化占位图'],
    manual: ['badge-neutral', '人工标签'],
    upload: ['badge-neutral', '人工标签'],
  };
  const [cls, label] = map[source] || ['badge-neutral', source || '未知'];
  return `<span class="badge ${cls}">${esc(label)}${extra ? ' · ' + esc(extra) : ''}</span>`;
}

async function loadStatus() {
  const el = document.getElementById('status-badges');
  try {
    statusCache = await req('/llm/status');
    const c = statusCache.cost || {};
    el.innerHTML = [
      statusCache.configured
        ? `<span class="badge badge-success">${esc('LLM 已接入 · ' + statusCache.model)}</span>`
        : `<span class="badge badge-warning" title="${esc(statusCache.reason)}">模型降级 · 规则兜底</span>`,
      `<span class="badge badge-neutral">${esc(`网关调用 ${c.total_calls || 0} 次 · ${c.total_tokens || 0} tokens · mock ${c.mock_calls || 0}`)}</span>`
    ].join('');
  } catch (e) {
    el.innerHTML = '<span class="badge badge-danger">服务未连通</span>';
  }
}

/* ---------------- 图表基础设施 ---------------- */
// 页面挂在外壳 iframe 里、且样式来自 Tailwind CDN（运行时注入）。
// innerHTML 赋值后立刻 echarts.init 会按「尚未套上 grid 类」的全宽量尺寸，画布会溢出压图 ——
// 这里等两帧布局稳定再初始化，并挂 ResizeObserver。
let charts = [];

// echarts 按需懒加载：整包 echarts.min.js 约 1MB，首屏（外壳布局 / 登录态）并不需要，
// 只有打开「概览 / 效果关联」这类图表页才会用到。改为动态注入脚本、Promise 化，
// 让首屏 HTML 解析完即可绘制外壳，图表在接口数据返回后再 init（见 renderCharts）。
// 注意：head 里已移除 <script src=echarts>，故此处是唯一加载入口；mkChart 仍对
// echarts 未定义做兜底（返回 null），加载失败时仅图表区域空白，不影响其余功能。
let _echartsLoading = null;
function ensureECharts() {
  if (typeof echarts !== 'undefined') return Promise.resolve();
  if (_echartsLoading) return _echartsLoading;
  _echartsLoading = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = '/shared/vendor/echarts.min.js';
    s.async = true;
    s.onload = () => resolve(window.echarts);
    s.onerror = () => reject(new Error('echarts 资源加载失败'));
    document.head.appendChild(s);
  });
  return _echartsLoading;
}

function chartTheme() {
  const cs = getComputedStyle(document.documentElement);
  const v = (n, f) => (cs.getPropertyValue(n) || '').trim() || f;
  return {
    ink2: v('--cp-ink2', '#5A6472'), ink3: v('--cp-ink3', '#8A94A3'),
    line: v('--cp-line', '#DDE2EA'), surface: v('--cp-surface', '#FFFFFF'),
    brand: v('--cp-brand', '#1D4ED8'), success: v('--cp-success', '#16A34A'),
    warning: v('--cp-warning', '#B4690E'), danger: v('--cp-danger', '#D92D20'),
    chart2: v('--cp-chart-2', '#7B5CFA'), chart5: v('--cp-chart-5', '#E4474B'), info: v('--cp-info', '#475467')
  };
}
function disposeCharts() { charts.forEach(c => { try { c.dispose(); } catch (e) { } }); charts = []; }
function mkChart(id, option) {
  const node = document.getElementById(id);
  if (!node || typeof echarts === 'undefined') return null;
  const chart = echarts.init(node, null, { renderer: 'canvas' });
  chart.setOption(option);
  charts.push(chart);
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(node);
    chart.__ro = ro;
  }
  return chart;
}
function renderCharts(build) {
  // 先确保 echarts 就绪（首屏未加载），再双 rAF 等布局稳定后绘制；
  // 加载失败仅图表区域空白，不阻塞页面其余交互。
  ensureECharts()
    .then(() => requestAnimationFrame(() => requestAnimationFrame(build)))
    .catch((e) => { console.error('[p07] 图表不可用：', e); });
}

/* ---------------- 概览 ---------------- */
async function loadDashboard() {
  disposeCharts();
  const el = document.getElementById('content');
  let s, perf, assets;
  try {
    // size 上限是 100（后端 le=100），超了会 422 让整页空白
    // with_platform_metrics=false：概览页只用 perf.items 画图，不展示 P06 大盘卡片；
    // 后端默认会同步 httpx 调 P06（超时 4s），P06 没起来时首屏被白等拖慢 —— 这里显式关掉。
    // 「效果关联」页仍走默认 true 保留跨模块指标。
    [s, perf, assets] = await Promise.all([
      req('/stats'), req('/reports/performance?with_platform_metrics=false'), req('/assets?size=100')
    ]);
  } catch (e) { el.innerHTML = errorBox(e); return; }

  el.innerHTML = `
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
      ${metricCard('素材总数', s.total_assets, 'brand', '总', `含预览文件 ${s.with_preview_file} 个`)}
      ${metricCard('已关联投放', s.linked_assets, 'success', '投', `覆盖率 ${(s.coverage_rate * 100).toFixed(0)}%`)}
      ${metricCard('总花费', '¥' + s.total_spend.toLocaleString(), 'warning', '费', `收入 ¥${s.total_revenue.toLocaleString()}`)}
      ${metricCard('整体 ROI', s.roi + 'x', 'accent', 'ROI', '收入 / 花费')}
    </div>
    <div class="grid gap-4 lg:grid-cols-2 mb-4">
      <div class="card p-5"><h3 class="text-sm font-medium text-[var(--ink2)] mb-3">素材类型分布</h3><div class="chart-box" id="chart-type"></div></div>
      <div class="card p-5"><h3 class="text-sm font-medium text-[var(--ink2)] mb-3">投放转化漏斗（已关联素材汇总）</h3><div class="chart-box" id="chart-funnel"></div></div>
    </div>
    <div class="grid gap-4 lg:grid-cols-2 mb-4">
      <div class="card p-5"><h3 class="text-sm font-medium text-[var(--ink2)] mb-3">素材 ROI 排行</h3><div class="chart-box" id="chart-roi"></div></div>
      <div class="card p-5"><h3 class="text-sm font-medium text-[var(--ink2)] mb-3">各平台花费与收入</h3><div class="chart-box" id="chart-platform"></div></div>
    </div>
    <div class="grid gap-4 lg:grid-cols-2">
      <div class="card p-5"><h3 class="text-sm font-medium text-[var(--ink2)] mb-3">素材标签热度 Top 10</h3><div class="chart-box" id="chart-tags"></div></div>
      <div class="card p-5"><h3 class="text-sm font-medium text-[var(--ink2)] mb-3">标签来源分布（LLM 真实 vs 人工/规则）</h3><div class="chart-box" id="chart-tag-src"></div></div>
    </div>
    <p class="mt-4 text-xs text-[var(--ink3)]">演示数据边界：source=demo 的 12 条素材（含程序化绘制的演示图）来自初始化播种；上传、AI 生成与跨模块推送的素材以真实文件与真实时间戳入库。所有图表均由接口真实字段聚合，无随机造数。</p>`;

  renderCharts(() => {
    const T = chartTheme();
    const palette = [T.brand, T.success, T.warning, T.chart2, T.chart5, T.info];

    mkChart('chart-type', {
      tooltip: { trigger: 'item', formatter: '{b}：{c} 个（{d}%）' },
      color: palette,
      legend: { bottom: 0, textStyle: { color: T.ink2 }, itemWidth: 10, itemHeight: 10 },
      series: [{
        type: 'pie', radius: ['42%', '66%'], center: ['50%', '44%'], avoidLabelOverlap: true,
        itemStyle: { borderColor: T.surface, borderWidth: 2 },
        label: { color: T.ink2, formatter: '{b}\n{c}' },
        labelLine: { lineStyle: { color: T.line } },
        data: Object.entries(s.by_type).map(([k, v]) => ({ name: TYPE_LABEL[k] || k, value: v }))
      }]
    });

    const sum = perf.items.reduce((a, i) => ({ imp: a.imp + i.impressions, clk: a.clk + i.clicks, cvt: a.cvt + i.conversions }), { imp: 0, clk: 0, cvt: 0 });
    mkChart('chart-funnel', {
      tooltip: { trigger: 'item', formatter: p => `${p.name}：${p.value.toLocaleString()}` },
      color: [T.brand, T.info, T.success],
      series: [{
        type: 'funnel', left: '6%', right: '6%', top: 10, bottom: 10, sort: 'descending', gap: 4,
        minSize: '12%', maxSize: '100%',
        label: { position: 'inside', color: '#FFFFFF', formatter: p => `${p.name}  ${p.value.toLocaleString()}` },
        itemStyle: { borderWidth: 0 },
        data: [
          { name: '曝光', value: sum.imp },
          { name: `点击 · CTR ${(sum.imp ? sum.clk / sum.imp * 100 : 0).toFixed(1)}%`, value: sum.clk },
          { name: `转化 · CVR ${(sum.clk ? sum.cvt / sum.clk * 100 : 0).toFixed(1)}%`, value: sum.cvt }
        ]
      }]
    });

    const roiItems = perf.items.slice().sort((a, b) => a.roi - b.roi);
    mkChart('chart-roi', {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}<br/>ROI：${p[0].value}x` },
      grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: 'value', axisLabel: { color: T.ink2, formatter: '{value}x' }, splitLine: { lineStyle: { color: T.line } } },
      yAxis: { type: 'category', data: roiItems.map(i => i.name), axisLabel: { color: T.ink2, width: 110, overflow: 'truncate' }, axisLine: { lineStyle: { color: T.line } } },
      series: [{ type: 'bar', data: roiItems.map(i => i.roi), barMaxWidth: 16, itemStyle: { color: T.brand, borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right', color: T.ink2, formatter: '{c}x' } }]
    });

    const platformMap = {};
    perf.items.forEach(i => {
      const m = platformMap[i.platform] || (platformMap[i.platform] = { spend: 0, revenue: 0 });
      m.spend += i.spend; m.revenue += i.revenue;
    });
    const pLabels = Object.keys(platformMap);
    mkChart('chart-platform', {
      tooltip: { trigger: 'axis', valueFormatter: v => '¥' + Number(v).toLocaleString() },
      legend: { data: ['花费', '收入'], textStyle: { color: T.ink2 }, top: 0, itemWidth: 10, itemHeight: 10 },
      grid: { left: 8, right: 16, top: 34, bottom: 8, containLabel: true },
      xAxis: { type: 'category', data: pLabels.map(k => PLATFORM_LABEL[k] || k), axisLabel: { color: T.ink2 }, axisLine: { lineStyle: { color: T.line } } },
      yAxis: { type: 'value', axisLabel: { color: T.ink2, formatter: v => v >= 10000 ? (v / 10000) + '万' : v }, splitLine: { lineStyle: { color: T.line } } },
      series: [
        { name: '花费', type: 'bar', data: pLabels.map(k => Math.round(platformMap[k].spend)), itemStyle: { color: T.warning, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 22 },
        { name: '收入', type: 'bar', data: pLabels.map(k => Math.round(platformMap[k].revenue)), itemStyle: { color: T.success, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 22 }
      ]
    });

    const tagCount = {};
    assets.items.forEach(a => tagsOf(a.tags).forEach(t => { tagCount[t] = (tagCount[t] || 0) + 1; }));
    const tags = Object.entries(tagCount).sort((a, b) => a[1] - b[1]).slice(0, 10);
    mkChart('chart-tags', {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: 'value', minInterval: 1, axisLabel: { color: T.ink2 }, splitLine: { lineStyle: { color: T.line } } },
      yAxis: { type: 'category', data: tags.map(t => t[0]), axisLabel: { color: T.ink2 }, axisLine: { lineStyle: { color: T.line } } },
      series: [{ type: 'bar', data: tags.map(t => t[1]), barMaxWidth: 14, itemStyle: { color: T.chart2, borderRadius: [0, 4, 4, 0] } }]
    });

    const srcLabel = { llm: 'LLM 打标', rule: '规则兜底', manual: '人工/推送' };
    const srcData = Object.entries(s.by_tag_source || {}).map(([k, v]) => ({ name: srcLabel[k] || k, value: v }));
    mkChart('chart-tag-src', {
      tooltip: { trigger: 'item', formatter: '{b}：{c} 个（{d}%）' },
      color: [T.success, T.warning, T.info],
      legend: { bottom: 0, textStyle: { color: T.ink2 }, itemWidth: 10, itemHeight: 10 },
      series: [{
        type: 'pie', radius: '58%', center: ['50%', '44%'],
        itemStyle: { borderColor: T.surface, borderWidth: 2 },
        label: { color: T.ink2, formatter: '{b}\n{c}' }, labelLine: { lineStyle: { color: T.line } },
        data: srcData
      }]
    });
  });
}

function metricCard(label, value, accent, mark, sub) {
  const colors = { brand: 'var(--brand)', success: 'var(--success)', warning: 'var(--warning)', accent: 'var(--cp-chart-2)' };
  const bgs = { brand: 'var(--brand-bg)', success: 'var(--cp-success-bg)', warning: 'var(--cp-warning-bg)', accent: 'var(--cp-elevated)' };
  return `<div class="card p-5 flex items-center gap-4">
    <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-xs font-bold" style="background:${bgs[accent]};color:${colors[accent]}">${esc(mark)}</div>
    <div class="min-w-0"><p class="text-sm text-[var(--ink3)] truncate">${esc(label)}</p>
    <p class="text-2xl font-semibold">${esc(value)}</p>
    <p class="text-xs text-[var(--ink3)] truncate">${esc(sub || '')}</p></div></div>`;
}

/* ---------------- 素材库（含上传） ---------------- */
let uploadPicked = null;

async function loadLibrary() {
  let d;
  try { d = await req('/assets?size=50'); } catch (e) { document.getElementById('content').innerHTML = errorBox(e); return; }
  const el = document.getElementById('content');
  el.innerHTML = `
    <div class="card p-5 mb-4">
      <h3 class="text-sm font-medium mb-3">上传素材</h3>
      <div class="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div><label class="fl">素材名称 *</label><input id="up-name" class="w-full" placeholder="如：夏季控油防晒喷雾主图"></div>
        <div><label class="fl">类型</label><select id="up-type" class="w-full"><option value="image">图片</option><option value="video">视频</option><option value="copy">文案</option></select></div>
        <div class="lg:col-span-2"><label class="fl">标签（逗号分隔）</label><input id="up-tags" class="w-full" placeholder="防晒,夏季,主图"></div>
      </div>
      <div class="mt-3"><label class="fl">描述</label><input id="up-desc" class="w-full" placeholder="用于以文搜图的语义描述"></div>
      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <div class="drop" id="drop" onclick="document.getElementById('up-file').click()">点击选择或拖入文件（png / jpg / webp / gif / mp4 / mov / webm，≤32MB）
          <div class="mt-1 text-xs" id="drop-info">支持多文件依次上传，文件真实字节与图片宽高会被读取</div></div>
        <div class="flex flex-col justify-between gap-2">
          <label class="flex items-center gap-2 text-sm text-[var(--ink2)]">
            <input type="checkbox" id="up-autotag" class="w-auto" ${statusCache.configured ? 'checked' : ''}>
            上传后自动智能打标${statusCache.configured ? '（LLM 真实调用，约 2-8 秒）' : '（当前模型降级，走词表规则）'}
          </label>
          <input type="file" id="up-file" class="hidden" accept="image/*,video/*">
          <div class="flex gap-2"><button class="btn btn-primary" onclick="doUpload(this)">上传入库</button>
          <span class="text-xs text-[var(--ink3)] self-center">文件落 <code>data/uploads/</code>，入库后卡片即可预览</span></div>
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-3 mb-4">
      <input id="kw" placeholder="搜索素材名称/标签/描述..." class="flex-1 min-w-40" onkeyup="if(event.key==='Enter')filterLib()">
      <select id="type-filter" onchange="filterLib()"><option value="">全部类型</option><option value="image">图片</option><option value="video">视频</option><option value="copy">文案</option></select>
      <button class="btn btn-primary" onclick="filterLib()">搜索</button>
      <button class="btn btn-secondary" onclick="loadLibrary()">重置</button>
      <span class="text-xs text-[var(--ink3)]" id="lib-count"></span>
    </div>
    <div id="asset-grid" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"></div>`;

  bindDrop();
  renderAssets(d.items, d.total);
}

function bindDrop() {
  const zone = document.getElementById('drop'), input = document.getElementById('up-file');
  if (!zone) return;
  const showFile = (f) => {
    uploadPicked = f;
    document.getElementById('drop-info').textContent = f ? `已选：${f.name}（${kb(f.size)}）` : '支持多文件依次上传，文件真实字节与图片宽高会被读取';
  };
  input.onchange = () => showFile(input.files[0]);
  zone.ondragover = (e) => { e.preventDefault(); zone.classList.add('on'); };
  zone.ondragleave = () => zone.classList.remove('on');
  zone.ondrop = (e) => {
    e.preventDefault(); zone.classList.remove('on');
    if (e.dataTransfer.files[0]) { input.files = e.dataTransfer.files; showFile(e.dataTransfer.files[0]); }
  };
}

async function doUpload(btn) {
  const name = document.getElementById('up-name').value.trim();
  if (!name) { toast('请填写素材名称', 'err'); return; }
  const form = new FormData();
  form.append('name', name);
  form.append('asset_type', document.getElementById('up-type').value);
  form.append('tags', document.getElementById('up-tags').value);
  form.append('description', document.getElementById('up-desc').value);
  form.append('auto_tag', document.getElementById('up-autotag').checked ? 'true' : 'false');
  if (uploadPicked) form.append('file', uploadPicked);

  const submit = btn; submit.disabled = true; submit.textContent = '上传中…';
  try {
    const asset = await req('/assets', { method: 'POST', form });
    const tg = asset.tagging;
    toast(`已入库 ${asset.asset_id}${tg ? ` · 打标来源 ${tg.tag_source}` : ''}`, tg && tg.tag_source === 'llm' ? 'ok' : 'warn');
    if (tg && tg.degraded_reason) toast(tg.degraded_reason, 'warn');
    uploadPicked = null;
    loadStatus();
    loadLibrary();
  } catch (e) { toast('上传失败：' + e.message, 'err'); submit.disabled = false; submit.textContent = '上传入库'; }
}

function thumbHTML(a) {
  const url = a.file_url;
  const mime = a.mime_type || '';
  if (url && mime.startsWith('video/')) return `<video src="${esc(url)}" muted preload="metadata"></video>`;
  if (url && (mime.startsWith('image/') || !mime)) return `<img src="${esc(url)}" alt="${esc(a.name)}" loading="lazy">`;
  if (a.asset_type === 'copy') return `<span class="px-3 text-center">${esc((a.content || a.description || '文案素材').slice(0, 60))}</span>`;
  const mark = { image: '图片（无文件）', video: '视频（无文件）', copy: 'TXT' }[a.asset_type] || '素材';
  return esc(mark);
}

function renderAssets(items, total) {
  const grid = document.getElementById('asset-grid');
  const count = document.getElementById('lib-count');
  if (count) count.textContent = `共 ${total} 条，显示 ${items.length} 条`;
  grid.innerHTML = items.map(a => `
    <div class="card overflow-hidden hover:border-[var(--brand)] transition cursor-pointer" onclick="showAssetDetail('${esc(a.asset_id)}')">
      <div class="thumb">${thumbHTML(a)}</div>
      <div class="p-3">
        <p class="text-sm font-medium truncate">${esc(a.name)}</p>
        <div class="mt-2 flex flex-wrap gap-1">${tagsOf(a.tags).slice(0, 3).map(t => `<span class="badge badge-brand">${esc(t)}</span>`).join('')}</div>
        <div class="mt-2 flex items-center justify-between text-xs text-[var(--ink3)]">
          <span>${esc(TYPE_LABEL[a.asset_type] || a.asset_type)} · ${esc(a.asset_type === 'copy' ? '' : (a.width && a.height ? a.width + '×' + a.height : '未标注'))}</span>
          <span>${esc(kb(a.file_size))}</span>
        </div>
        <div class="mt-2 flex items-center justify-between">
          <span class="badge ${a.source === 'demo' ? 'badge-neutral' : 'badge-success'}">${esc((SOURCE_LABEL[a.source] || a.source))}</span>
          <span class="text-xs text-[var(--ink3)]">${esc(fmtDate(a.created_at))}</span>
        </div>
      </div>
    </div>`).join('') || '<p class="text-sm text-[var(--ink3)]">没有符合条件的素材</p>';
}

async function filterLib() {
  const kw = document.getElementById('kw').value.trim();
  const type = document.getElementById('type-filter').value;
  let url = `${API}/assets?size=50`;
  if (kw) url += `&keyword=${encodeURIComponent(kw)}`;
  if (type) url += `&asset_type=${type}`;
  try {
    const d = await req(url.replace(API, ''));
    renderAssets(d.items, d.total);
  } catch (e) { toast('筛选失败：' + e.message, 'err'); }
}

/* ---------------- 素材详情 ---------------- */
async function showAssetDetail(id) {
  let a;
  try { a = await req(`/assets/${encodeURIComponent(id)}`); } catch (e) { document.getElementById('content').innerHTML = errorBox(e); return; }
  if (location.hash !== '#asset/' + encodeURIComponent(id)) location.hash = 'asset/' + encodeURIComponent(id);
  const el = document.getElementById('content');
  const tags = tagsOf(a.tags);
  el.innerHTML = `
    <button class="btn btn-secondary mb-4" onclick="showPage('library','')">← 返回素材库</button>
    <div class="grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2 space-y-4">
        <div class="card p-3">${a.file_url
          ? `<img src="${esc(a.file_url)}" alt="${esc(a.name)}" class="w-full max-h-96 object-contain bg-[var(--elevated)] rounded">`
          : `<div class="thumb" style="height:14rem">${a.asset_type === 'copy' ? esc((a.content || a.description || '文案素材').slice(0, 120)) : '该素材没有可预览的文件'}</div>`}
        </div>
        ${a.content ? `<div class="card p-5"><h3 class="font-medium mb-2">素材正文</h3><pre class="whitespace-pre-wrap text-sm text-[var(--ink2)] font-sans">${esc(a.content)}</pre></div>` : ''}

        <div class="card p-5">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-medium">投放效果（${a.performance.length} 条）</h3>
            <button class="btn btn-secondary" onclick="togglePerfForm()">录入投放数据</button>
          </div>
          <div id="perf-form" class="hidden mb-4 grid gap-2 md:grid-cols-4">
            <div><label class="fl">店铺 *</label><input id="pf-store" class="w-full" placeholder="示例旗舰店"></div>
            <div><label class="fl">平台</label><select id="pf-platform" class="w-full">${Object.entries(PLATFORM_LABEL).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></div>
            <div><label class="fl">开始日期</label><input id="pf-start" type="date" class="w-full" value="2026-10-01"></div>
            <div><label class="fl">结束日期</label><input id="pf-end" type="date" class="w-full" value="2026-10-13"></div>
            <div><label class="fl">曝光</label><input id="pf-imp" type="number" min="0" class="w-full" value="50000"></div>
            <div><label class="fl">点击</label><input id="pf-clk" type="number" min="0" class="w-full" value="3000"></div>
            <div><label class="fl">转化</label><input id="pf-cvt" type="number" min="0" class="w-full" value="120"></div>
            <div><label class="fl">花费(元)</label><input id="pf-spend" type="number" min="0" step="0.01" class="w-full" value="2000"></div>
            <div><label class="fl">收入(元)</label><input id="pf-rev" type="number" min="0" step="0.01" class="w-full" value="15000"></div>
            <div class="md:col-span-3 flex items-end"><button class="btn btn-primary" onclick="savePerformance('${esc(a.asset_id)}')">提交</button>
            <span class="ml-3 text-xs text-[var(--ink3)]">点击>曝光 或 转化>点击 会被后端 422 拒绝</span></div>
          </div>
          ${a.performance.length ? `<div class="overflow-x-auto"><table class="w-full text-sm"><thead><tr class="text-[var(--ink3)]"><th class="text-left py-2">平台</th><th class="text-left">店铺</th><th>曝光</th><th>点击</th><th>转化</th><th>花费</th><th>收入</th><th>ROI</th></tr></thead><tbody>
            ${a.performance.map(p => {
              const roi = p.spend > 0 ? (p.revenue / p.spend).toFixed(1) + 'x' : '-';
              return `<tr class="border-t border-[var(--line)]"><td class="py-2">${esc(PLATFORM_LABEL[p.platform] || p.platform)}</td><td>${esc(p.store_name)}</td>
                <td class="text-center">${p.impressions.toLocaleString()}</td><td class="text-center">${p.clicks.toLocaleString()}</td><td class="text-center">${p.conversions}</td>
                <td class="text-center">¥${p.spend.toLocaleString()}</td><td class="text-center">¥${p.revenue.toLocaleString()}</td>
                <td class="text-center font-medium text-[var(--brand)]">${esc(roi)}</td></tr>`;
            }).join('')}
          </tbody></table></div>` : '<p class="text-[var(--ink3)] text-sm">暂无投放数据</p>'}
        </div>
      </div>

      <div class="space-y-4">
        <div class="card p-5">
          <div class="flex items-center justify-between mb-3"><h3 class="font-medium">智能打标</h3>${sourceBadge(a.tag_source)}</div>
          <div class="flex flex-wrap gap-2 mb-3" id="tag-box">${tags.map(t => `<span class="badge badge-brand">${esc(t)}</span>`).join('') || '<span class="text-xs text-[var(--ink3)]">暂无标签</span>'}</div>
          <div class="flex gap-2">
            <button class="btn btn-primary" onclick="reTag('${esc(a.asset_id)}', true)">重新打标（覆盖）</button>
            <button class="btn btn-secondary" onclick="reTag('${esc(a.asset_id)}', false)">追加</button>
          </div>
          <p class="mt-2 text-xs text-[var(--ink3)]">打标走 shared/llm-gateway；模型不可用时退回词表规则并标为「规则兜底」。</p>
        </div>

        <div class="card p-5"><h3 class="font-medium mb-3">素材信息</h3>
          <dl class="space-y-1 text-sm">
            <dt class="text-[var(--ink3)]">ID</dt><dd>${esc(a.asset_id)}</dd>
            <dt class="text-[var(--ink3)]">类型 / 来源</dt><dd>${esc(TYPE_LABEL[a.asset_type] || a.asset_type)} · ${esc(SOURCE_LABEL[a.source] || a.source)}</dd>
            <dt class="text-[var(--ink3)]">尺寸 / 大小</dt><dd>${esc(a.width && a.height ? a.width + '×' + a.height : '未标注')} · ${esc(kb(a.file_size))}${esc(a.mime_type ? ' · ' + a.mime_type : '')}</dd>
            <dt class="text-[var(--ink3)]">创建时间</dt><dd>${esc(fmtDate(a.created_at))}</dd>
            <dt class="text-[var(--ink3)]">更新时间</dt><dd>${esc(fmtDate(a.updated_at))}</dd>
            <dt class="text-[var(--ink3)]">描述</dt><dd>${esc(a.description || '-')}</dd>
          </dl>
        </div>
        <div class="card p-5"><h3 class="font-medium mb-2 text-[var(--danger)]">删除素材</h3>
          <p class="text-xs text-[var(--ink3)] mb-3">删除会同时清掉投放关联与磁盘文件，不可恢复。</p>
          <button class="btn btn-danger" onclick="removeAsset('${esc(a.asset_id)}')">删除 ${esc(a.asset_id)}</button></div>
      </div>
    </div>`;
}

function togglePerfForm() { document.getElementById('perf-form').classList.toggle('hidden'); }

async function savePerformance(id) {
  const num = (el) => Number(document.getElementById(el).value || 0);
  const payload = {
    store_name: document.getElementById('pf-store').value.trim(),
    platform: document.getElementById('pf-platform').value,
    impressions: num('pf-imp'), clicks: num('pf-clk'), conversions: num('pf-cvt'),
    spend: num('pf-spend'), revenue: num('pf-rev'),
    period_start: document.getElementById('pf-start').value,
    period_end: document.getElementById('pf-end').value
  };
  if (!payload.store_name) { toast('请填写店铺名', 'err'); return; }
  try {
    await req(`/assets/${encodeURIComponent(id)}/performance`, { method: 'POST', body: payload });
    toast('投放数据已录入', 'ok');
    showAssetDetail(id);
  } catch (e) { toast('录入被拒绝：' + e.message, 'err'); }
}

async function reTag(id, overwrite) {
  const btns = document.querySelectorAll('.btn');
  btns.forEach(b => { if (b.textContent.includes('打标')) b.disabled = true; });
  try {
    const r = await req(`/assets/${encodeURIComponent(id)}/tag`, { method: 'POST', body: { overwrite } });
    document.getElementById('tag-box').innerHTML = tagsOf(r.tags).map(t => `<span class="badge badge-brand">${esc(t)}</span>`).join('');
    toast(r.tag_source === 'llm' ? `LLM 打标完成（${r.meta.latency_ms}ms）` : '已用规则兜底打标', r.tag_source === 'llm' ? 'ok' : 'warn');
    if (r.degraded_reason) toast(r.degraded_reason, 'warn');
  } catch (e) { toast('打标失败：' + e.message, 'err'); }
  btns.forEach(b => { if (b.textContent.includes('打标')) b.disabled = false; });
}

async function removeAsset(id) {
  if (!confirm(`确认删除素材 ${id}？文件与投放关联会一并删除。`)) return;
  try {
    const r = await req(`/assets/${encodeURIComponent(id)}`, { method: 'DELETE' });
    toast(`已删除 ${r.asset_id}${r.file_removed ? '（含磁盘文件）' : ''}`, 'ok');
    loadLibrary();
  } catch (e) { toast('删除失败：' + e.message, 'err'); }
}

/* ---------------- 以文搜图 ---------------- */
function loadSearch() {
  document.getElementById('content').innerHTML = `
    <div class="note">${CP.icon('search', 16)}<span>检索引擎：<code>中文 n-gram 分词 + 同义组归一 + 字段加权打分（tags&gt;name&gt;description）+ IDF 抑制泛词</code>。
    这是文本层检索，<b>不是 CLIP 多模态向量检索</b>；低于阈值会明确拒答而不是返回弱相关结果。</span></div>
    <div class="card p-6 mb-6">
      <div class="flex flex-wrap gap-3">
        <input id="search-q" class="flex-1 min-w-48" placeholder="用自然语言描述，如：夏天清爽的防晒霜" onkeyup="if(event.key==='Enter')doSearch()">
        <select id="search-type"><option value="">全部类型</option><option value="image">图片</option><option value="video">视频</option><option value="copy">文案</option></select>
        <select id="search-k"><option value="5">Top 5</option><option value="10">Top 10</option><option value="20">Top 20</option></select>
        <button class="btn btn-primary" onclick="doSearch()">搜索</button>
      </div>
      <div class="mt-3 flex flex-wrap gap-2 text-xs">
        <span class="text-[var(--ink3)]">试试：</span>
        ${['夏天清爽的防晒霜', '有没有直播用的背景板', '双十一预售的海报', '科技感运动鞋详情', '库里没有的无人机航拍素材']
          .map(q => `<button class="badge badge-neutral hover:bg-[var(--brand-bg)]" onclick="document.getElementById('search-q').value='${q}';doSearch()">${esc(q)}</button>`).join('')}
      </div>
    </div>
    <div id="search-results"></div>`;
}

async function doSearch() {
  const q = document.getElementById('search-q').value.trim();
  if (!q) { toast('请输入检索描述', 'err'); return; }
  const el = document.getElementById('search-results');
  el.innerHTML = '<p class="text-sm text-[var(--ink3)]">检索中…</p>';
  const body = { query: q, top_k: Number(document.getElementById('search-k').value) };
  const type = document.getElementById('search-type').value;
  if (type) body.asset_type = type;
  let d;
  try { d = await req('/search', { method: 'POST', body }); } catch (e) { el.innerHTML = errorBox(e); return; }

  if (d.refused) {
    el.innerHTML = `<div class="card p-6"><h3 class="font-medium mb-2">库内无匹配素材（已拒答）</h3>
      <p class="text-sm text-[var(--ink2)]">${esc(d.reason)}</p>
      <p class="mt-2 text-xs text-[var(--ink3)]">切出的检索词：${esc((d.query_terms || []).join(' / '))}</p></div>`;
    return;
  }
  el.innerHTML = `<p class="text-sm text-[var(--ink2)] mb-3">命中 ${d.total} 条（候选 ${d.candidates} 条，阈值 ${d.threshold}）· 切词 ${esc((d.query_terms || []).slice(0, 8).join(' / '))}</p>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">${d.items.map(i => `
    <div class="card p-4 hover:border-[var(--brand)] transition cursor-pointer" onclick="showAssetDetail('${esc(i.asset_id)}')">
      <div class="flex items-center justify-between mb-2">
        <span class="badge badge-brand">相关度 ${(i.relevance_score * 100).toFixed(0)}%</span>
        <span class="text-xs text-[var(--ink3)]">${esc(TYPE_LABEL[i.asset_type] || i.asset_type)}</span>
      </div>
      <div class="relbar mb-3"><i style="width:${(i.relevance_score * 100).toFixed(0)}%"></i></div>
      <p class="text-sm font-medium">${esc(i.name)}</p>
      <p class="text-xs text-[var(--ink3)] mt-1">${esc(i.description || '')}</p>
      <p class="text-xs text-[var(--ink2)] mt-2">命中理由（词 → 命中的字段）：</p>
      <div class="mt-1 flex flex-wrap gap-1">${(i.matched_terms || []).map(m => `<span class="badge badge-success">${esc(m.term)}→${esc(m.fields.join(','))}</span>`).join('')}</div>
    </div>`).join('')}</div>`;
}

/* ---------------- AI 生成 ---------------- */
function loadGenerate() {
  document.getElementById('content').innerHTML = `
    <div class="note">${CP.icon('brain', 16)}<span>文案与视频分镜脚本经 <code>shared/llm-gateway</code> 真实生成（prompt 版本化在 <code>prompts/</code>）；
    图片类型为<b>程序化绘制的投放规格卡片</b>，不是 AI 出图 —— 真实图像模型接口在本环境未验证，未验证不宣称已跑通。</span></div>
    <div class="card p-6 mb-6">
      <div class="space-y-4">
        <div><label class="fl">提示词 *</label><textarea id="gen-prompt" class="w-full" rows="3" placeholder="描述要生成的素材，如：春季新品氨基酸洗发水温和去油"></textarea></div>
        <div class="flex flex-wrap gap-4">
          <div><label class="fl">类型</label><select id="gen-type"><option value="copy">文案</option><option value="video">视频脚本</option><option value="image">图片（规格卡）</option></select></div>
          <div><label class="fl">风格</label><select id="gen-style"><option value="commercial">商业</option><option value="creative">创意</option><option value="minimal">极简</option></select></div>
          <label class="flex items-center gap-2 text-sm text-[var(--ink2)] self-end mb-2"><input type="checkbox" id="gen-save" class="w-auto" checked>生成后保存到素材库</label>
          <button class="btn btn-primary self-end mb-1" onclick="doGenerate(this)">生成</button>
        </div>
      </div>
    </div>
    <div id="gen-result"></div>`;
}

async function doGenerate(btn) {
  const prompt = document.getElementById('gen-prompt').value.trim();
  if (!prompt) { toast('请输入提示词', 'err'); return; }
  const submit = btn; submit.disabled = true; submit.textContent = '生成中…';
  const el = document.getElementById('gen-result');
  const t0 = Date.now();
  el.innerHTML = `<p class="text-sm text-[var(--ink3)]">真实模型生成中 —— 本环境实测 19-30 秒（网关超时上限 75 秒，超时则退回规则模板并如实标注）。已等待 <span id="gen-timer">0s</span></p>`;
  const tick = setInterval(() => {
    const n = document.getElementById('gen-timer');
    if (!n) { clearInterval(tick); return; }
    n.textContent = Math.round((Date.now() - t0) / 1000) + 's';
  }, 1000);
  let d;
  try {
    d = await req('/generate', { method: 'POST', body: {
      prompt, asset_type: document.getElementById('gen-type').value,
      style: document.getElementById('gen-style').value,
      save_to_library: document.getElementById('gen-save').checked
    } });
  } catch (e) { el.innerHTML = errorBox(e); submit.disabled = false; submit.textContent = '生成'; return; }
  submit.disabled = false; submit.textContent = '生成';

  const r = d.result, meta = d.meta || {};
  const metaLine = meta.model ? `${esc(meta.model)} · ${esc(meta.latency_ms)}ms · ${esc(meta.total_tokens)} tokens · prompt ${esc(meta.prompt_version)}` : '未调用模型（程序化绘制）';
  let body = '';
  if (d.content_type === 'copy') {
    body = `<p class="text-lg font-medium">${esc(r.title)}</p><p class="text-sm text-[var(--ink2)] mt-1">${esc(r.subtitle || '')}</p>
      <ul class="mt-3 space-y-1 text-sm">${(r.bullets || []).map(b => `<li class="flex gap-2"><span class="text-[var(--brand)]">·</span>${esc(b)}</li>`).join('')}</ul>
      <p class="mt-3"><span class="badge badge-brand">${esc(r.cta || '')}</span></p>
      ${r.content ? `<pre class="whitespace-pre-wrap text-sm mt-3 text-[var(--ink2)] font-sans">${esc(r.content)}</pre>` : ''}`;
  } else if (d.content_type === 'video_script') {
    body = `<p class="font-medium">${esc(r.title)}</p><p class="text-xs text-[var(--ink3)] mt-1">总时长 ${esc(r.total_seconds)}s</p>
      <table class="w-full text-sm mt-3"><thead><tr class="text-[var(--ink3)] text-left"><th class="py-1">时间</th><th>画面</th><th>口播</th><th>字幕</th></tr></thead>
      <tbody>${(r.scenes || []).map(s => `<tr class="border-t border-[var(--line)]"><td class="py-1">${esc(s.time)}</td><td>${esc(s.shot)}</td><td>${esc(s.voice)}</td><td>${esc(s.on_screen_text)}</td></tr>`).join('')}</tbody></table>`;
  } else {
    const preview = d.saved_asset ? d.saved_asset.file_url : d.preview_data_url;
    body = `<p class="font-medium">${esc(r.title)}</p><p class="text-sm text-[var(--ink2)] mt-1">${esc(r.description || '')}</p>
      ${preview ? `<img src="${esc(preview)}" alt="生成预览" class="mt-3 max-h-72 rounded border border-[var(--line)]">` : ''}`;
  }
  el.innerHTML = `<div class="card p-6">
    <div class="flex items-center justify-between mb-3"><h3 class="font-medium">生成结果</h3>
      <div class="flex items-center gap-2">${sourceBadge(d.source)}<span class="text-xs text-[var(--ink3)]">${metaLine}</span></div></div>
    ${body}
    <div class="mt-3 flex flex-wrap gap-1">${tagsOf(r.tags).map(t => `<span class="badge badge-brand">${esc(t)}</span>`).join('')}</div>
    ${d.note ? `<p class="mt-3 text-xs text-[var(--warning)]">${esc(d.note)}</p>` : ''}
    ${d.saved_asset ? `<p class="mt-3 text-sm text-[var(--success)]">已保存到素材库：<a class="underline" href="javascript:showAssetDetail('${esc(d.saved_asset.asset_id)}')">${esc(d.saved_asset.asset_id)}</a> · ${esc(d.saved_asset.name)}</p>` : ''}
  </div>`;
  loadStatus();
}

/* ---------------- 效果关联报表 ---------------- */
async function loadReport(platform) {
  const chosen = platform !== undefined ? platform : (document.getElementById('perf-platform') || {}).value;
  let d;
  try { d = await req('/reports/performance' + (chosen ? `?platform=${encodeURIComponent(chosen)}` : '')); } catch (e) { document.getElementById('content').innerHTML = errorBox(e); return; }
  const pm = d.platform_metrics || {};
  const el = document.getElementById('content');
  el.innerHTML = `
    <div class="card p-5 mb-4">
      <div class="flex flex-wrap items-center gap-3">
        <label class="text-sm text-[var(--ink2)]">平台</label>
        <select id="perf-platform" onchange="loadReport(this.value)"><option value="">全部平台</option>
          ${Object.entries(PLATFORM_LABEL).map(([k, v]) => `<option value="${k}" ${k === chosen ? 'selected' : ''}>${v}</option>`).join('')}</select>
        <span class="text-xs text-[var(--ink3)]">共 ${d.total} 条关联记录</span>
      </div>
    </div>

    <div class="card p-5 mb-4">
      <h3 class="text-sm font-medium mb-1">大盘对照（真实跨模块调用 P06 数据中台）</h3>
      <p class="text-xs text-[var(--ink3)] mb-3">目标：<code>${esc(pm.source_url || '')}</code>${pm.fetched_at ? ' · 取数于 ' + esc(fmtDate(pm.fetched_at)) : ''}</p>
      ${pm.available ? `<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">${pm.metrics.map(m => `
        <div class="card p-4"><p class="text-xs text-[var(--ink3)]">${esc(m.name)}</p>
        <p class="text-xl font-semibold">${esc(m.latest)}<span class="text-xs font-normal text-[var(--ink3)] ml-1">${esc(m.unit)}</span></p>
        <p class="text-xs text-[var(--ink2)]">近均 ${esc(m.avg)} · 趋势 ${(m.trend * 100).toFixed(1)}%</p></div>`).join('')}</div>`
        : `<div class="note mt-2"><span>P06 指标不可用，此处不编造大盘数字。原因：${esc(pm.reason || '未知')}</span></div>`}
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="bg-[var(--elevated)] text-[var(--ink3)]"><th class="text-left px-4 py-3">素材</th><th>类型</th><th>平台</th><th>店铺</th><th class="text-right">曝光</th><th class="text-right">点击</th><th class="text-right">CTR</th><th class="text-right">转化</th><th class="text-right">CVR</th><th class="text-right">花费</th><th class="text-right">收入</th><th class="text-right">ROI</th></tr></thead>
        <tbody>${d.items.map(i => `<tr class="border-t border-[var(--line)] hover:bg-[var(--elevated)] cursor-pointer" onclick="showAssetDetail('${esc(i.asset_id)}')">
          <td class="px-4 py-3 font-medium">${esc(i.name)}</td>
          <td class="text-center">${esc(TYPE_LABEL[i.asset_type] || i.asset_type)}</td>
          <td class="text-center">${esc(PLATFORM_LABEL[i.platform] || i.platform)}</td>
          <td class="text-center">${esc(i.store_name)}</td>
          <td class="text-right">${i.impressions.toLocaleString()}</td>
          <td class="text-right">${i.clicks.toLocaleString()}</td>
          <td class="text-right">${(i.ctr * 100).toFixed(1)}%</td>
          <td class="text-right">${i.conversions}</td>
          <td class="text-right">${(i.cvr * 100).toFixed(1)}%</td>
          <td class="text-right">¥${i.spend.toLocaleString()}</td>
          <td class="text-right">¥${i.revenue.toLocaleString()}</td>
          <td class="text-right font-medium text-[var(--brand)]">${i.roi}x</td></tr>`).join('') || '<tr><td colspan="12" class="px-4 py-6 text-center text-[var(--ink3)]">暂无关联数据</td></tr>'}
        </tbody></table>
    </div>`;
}

/* ---------------- 主题联动 ---------------- */
// 图表色板从 CSS 变量读取，主题切换后必须重画，否则残留上一个主题的配色
if (typeof MutationObserver !== 'undefined') {
  new MutationObserver(() => {
    if (currentPage === 'dashboard' && charts.length) showPage('dashboard');
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
}
window.addEventListener('resize', () => charts.forEach(c => c.resize()));

document.getElementById('nav').querySelector('.tab').classList.add('active');
loadStatus();
routeFromHash();
