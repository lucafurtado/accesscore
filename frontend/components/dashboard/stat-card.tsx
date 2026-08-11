import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatCardProps {
  title: string;
  icon: LucideIcon;
  value: string | number | null;
  isLoading: boolean;
  hasError: boolean;
  subtitle?: string;
}

export function StatCard({ title, icon: Icon, value, isLoading, hasError, subtitle }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-muted-foreground text-sm font-medium">{title}</CardTitle>
        <Icon className="text-muted-foreground h-4 w-4" aria-hidden="true" />
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-16" />
        ) : hasError ? (
          <p className="text-muted-foreground text-sm">Unavailable</p>
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
        {subtitle && !isLoading && !hasError ? (
          <p className="text-muted-foreground mt-1 text-xs">{subtitle}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
