"use client";

import Link from "next/link";
import { ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsyncData } from "@/hooks/use-async-data";
import { auditLogsApi } from "@/lib/api/audit-logs";
import { formatDateTime } from "@/lib/format";

export function RecentAuditCard() {
  const { data, isLoading, error } = useAsyncData(
    () => auditLogsApi.list({ limit: 5 }),
    [],
  );

  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Recent Activity</CardTitle>
        <Link href="/dashboard/audit-logs" className="text-primary text-sm hover:underline">
          View all
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <p className="text-muted-foreground text-sm">Unable to load recent activity.</p>
        ) : data && data.items.length > 0 ? (
          <ul className="divide-y">
            {data.items.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-4 py-2.5 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="font-mono text-xs">
                    {entry.action}
                  </Badge>
                  {entry.resource_type ? (
                    <span className="text-muted-foreground">on {entry.resource_type}</span>
                  ) : null}
                </div>
                <time className="text-muted-foreground shrink-0 text-xs" dateTime={entry.created_at}>
                  {formatDateTime(entry.created_at)}
                </time>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-muted-foreground flex flex-col items-center gap-2 py-8 text-sm">
            <ScrollText className="h-6 w-6" />
            No recent activity.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
