import { NextResponse } from "next/server";

import { readBrandFromDisk } from "@/lib/brand-server";

/** 品牌配置只读接口：外壳 ⚙ 保存后写的是同一份 shared/config/brand.json，
 *  这里不落缓存，刷新本模块就能看到最新公司名与 logo。 */
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(readBrandFromDisk());
}
