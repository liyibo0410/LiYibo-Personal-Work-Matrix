"use client";

import { useEffect } from "react";

import { normalizeTheme, THEME_KEY, type Theme } from "@/lib/theme";

// 与统一外壳（shell）的主题桥：iframe 内接收 cp-shell 下发的 cp:theme 并持久化，
// 挂载后上报 cp:ready 供 shell 识别。认证仍走 P02 自身的 httpOnly Cookie（完整 RBAC），
// 故此处只桥接主题，不接管令牌，避免半成品逻辑。

function themeFromUrl(): Theme | null {
  const m = /[?&]cp-theme=(light|dark)/.exec(window.location.search);
  return m ? normalizeTheme(m[1]) : null;
}

// 主题额外落一份非 HttpOnly 的 Cookie：中间件在 / → /login 跳转时会丢掉 query，
// 只有 Cookie 能让服务端渲染直接出正确主题（否则先闪一下深色再翻白）。
function persistTheme(value: Theme) {
  try {
    localStorage.setItem(THEME_KEY, value);
  } catch {
    /* 隐私模式下忽略 */
  }
  try {
    document.cookie = `${THEME_KEY}=${encodeURIComponent(value)}; path=/; max-age=${7 * 24 * 3600}; samesite=lax`;
  } catch {
    /* 忽略 */
  }
}

function readPersistedTheme(): Theme | null {
  try {
    const m = new RegExp("(?:^|; )" + THEME_KEY + "=([^;]*)").exec(document.cookie);
    if (m) return normalizeTheme(decodeURIComponent(m[1]));
  } catch {
    /* 忽略 */
  }
  try {
    return normalizeTheme(localStorage.getItem(THEME_KEY));
  } catch {
    return null;
  }
}

function applyTheme(theme: string) {
  const value = normalizeTheme(theme) ?? "light";
  document.documentElement.setAttribute("data-theme", value);
  persistTheme(value);
}

/** 主题桥接：外壳切换深浅色时同步到本模块。 */
export function CpThemeBridge() {
  useEffect(() => {
    const inFrame = window.self !== window.top;
    applyTheme(themeFromUrl() || readPersistedTheme() || "light");
    if (!inFrame) return;

    try {
      window.parent.postMessage(
        { source: "cp-module", type: "cp:ready", module: "p02", title: document.title },
        "*",
      );
    } catch {
      /* 跨域限制时忽略 */
    }

    const onMessage = (event: MessageEvent) => {
      const data = event.data as { source?: string; type?: string; theme?: string } | null;
      if (!data || data.source !== "cp-shell") return;
      if (data.type === "cp:theme") applyTheme(data.theme || "light");
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  return null;
}
