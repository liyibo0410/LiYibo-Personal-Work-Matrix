// 构建前把仓库共享设计令牌复制到 Next 项目内，供 globals.css 引入。
// Next 不允许 import 项目根（web/）之外的文件，因此采用「构建期复制」实现单一真源：
// 唯一真源始终是 ../../../shared/ui-kit/tokens.css，本脚本只是把它同步进来。
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url)); // web/scripts
const repoRoot = join(here, "..", "..", "..", ".."); // web → p02 → projects → root
const src = join(repoRoot, "shared", "ui-kit", "tokens.css");
const out = join(here, "..", "src", "app", "tokens.css");

const banner =
  "/* GENERATED — 请勿直接编辑。构建期由 scripts/copy-tokens.mjs 从\n" +
  "   shared/ui-kit/tokens.css 复制同步（单一真源在仓库根）。 */\n";

const body = readFileSync(src, "utf8");
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, banner + body, "utf8");
console.log("[copy-tokens] synced shared design tokens ->", out);
