import { Plus, Store as StoreIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";

const platforms = [
  { label: "抖音电商", value: "douyin" },
  { label: "淘宝", value: "taobao" },
  { label: "天猫", value: "tmall" },
  { label: "拼多多", value: "pinduoduo" },
  { label: "京东", value: "jd" },
  { label: "TikTok Shop", value: "tiktok_shop" },
  { label: "Amazon", value: "amazon" },
  { label: "其他", value: "other" },
] as const;

/** 渲染店铺创建表单。 */
export function StoreCreateForm() {
  return (
    <form action="/stores/create" method="post" className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500 text-white">
          <StoreIcon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-ink-1">新建店铺</h2>
          <p className="text-sm text-ink-3">为多平台商品、SKU 和库存建立归属</p>
        </div>
      </div>

      <Field label="店铺名称" required>
        <Input name="name" required placeholder="例如：抖音旗舰店" />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="平台">
          <Select name="platform" defaultValue="douyin">
            {platforms.map((platform) => (
              <option key={platform.value} value={platform.value}>
                {platform.label}
              </option>
            ))}
          </Select>
        </Field>

        <Field label="负责人">
          <Input name="owner_name" placeholder="运营负责人" />
        </Field>
      </div>

      <Button type="submit" size="lg" className="w-full">
        <Plus className="h-4 w-4" aria-hidden="true" />
        创建店铺
      </Button>
    </form>
  );
}
