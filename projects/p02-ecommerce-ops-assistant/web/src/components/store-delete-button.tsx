"use client";

import { Trash2 } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

/** 删除店铺按钮：提交前二次确认，避免误删（店铺删除不可恢复）。 */
export function StoreDeleteButton({
  storeId,
  storeName,
}: {
  storeId: number;
  storeName: string;
}) {
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    const confirmed = window.confirm(
      `确定删除店铺「${storeName}」？\n此操作不可恢复：店铺下的平台账号会一并删除，商品将变为未绑定状态。`,
    );
    if (!confirmed) {
      event.preventDefault();
    }
  }

  return (
    <form
      action={`/stores/${storeId}/delete`}
      method="post"
      onSubmit={handleSubmit}
    >
      <input type="hidden" name="store_id" value={storeId} />
      <button
        type="submit"
        className={buttonVariants({ variant: "danger", size: "sm" })}
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
        删除店铺
      </button>
    </form>
  );
}
