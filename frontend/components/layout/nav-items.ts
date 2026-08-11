import type { LucideIcon } from "lucide-react";
import { LayoutDashboard, ScrollText, ShieldCheck, Users2, KeyRound } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** null = visible to every authenticated user, no gate needed. */
  permission: string | null;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, permission: null },
  { href: "/dashboard/users", label: "Users", icon: Users2, permission: "users:read" },
  { href: "/dashboard/roles", label: "Roles", icon: ShieldCheck, permission: "roles:read" },
  {
    href: "/dashboard/permissions",
    label: "Permissions",
    icon: KeyRound,
    permission: "permissions:read",
  },
  {
    href: "/dashboard/audit-logs",
    label: "Audit Logs",
    icon: ScrollText,
    permission: "audit_logs:read",
  },
];
