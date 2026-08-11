"use client";

import { ShieldCheck } from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { useAsyncData } from "@/hooks/use-async-data";
import { rolesApi } from "@/lib/api/roles";

export function RolesStatCard() {
  const { data, isLoading, error } = useAsyncData(() => rolesApi.list(), []);

  return (
    <StatCard
      title="Roles"
      icon={ShieldCheck}
      value={data?.length ?? null}
      isLoading={isLoading}
      hasError={!!error}
    />
  );
}
