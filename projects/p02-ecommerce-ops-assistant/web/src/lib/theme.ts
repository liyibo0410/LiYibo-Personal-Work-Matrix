/** 主题令牌的键名与取值：外壳与各模块共用同一套约定。
 *  放在中立模块里，服务端组件（layout/middleware）与客户端桥都能引用，
 *  不必从 "use client" 文件里导正常量。 */
export const THEME_KEY = "cp_theme_v2";

export type Theme = "light" | "dark";

/** 只认 light / dark，其余一律回 null，避免把任意输入拼进 cookie 或 data-theme。 */
export function normalizeTheme(value: string | null | undefined): Theme | null {
  return value === "light" || value === "dark" ? value : null;
}
