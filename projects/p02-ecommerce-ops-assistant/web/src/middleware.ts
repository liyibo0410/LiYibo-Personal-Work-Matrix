import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { normalizeTheme } from "@/lib/theme";

// /api/brand 只吐公开的品牌配置（公司名与 logo，无用户数据），登录页也要能取，
// 否则未登录访客看到的仍是写死的默认名。
const PUBLIC_PATHS = ["/login", "/logout", "/api/brand"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/_next") || pathname.includes(".")) {
    return NextResponse.next();
  }

  const token = request.cookies.get("eo_auth_token")?.value;
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    // 外壳用 ?cp-theme= 下发主题初值，重定向会把它丢掉，导致登录页退回默认深色
    // 与外壳不一致。这里显式带过去（只认 light/dark，避免把任意输入拼进跳转地址）。
    const theme = normalizeTheme(request.nextUrl.searchParams.get("cp-theme"));
    if (theme) {
      loginUrl.searchParams.set("cp-theme", theme);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
