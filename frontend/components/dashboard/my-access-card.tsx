"use client";

import { KeyRound } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "@/hooks/use-session";

export function MyAccessCard() {
  const { user, permissions } = useSession();

  return (
    <Card className="col-span-full lg:col-span-1">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="h-4 w-4" />
          Your Access
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-sm font-medium">{user?.full_name || user?.email}</p>
          <p className="text-muted-foreground text-xs">{user?.email}</p>
        </div>
        <div>
          <p className="text-muted-foreground mb-1.5 text-xs font-medium">
            {permissions.length} effective permission{permissions.length === 1 ? "" : "s"}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {permissions.length === 0 ? (
              <span className="text-muted-foreground text-xs">No permissions assigned.</span>
            ) : (
              permissions
                .slice(0, 8)
                .map((permission) => (
                  <Badge key={permission} variant="outline" className="font-mono text-xs">
                    {permission}
                  </Badge>
                ))
            )}
            {permissions.length > 8 ? (
              <Badge variant="outline" className="text-xs">
                +{permissions.length - 8} more
              </Badge>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
