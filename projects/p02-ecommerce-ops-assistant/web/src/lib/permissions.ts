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

export function permissionBadges(user: UserAccount): string[] {
  const badges = ["可查看"];
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
