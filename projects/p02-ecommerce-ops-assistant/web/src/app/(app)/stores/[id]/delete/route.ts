import { redirect } from "next/navigation";

import { API_BASE_URL } from "@/lib/api";
import { authHeaders } from "@/lib/session";

/** 处理 stores/删除请求：读取表单中的 store_id，调用后端 DELETE 接口，并按结果重定向。 */
export async function POST(request: Request) {
  const formData = await request.formData();
  const storeId = formData.get("store_id");
  if (!storeId || typeof storeId !== "string") {
    redirect("/");
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/stores/${storeId}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });

  if (!response.ok) {
    redirect("/?store=delete_failed");
  }

  redirect("/?store=deleted");
}
