/** 轻量 className 合并工具：过滤假值后用空格连接。 */
export function cn(
  ...parts: Array<string | false | null | undefined>
): string {
  return parts.filter(Boolean).join(" ");
}
