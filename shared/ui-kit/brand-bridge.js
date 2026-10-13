/* 构建型模块（P01 客服、P03 问数这类需要打包的前端）使用的品牌桥。
 *
 * 契约与 shared/ui-kit/ui-kit.js 的 CP.applyBrand 完全一致：页面用
 *   data-cp-brand="company|name_en|subtitle|tagline|version|logo|initials"
 *   data-cp-brand-logo-src="/assets/xxx.png"   自定义 logo 优先，没设就用这个默认图
 *   data-cp-brand-title="{company} · 统一平台"  浏览器标题
 * 声明绑定节点。
 *
 * 与 ui-kit.js 的差别只在「怎么拿到 brand.json」：这类模块的 dev server 没有
 * /shared 同源映射（路径会被 SPA fallback 吃掉），所以网关端口由调用方在构建期
 * 从 SERVICE_REGISTRY（shared/config/services.json）import 进来，禁止写死数字。
 * 挂载进外壳时走 postMessage(cp:brand)，独立访问时回落外壳网关 GET /api/brand。
 */

function safeLogo(logo) {
  // 只认图片 dataURL：brand.json 里混进别的东西时不能拼进 innerHTML
  return /^data:image\//.test(logo || "") ? logo : "";
}

export function initBrandBridge(options) {
  const opts = options || {};
  const reg = opts.registry || {};
  let brand = null;

  function apply() {
    if (!brand) return;
    const logo = safeLogo(brand.logo);
    document.querySelectorAll("[data-cp-brand]").forEach((node) => {
      const key = node.getAttribute("data-cp-brand");
      if (key === "logo") {
        const want = logo ? '<img src="' + logo + '" alt="logo">' : (brand.initials || "");
        if (node.innerHTML !== want) node.innerHTML = want;
        node.classList.toggle("cp-brand-is-image", !!logo);
        return;
      }
      const val = brand[key];
      if (typeof val === "string" && node.textContent !== val) node.textContent = val;
    });
    document.querySelectorAll("[data-cp-brand-logo-src]").forEach((node) => {
      const want = logo || node.getAttribute("data-cp-brand-logo-src") || "";
      if (!want) return;
      if (node.tagName === "IMG") {
        if (node.getAttribute("src") !== want) node.setAttribute("src", want);
      } else if (node.style.backgroundImage.indexOf(want) === -1) {
        node.style.backgroundImage = 'url("' + want + '")';
      }
    });
    const titleNode = document.querySelector("[data-cp-brand-title]");
    if (titleNode) {
      document.title = titleNode.getAttribute("data-cp-brand-title")
        .replace(/\{company\}/g, brand.company || "")
        .replace(/\{name_en\}/g, brand.name_en || "");
    }
  }

  // Vue 重渲染会重建节点，DOM 变化后要把品牌补回。写入前都先比对，值已一致就不再写，
  // 所以观察器不会被自己的写入持续触发；一帧内多次变更合并成一次重放。
  let queued = false;
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; apply(); });
  }
  function watchDom() {
    if (typeof MutationObserver === "undefined" || !document.body) return;
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
  }

  function pick(json) {
    // 网关包了一层 {ok, brand}，brand.json 本身就是品牌对象
    if (!json || typeof json !== "object") return null;
    const b = typeof json.brand === "object" && json.brand ? json.brand : json;
    return typeof b.company === "string" ? b : null;
  }

  function sources() {
    const urls = [];
    if (opts.src) urls.push(opts.src);
    const port = reg.gateway && reg.gateway.web_port;
    if (port) {
      // 主机跟随当前访问地址：本机是 127.0.0.1，局域网访问自动换成局域网 IP
      urls.push("http://" + (location.hostname || reg.host || "127.0.0.1") + ":" + port + "/api/brand");
    }
    return urls;
  }

  function load() {
    const urls = sources();
    let i = 0;
    function attempt() {
      if (i >= urls.length) return Promise.resolve(null);
      return fetch(urls[i++], { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((j) => { const b = pick(j); if (b) return b; return attempt(); })
        .catch(() => attempt());
    }
    return attempt().then((b) => {
      if (!b) return null;                     // 外壳没起就用页面里写好的占位文案
      brand = b;
      apply();
      return b;
    });
  }

  window.addEventListener("message", (ev) => {
    const d = ev.data || {};
    if (d.source !== "cp-shell" || d.type !== "cp:brand") return;
    const b = pick(d.brand);
    if (!b) return;
    brand = b;
    apply();
  });

  if (document.body) watchDom();
  else document.addEventListener("DOMContentLoaded", watchDom);
  load();
  return { refresh: load };
}
