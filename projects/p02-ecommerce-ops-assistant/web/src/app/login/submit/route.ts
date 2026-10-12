import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/lib/api";
import { AUTH_COOKIE_NAME } from "@/lib/session";

/** 处理登录/提交请求：读取表单和路径参数，调用后端 API，并按结果响应或重定向。 */
export async function POST(request: Request) {
  const formData = await request.formData();

  let response: Response;
  try {
    // 登录表单由服务端 route 转发给后端，成功后只把 token 写入 httpOnly cookie。
    response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: formData.get("email")?.toString() ?? "",
        password: formData.get("password")?.toString() ?? "",
      }),
    });
  } catch (error) {
    // 后端未启动/网络不通时，fetch 会抛异常；打日志并回到登录页提示，而不是裸 500。
    console.error("[login] 无法连接后端 API：", API_BASE_URL, error);
    redirect("/login?error=backend");
  }

  if (!response.ok) {
    redirect("/login?error=1");
  }

  const payload = (await response.json()) as { access_token: string };
  const cookieStore = await cookies();
  // httpOnly cookie 降低 token 被客户端脚本读取的风险；后续 API 调用由服务端统一附加 Authorization。
  cookieStore.set(AUTH_COOKIE_NAME, payload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
  });

  redirect("/");
}
