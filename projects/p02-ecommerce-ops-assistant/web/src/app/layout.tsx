import type { Metadata } from "next";
import { cookies } from "next/headers";

import "./tokens.css";
import "./globals.css";
import { CpBrandBridge } from "@/components/cp-brand-bridge";
import { CpThemeBridge } from "@/components/cp-theme-bridge";
import { readBrandFromDisk } from "@/lib/brand-server";
import { THEME_KEY } from "@/lib/theme";

// 标题里的公司名跟着 brand.json 走：服务端直接读文件，SSR 出去就是最新值，
// 不用等客户端桥回填。
export async function generateMetadata(): Promise<Metadata> {
  const brand = readBrandFromDisk();
  return {
    title: `电商运营助手 · ${brand.company}`,
    description: "AI 单品运营工作台",
  };
}

/** 渲染 RootLayout 组件，集中展示根布局所需的数据、状态和操作入口。 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // 主题从 Cookie 读，服务端就能渲染出正确的 data-theme：外壳传来的 ?cp-theme=
  // 会在 / → /login 的跳转中被丢掉，只靠客户端桥接会先闪一下深色再翻白。
  const theme = (await cookies()).get(THEME_KEY)?.value === "dark" ? "dark" : "light";

  return (
    <html
      lang="zh-CN"
      data-theme={theme}
      className="h-full antialiased"
    >
      <body className="cp-app min-h-full flex flex-col" data-cp-module="p02">
        <CpThemeBridge />
        <CpBrandBridge />
        {children}
      </body>
    </html>
  );
}
