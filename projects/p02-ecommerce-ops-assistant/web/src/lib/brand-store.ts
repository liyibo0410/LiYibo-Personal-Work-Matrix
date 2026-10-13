import { useSyncExternalStore } from "react";

import { DEFAULT_BRAND, mergeBrand, type CpBrand } from "./brand";

/** 品牌位的客户端 store：外壳 ⚙ 保存后通过 postMessage(cp:brand) 或本模块
 *  `/api/brand` 刷新到这里，订阅了 `useBrand()` 的组件即时重绘。
 *
 *  只允许客户端组件引用（这里用了 useSyncExternalStore）；服务端要读磁盘请走
 *  brand-server.ts，它只依赖纯数据模块 brand.ts。 */

let current: CpBrand = DEFAULT_BRAND;
const listeners = new Set<() => void>();

/** 写入新品牌并通知订阅者；无效数据返回 false，页面继续用上一份。 */
export function setBrand(raw: unknown): boolean {
  const merged = mergeBrand(raw);
  if (!merged) return false;
  current = merged;
  listeners.forEach((notify) => notify());
  return true;
}

export function getBrand(): CpBrand {
  return current;
}

function subscribe(notify: () => void): () => void {
  listeners.add(notify);
  return () => {
    listeners.delete(notify);
  };
}

// 服务端快照恒为默认值：SSR 出的 HTML 与水合首帧一致，品牌在挂载后才刷新，
// 不会因为读到磁盘文件而出现 hydration 文本不匹配。
function getServerSnapshot(): CpBrand {
  return DEFAULT_BRAND;
}

/** 组件里读当前品牌（外壳改了公司名或 logo 会即时刷新）。 */
export function useBrand(): CpBrand {
  return useSyncExternalStore(subscribe, getBrand, getServerSnapshot);
}
