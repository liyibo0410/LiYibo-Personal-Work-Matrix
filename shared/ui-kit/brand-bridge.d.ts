/**
 * 构建型模块（P01 客服 / P03 问数）的品牌桥类型声明 —— 实现见同名 brand-bridge.js。
 * 契约与 shared/ui-kit/ui-kit.js 的 CP.applyBrand 一致，页面用
 * data-cp-brand / data-cp-brand-logo-src / data-cp-brand-title 声明绑定节点。
 */
export interface BrandBridgeOptions {
  /** SERVICE_REGISTRY（shared/config/services.json 或其 gateway 子集），用于解析外壳网关端口 */
  registry?: {
    host?: string;
    gateway?: { web_port?: number };
    [key: string]: unknown;
  };
  /** 同源品牌文件地址；模块自身挂了 /shared 时才需要，取不到会自动回落网关 */
  src?: string;
}

export interface BrandBridge {
  /** 重新拉取品牌配置（外壳改了品牌、又不走 postMessage 时可用） */
  refresh: () => Promise<Record<string, string> | null>;
}

export function initBrandBridge(options?: BrandBridgeOptions): BrandBridge;
