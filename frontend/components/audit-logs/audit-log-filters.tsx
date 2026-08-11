"use client";

import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface AuditLogFilterValues {
  action: string;
  resourceType: string;
  actorUserId: string;
}

interface AuditLogFiltersProps {
  values: AuditLogFilterValues;
  onChange: (values: AuditLogFilterValues) => void;
}

export function AuditLogFilters({ values, onChange }: AuditLogFiltersProps) {
  const hasActiveFilters = values.action || values.resourceType || values.actorUserId;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <Input
        placeholder="Filter by action (e.g. user.created)"
        className="max-w-56"
        value={values.action}
        onChange={(e) => onChange({ ...values, action: e.target.value })}
      />
      <Input
        placeholder="Resource type (e.g. user)"
        className="max-w-44"
        value={values.resourceType}
        onChange={(e) => onChange({ ...values, resourceType: e.target.value })}
      />
      <Input
        placeholder="Actor user ID"
        className="max-w-56"
        value={values.actorUserId}
        onChange={(e) => onChange({ ...values, actorUserId: e.target.value })}
      />
      {hasActiveFilters ? (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange({ action: "", resourceType: "", actorUserId: "" })}
        >
          <X className="mr-1 h-3.5 w-3.5" />
          Clear
        </Button>
      ) : null}
    </div>
  );
}
