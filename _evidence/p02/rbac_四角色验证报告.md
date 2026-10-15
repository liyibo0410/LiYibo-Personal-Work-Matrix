# P02 四角色 RBAC 验证报告

> 验证时间：2026-10-12
> 后端版本：P02 v0.2.0（四角色 RBAC 版）

## 1. 角色定义

| 角色 | 枚举值 | 中文 | 权限 |
|---|---|---|---|
| OWNER | `owner` | 老板 | 全权：读/写/管用户/确认投放 |
| OPERATOR | `operator` | 运营 | 读/写/确认投放 |
| DESIGNER | `designer` | 美工 | 读/写（创意相关） |
| CS | `cs` | 客服 | 仅读 |

## 2. 演示账号

| 账号 | 角色 | 密码 |
|---|---|---|
| boss@example.com | owner | Test123456 |
| ops@example.com | operator | Test123456 |
| design@example.com | designer | Test123456 |
| cs@example.com | cs | Test123456 |

## 3. 权限验证结果

### 3.1 各角色权限矩阵

```
boss@example.com  → role: owner
  can_read=True can_edit=True can_manage_users=True can_confirm_ad=True

ops@example.com   → role: operator
  can_read=True can_edit=True can_manage_users=False can_confirm_ad=True

design@example.com → role: designer
  can_read=True can_edit=True can_manage_users=False can_confirm_ad=False

cs@example.com    → role: cs
  can_read=True can_edit=False can_manage_users=False can_confirm_ad=False
```

### 3.2 老板看板 403 证据

```
=== Boss -> /api/v1/dashboard/overview ===
HTTP 200
{
  "total_stores": 3,
  "active_stores": 3,
  "total_products": 6,
  "summary": "经营数据概览（仅老板可见）"
}

=== CS -> /api/v1/dashboard/overview ===
HTTP 403
{"detail": "Owner dashboard access only"}
```

### 3.3 前端导航隔离

- CS 角色登录后，侧边栏自动隐藏「经营总览」「数据导入」「模型配置」
- DESIGNER 角色隐藏「经营总览」
- OWNER/OPERATOR 可见全部导航

## 4. 代码变更清单

| 文件 | 变更 |
|---|---|
| `api/app/models.py` | UserRole 枚举：VIEWER → 新增 DESIGNER + CS |
| `api/app/services/users.py` | ROLE_PERMISSIONS 新增 designer/cs 权限映射 |
| `api/app/api/routes/auth.py` | 新增 `require_owner_permission` 依赖；edit 权限加入 designer |
| `api/app/api/routes/dashboard.py` | 新建老板看板路由，仅 owner 可访问 |
| `api/app/agents/policy.py` | Viewer → CS 角色引用更新 |
| `api/app/main.py` | 注册 dashboard 路由 |
| `web/src/types.ts` | UserRole 类型新增 designer/cs |
| `web/src/lib/permissions.ts` | 新增 isOwner/isCs/roleLabel 辅助函数 |
| `web/src/components/app-shell.tsx` | 导航按角色过滤 + 角色徽章展示 |
| `web/src/app/(app)/layout.tsx` | 传递完整 user 信息（含 role）给 AppShell |
| `web/src/app/(app)/dashboard/page.tsx` | 新建老板看板页面 |
| `web/src/app/(app)/settings/page.tsx` | 角色选项更新为四角色中文标签 |
| `api/scripts/bootstrap_demo_users.py` | 新建四角色演示账号初始化脚本 |
| `api/scripts/run_local_dev.py` | 添加 shared/llm-gateway 到 Python 路径 |
