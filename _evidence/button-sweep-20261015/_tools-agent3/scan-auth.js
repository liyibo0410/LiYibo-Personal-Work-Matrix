// 扫描 P02 前端 route.ts：找出「GET 后端但没带 authHeaders」的调用（怀疑 401 → 静默失败）
const fs = require("fs"), path = require("path");
const root = path.join("D:\\software\\PycharmProjects\\作品矩阵", "projects", "p02-ecommerce-ops-assistant",
  "web", "src", "app", "(app)", "products", "[id]");
function walk(d, out = []) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name === "route.ts") out.push(p);
  }
  return out;
}
let n = 0;
for (const f of walk(root)) {
  const c = fs.readFileSync(f, "utf8");
  const calls = c.split("fetch(").slice(1).map((s) => s.split(");")[0].replace(/\s+/g, " "));
  const bad = calls.filter((s) => s.includes("API_BASE_URL") && !s.includes("authHeaders") && !s.includes("method:"));
  if (bad.length) {
    n++;
    console.log(path.relative(root, f), "无鉴权GET:", bad.map((x) => x.slice(0, 140)).join(" || "));
  }
}
console.log("suspicious files:", n);