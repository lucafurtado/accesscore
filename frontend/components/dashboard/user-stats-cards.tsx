"use client";

import { UserCheck, Users2 } from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { useAsyncData } from "@/hooks/use-async-data";
import { usersApi } from "@/lib/api/users";

export function UserStatsCards() {
  const { data, isLoading, error } = useAsyncData(() => usersApi.stats(), []);

  return (
    <>
      <StatCard
        title="Total Users"
        icon={Users2}
        value={data?.total ?? null}
        isLoading={isLoading}
        hasError={!!error}
      />
      <StatCard
        title="Active Users"
        icon={UserCheck}
        value={data?.active ?? null}
        isLoading={isLoading}
        hasError={!!error}
        subtitle={data ? `${data.total - data.active} inactive` : undefined}
      />
    </>
  );
}
