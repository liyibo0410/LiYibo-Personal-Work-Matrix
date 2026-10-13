import { getCurrentUser } from "@/lib/api";
import { getAuthToken } from "@/lib/session";
import { AppShell } from "@/components/app-shell";

/** 工作台区布局：服务端解析当前用户，套深色应用外壳（侧边栏 + 顶部栏）。 */
export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const token = await getAuthToken();
  const currentUser = token ? await getCurrentUser(token) : null;
  return (
    <AppShell
      user={
        currentUser
          ? { display_name: currentUser.display_name, role: currentUser.role }
          : null
      }
    >
      {children}
    </AppShell>
  );
}
