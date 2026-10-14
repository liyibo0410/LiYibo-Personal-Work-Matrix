import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/lib/api";
import { authHeaders } from "@/lib/session";

/** 处理商品删除提交：确认后调用后端 DELETE，按结果回跳商品池并带提示。 */
export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  // id 会拼进后端 URL，只接受纯数字，避免把任意字符串送进请求路径。
  if (!/^\d+$/.test(id)) {
    redirect("/products");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/products/${id}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });

  if (!response.ok) {
    redirect("/products?product=delete_failed");
  }

  redirect("/products?product=deleted");
}
