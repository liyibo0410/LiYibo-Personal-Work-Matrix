/** 全平台品牌位的形状与默认值。唯一真源是仓库根 `shared/config/brand.json`，
 *  由外壳网关 `GET/POST /api/brand` 读写；这里是各模块侧的镜像默认值，
 *  只用于「取不到配置时页面照样渲染」。
 *
 *  本文件必须保持纯数据：登录页等 React Server Component 也会经由
 *  brand-server.ts 读它，一旦引入 useSyncExternalStore 之类的客户端 API，
 *  Next 会直接拒绝编译。可订阅的 store 与 useBrand() 在 brand-store.ts。 */
export interface CpBrand {
  company: string;
  name_en: string;
  subtitle: string;
  tagline: string;
  version: string;
  /** 用户上传的 logo，图片 dataURL；空则回落到 initials 字母标 */
  logo: string;
  initials: string;
}

export const DEFAULT_BRAND: CpBrand = {
  company: "李奕波个人作品矩阵",
  name_en: "Li Yibo's Personal Portfolio",
  subtitle: "统一平台",
  tagline: "AI 电商运营中台",
  version: "v1.0",
  logo: "",
  initials: "CP",
};

const BRAND_KEYS = Object.keys(DEFAULT_BRAND) as (keyof CpBrand)[];

/** 合并任意来源的品牌对象：brand.json 本体、网关的 {ok, brand}、外壳的 postMessage。
 *  只收字符串字段；logo 只认图片 dataURL，防止把别的内容当图片拼进 DOM。 */
export function mergeBrand(raw: unknown): CpBrand | null {
  if (!raw || typeof raw !== "object") return null;
  const source = raw as Record<string, unknown>;
  // 网关与外壳都把品牌包在 brand 字段里，往下剥一层再判断
  if (typeof source.company !== "string" && source.brand) return mergeBrand(source.brand);
  const merged: CpBrand = { ...DEFAULT_BRAND };
  for (const key of BRAND_KEYS) {
    if (typeof source[key] === "string") merged[key] = source[key] as string;
  }
  if (!/^data:image\//.test(merged.logo)) merged.logo = "";
  return merged;
}
