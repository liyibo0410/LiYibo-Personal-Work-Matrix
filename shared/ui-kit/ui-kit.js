/* ══════════════════════════════════════════════════════════════════
   云枢智能统一平台 · 共享前端运行时（ui-kit.js）
   提供：主题切换、侧栏折叠/移动端抽屉、shell↔模块 postMessage 桥、
        SERVICE_REGISTRY 读取助手（配合 services.js 的 window.CP_REGISTRY）。
   无第三方依赖。模块页面与 shell 均可引入。
   ══════════════════════════════════════════════════════════════════ */
(function (global) {
  "use strict";

  var CP = global.CP = global.CP || {};

  /* ---------------- 主题 ---------------- */
  // 默认白底（浅色）。键升到 v2 并清掉旧值：旧浏览器里存着的 "dark" 是「深色曾是默认」
  // 留下的自动值而不是用户主动选的，留着它会让全站默认翻不回白底。
  var THEME_KEY = "cp_theme_v2";
  var LEGACY_THEME_KEY = "cp_theme";
  // 外壳挂载模块时用 ?cp-theme= 传初值：iframe 与外壳不同源，localStorage 不共享，
  // 只靠 postMessage 会先闪一下深色再翻白。
  CP.themeFromUrl = function () {
    try {
      var m = /[?&]cp-theme=(light|dark)/.exec(global.location.search);
      return m ? m[1] : "";
    } catch (e) { return ""; }
  };
  CP.getTheme = function () {
    var fromUrl = CP.themeFromUrl();
    if (fromUrl) return fromUrl;
    try {
      if (localStorage.getItem(LEGACY_THEME_KEY)) localStorage.removeItem(LEGACY_THEME_KEY);
      return localStorage.getItem(THEME_KEY) || "light";
    } catch (e) { return "light"; }
  };
  CP.setTheme = function (theme) {
    var t = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
    // 通知父窗口（模块在 iframe 内时，让 shell 同步主题）
    CP.postToParent({ type: "cp:theme", theme: t });
    return t;
  };
  CP.toggleTheme = function () {
    return CP.setTheme(CP.getTheme() === "dark" ? "light" : "dark");
  };
  CP.initTheme = function () { CP.setTheme(CP.getTheme()); };

  /* ---------------- 侧栏折叠 / 移动端抽屉 ---------------- */
  CP.initSidebar = function (sidebarEl) {
    var sb = sidebarEl || document.querySelector(".cp-sidebar");
    if (!sb) return;
    var COLLAPSE_KEY = "cp_sidebar_collapsed";
    try {
      if (localStorage.getItem(COLLAPSE_KEY) === "1" && global.innerWidth > 640) {
        sb.classList.add("collapsed");
      }
    } catch (e) {}
    CP._sidebar = sb;
    CP._sidebarCollapseKey = COLLAPSE_KEY;
  };
  CP.toggleSidebar = function () {
    var sb = CP._sidebar || document.querySelector(".cp-sidebar");
    if (!sb) return;
    if (global.innerWidth <= 640) {
      sb.classList.toggle("open");           // 移动端：抽屉
    } else {
      sb.classList.toggle("collapsed");      // 桌面端：窄栏
      try { localStorage.setItem(CP._sidebarCollapseKey || "cp_sidebar_collapsed",
        sb.classList.contains("collapsed") ? "1" : "0"); } catch (e) {}
    }
  };
  CP.closeSidebar = function () {
    var sb = CP._sidebar || document.querySelector(".cp-sidebar");
    if (sb) sb.classList.remove("open");
  };

  /* ---------------- 品牌位（公司名 / logo）----------------
     唯一真源是 shared/config/brand.json。shell 登录后从 /api/brand 读取并
     用 postMessage(cp:brand) 下发给 iframe 模块；独立访问模块时（不在 iframe
     里）由这里自行同源拉取。页面用 data-cp-brand="字段名" 声明要绑定的节点。 */
  CP.DEFAULT_BRAND = {
    company: "云枢智能", name_en: "CloudPivot", subtitle: "统一平台",
    tagline: "AI 电商运营中台", version: "v1.0", logo: "", initials: "CP"
  };
  CP.getBrand = function () { return CP._brand || CP.DEFAULT_BRAND; };

  // 把 dataURL 之外的垃圾值挡掉，避免拼进 innerHTML 造成注入
  function safeLogo(b) {
    var logo = b.logo || "";
    return /^data:image\//.test(logo) ? logo : "";
  }
  CP.applyBrand = function (brand) {
    if (brand) {
      var merged = {};
      Object.keys(CP.DEFAULT_BRAND).forEach(function (k) {
        merged[k] = typeof brand[k] === "string" ? brand[k] : CP.DEFAULT_BRAND[k];
      });
      CP._brand = merged;
    }
    var b = CP.getBrand();
    var logo = safeLogo(b);
    document.querySelectorAll("[data-cp-brand]").forEach(function (node) {
      var key = node.getAttribute("data-cp-brand");
      if (key === "logo") {
        node.innerHTML = logo ? '<img src="' + logo + '" alt="logo">' : (b.initials || "");
        node.classList.toggle("cp-brand-is-image", !!logo);
        return;
      }
      if (key === "initials") { if (!logo) node.textContent = b.initials || ""; return; }
      var v = b[key];
      if (typeof v === "string") node.textContent = v;
    });
    // 「自定义 logo 优先，没设就用页面自带标识」的图片位：给有自己产品 mark 的模块
    // （P05 衡鉴、P01 听澜）用，属性值就是它们的默认图地址。
    document.querySelectorAll("[data-cp-brand-logo-src]").forEach(function (node) {
      var want = logo || node.getAttribute("data-cp-brand-logo-src") || "";
      if (!want) { return; }
      if (node.tagName === "IMG") {
        if (node.getAttribute("src") !== want) { node.setAttribute("src", want); }
      } else if (node.style.backgroundImage.indexOf(want) === -1) {
        node.style.backgroundImage = 'url("' + want + '")';
      }
    });
    var titleNode = document.querySelector("[data-cp-brand-title]");
    if (titleNode) document.title = titleNode.getAttribute("data-cp-brand-title")
      .replace(/\{company\}/g, b.company).replace(/\{name_en\}/g, b.name_en);
    // 品牌是异步到位的：由 JS 渲染顶栏/页脚（P05）或框架托管 DOM（P01/P03）的代码
    // 需要这个事件才能在自己的绘制里用到最新值。
    try { document.dispatchEvent(new CustomEvent("cp:brand-applied", { detail: b })); } catch (e) {}
    return b;
  };

  // 品牌来源按顺序尝试，取到即用，取不到就保留默认值（绝不让页面白屏）：
  //   ① 页面声明的同源地址 —— 静态模块把 /shared 挂进了自己的服务；
  //   ② 外壳网关 GET /api/brand —— 覆盖 file:// 打开的门户，以及 dev server
  //      没有 /shared 映射、/shared 路径只会命中 SPA fallback 的构建型模块。
  // 网关端口只从 SERVICE_REGISTRY（services.js 的 CP_REGISTRY.gateway）解析。
  CP.brandSources = function (declared) {
    var urls = [];
    if (declared) { urls.push(declared); }
    var reg = global.CP_REGISTRY || {};
    var port = reg.gateway && reg.gateway.web_port;
    if (port) {
      urls.push("http://" + (global.location.hostname || reg.host || "127.0.0.1") +
        ":" + port + "/api/brand");
    }
    return urls;
  };

  CP.loadBrand = function (url) {
    var declared = url !== undefined ? url
      : (document.body && document.body.getAttribute("data-cp-brand-src"));
    var urls = CP.brandSources(declared);
    var i = 0;
    function attempt() {
      if (i >= urls.length) { return Promise.resolve(CP.getBrand()); }
      return fetch(urls[i++], { cache: "no-store" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) {
          // brand.json 本身就是品牌对象；网关接口包了一层 {ok, brand}
          var b = j && (typeof j.brand === "object" && j.brand ? j.brand : j);
          if (b && typeof b.company === "string") { CP.applyBrand(b); return CP.getBrand(); }
          return attempt();
        })
        .catch(function () { return attempt(); });
    }
    return attempt();
  };

  /* ---------------- 服务健康状态 ---------------- */
  CP.setServiceHealth = function (health) { CP._health = health || {}; };
  CP.serviceOnline = function (id) {
    var h = CP._health && CP._health[id];
    return h ? !!h.online : null;   // null = 还没探测过
  };

  /* ---------------- postMessage 桥 ---------------- */
  // 模块 → 父窗口（shell）
  CP.postToParent = function (msg) {
    try {
      if (global.parent && global.parent !== global) {
        global.parent.postMessage(Object.assign({ source: "cp-module" }, msg), "*");
      }
    } catch (e) {}
  };
  // 在 iframe 内标记自身，并上报就绪 + 期望高度
  CP.initModuleBridge = function (meta) {
    meta = meta || {};
    document.documentElement.setAttribute("data-cp-embedded", "1");
    CP.postToParent({ type: "cp:ready", module: meta.module || "", title: meta.title || document.title });
    // 自适应高度：把内容高度上报给 shell，供其调整 iframe
    if (typeof ResizeObserver !== "undefined" && document.body) {
      var ro = new ResizeObserver(function () {
        CP.postToParent({ type: "cp:resize", height: document.documentElement.scrollHeight });
      });
      ro.observe(document.body);
    }
    // 接收 shell 下发的主题 / 令牌 / 品牌
    global.addEventListener("message", function (ev) {
      var d = ev.data || {};
      if (d.source !== "cp-shell") return;
      if (d.type === "cp:theme") { CP.setTheme(d.theme); }
      if (d.type === "cp:auth") { CP._token = d.token || ""; }
      if (d.type === "cp:brand") { CP.applyBrand(d.brand); }
    });
  };
  CP.inIframe = function () {
    try { return global.self !== global.top; } catch (e) { return true; }
  };
  CP.getToken = function () { return CP._token || ""; };

  /* ---------------- SERVICE_REGISTRY 助手 ---------------- */
  // 依赖 services.js 注入的 window.CP_REGISTRY
  CP.registry = function () { return global.CP_REGISTRY || null; };
  CP.serviceUrl = function (id, which) {
    var reg = CP.registry();
    if (!reg || !reg.services[id]) return "";
    var s = reg.services[id];
    var p = which === "web" ? (s.web_port || s.api_port) : s.api_port;
    // 跟随当前访问主机，局域网打开时不会退化成访客自己机器的 127.0.0.1
    var host = (global.location && global.location.hostname) || reg.host;
    return "http://" + host + ":" + p;
  };
  CP.apiUrl = function (id, path) {
    var reg = CP.registry();
    if (!reg || !reg.services[id]) return "";
    var s = reg.services[id];
    var prefix = (s.api_prefix || "").replace(/\/$/, "");
    var p = path ? ("_" + path).replace(/^_\/?/, "/") : "";
    return CP.serviceUrl(id) + prefix + p;
  };
  CP.serviceIds = function () {
    var reg = CP.registry();
    return reg ? Object.keys(reg.services).sort() : [];
  };
  CP.byLayer = function () {
    var reg = CP.registry(); var out = {};
    if (!reg) return out;
    Object.keys(reg.services).forEach(function (id) {
      var L = reg.services[id].layer || "?";
      (out[L] = out[L] || []).push(id);
    });
    Object.keys(out).forEach(function (L) { out[L].sort(); });
    return out;
  };

  /* ---------------- 图标（内联 SVG，统一线条风格）---------------- */
  var ICONS = {
    chat: "M4 5h16v10H8l-4 4z", chart: "M5 19V9m5 10V5m5 14v-7m4 7H3",
    search: "M11 4a7 7 0 105.3 11.6L21 20", book: "M5 4h9a3 3 0 013 3v13H8a3 3 0 01-3-3z",
    doc: "M7 3h7l4 4v14H7zM14 3v4h4", database: "M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6",
    image: "M4 5h16v14H4zM4 15l4-4 3 3 3-3 6 6", video: "M4 6h11v12H4zM15 10l5-3v10l-5-3",
    trophy: "M7 4h10v5a5 5 0 01-10 0zM5 5h2M17 5h2M9 20h6M12 14v6", brain: "M9 4a3 3 0 00-3 3 3 3 0 00-2 5 3 3 0 002 5 3 3 0 003 3h1V4zM15 4a3 3 0 013 3 3 3 0 012 5 3 3 0 01-2 5 3 3 0 01-3 3h-1V4z",
    home: "M4 11l8-7 8 7v9h-6v-5h-4v5H4z", grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"
  };
  CP.icon = function (name, size) {
    var d = ICONS[name] || ICONS.grid;
    var s = size || 20;
    return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" ' +
      'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="' + d + '"/></svg>';
  };

  /* ---------------- 自动初始化 ---------------- */
  function boot() {
    CP.initTheme();
    CP.initSidebar();
    // 品牌位：先用默认值占位，再按「页面声明的同源地址 → 外壳网关」依次拉真实配置
    CP.applyBrand();
    CP.loadBrand();
    // 模块页面若声明 data-cp-module，自动建立桥接
    var m = document.body && document.body.getAttribute("data-cp-module");
    if (m && CP.inIframe()) { CP.initModuleBridge({ module: m }); }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }

})(typeof window !== "undefined" ? window : this);
