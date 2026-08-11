import { MyAccessCard } from "@/components/dashboard/my-access-card";
import { RecentAuditCard } from "@/components/dashboard/recent-audit-card";
import { RolesStatCard } from "@/components/dashboard/roles-stat-card";
import { UserStatsCards } from "@/components/dashboard/user-stats-cards";
import { PageHeader } from "@/components/common/page-header";
import { PermissionGate } from "@/components/permission-gate";

export default function DashboardPage() {
  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of AccessCore activity and access." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <PermissionGate permission="users:read">
          <UserStatsCards />
        </PermissionGate>
        <PermissionGate permission="roles:read">
          <RolesStatCard />
        </PermissionGate>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <PermissionGate permission="audit_logs:read">
          <RecentAuditCard />
        </PermissionGate>
        <MyAccessCard />
      </div>
    </div>
  );
}
