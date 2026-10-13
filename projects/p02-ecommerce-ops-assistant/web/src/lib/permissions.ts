import type { UserAccount } from "@/types";

export function canEdit(user: UserAccount | null): boolean {
  return Boolean(user?.permissions.can_edit);
}

export function canManageUsers(user: UserAccount | null): boolean {
  return Boolean(user?.permissions.can_manage_users);
}

export function canConfirmAdActions(user: UserAccount | null): boolean {
  return Boolean(user?.permissions.can_confirm_ad_actions);
}

export function canRead(user: UserAccount | null): boolean {
  return Boolean(user?.permissions.can_read);
}

export function isOwner(user: UserAccount | null): boolean {
  return user?.role === "owner";
}

export function isCs(user: UserAccount | null): boolean {
  return user?.role === "cs";
}

export function roleLabel(role: string): string {
  const map: Record<string, string> = {
    owner: "老板",
    operator: "运营",
    designer: "美工",
    cs: "客服",
  };
  return map[role] ?? role;
}

export function permissionBadges(user: UserAccount): string[] {
  const badges = [roleLabel(user.role)];
  if (user.permissions.can_edit) {
    badges.push("可编辑");
  }
  if (user.permissions.can_manage_users) {
    badges.push("管理用户");
  }
  if (user.permissions.can_confirm_ad_actions) {
    badges.push("确认投放");
  }
  return badges;
}
