import { existsSync, readFileSync } from "fs";
import path from "path";

import { DEFAULT_BRAND, mergeBrand, type CpBrand } from "./brand";

const BRAND_REL = path.join("shared", "config", "brand.json");

/** 从 cwd 逐级上溯找仓库根的 brand.json。
 *  dev 时 cwd 是 web/，构建或容器里的起点可能不同，所以不写死层级。 */
function findBrandFile(): string | null {
  let dir = process.cwd();
  for (let depth = 0; depth < 5; depth += 1) {
    const candidate = path.join(dir, BRAND_REL);
    if (existsSync(candidate)) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/** 服务端同步读品牌配置；读不到（比如容器里没挂 shared/）就用默认值，
 *  客户端桥仍会在挂载时从外壳拿到真实品牌。 */
export function readBrandFromDisk(): CpBrand {
  const file = findBrandFile();
  if (!file) return DEFAULT_BRAND;
  try {
    return mergeBrand(JSON.parse(readFileSync(file, "utf-8"))) ?? DEFAULT_BRAND;
  } catch {
    return DEFAULT_BRAND;
  }
}
