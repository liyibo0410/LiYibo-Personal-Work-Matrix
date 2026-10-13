"use client";

import { useEffect } from "react";

import { setBrand } from "@/lib/brand-store";

// 与统一外壳（shell）的品牌桥：外壳 ⚙「品牌设置」保存后写入 shared/config/brand.json，
// 挂载本模块时通过 cp:brand 下发；独立访问本模块时从同源 /api/brand 读同一份文件。
// 与 CpThemeBridge 一样只桥接展示层，不碰本模块自身的 Cookie 认证。

type ShellMessage = { source?: string; type?: string; brand?: unknown };

/** 品牌桥接：外壳改公司名/logo 时同步到本模块。 */
export function CpBrandBridge() {
  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const data = event.data as ShellMessage | null;
      if (!data || data.source !== "cp-shell" || data.type !== "cp:brand") return;
      setBrand(data.brand);
    };
    window.addEventListener("message", onMessage);
    fetch("/api/brand", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((brand) => setBrand(brand))
      .catch(() => {
        /* 读不到就沿用默认值，公司名与 logo 位不影响功能可用性 */
      });
    return () => window.removeEventListener("message", onMessage);
  }, []);

  return null;
}
