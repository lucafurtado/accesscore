import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDateTime } from "@/lib/format";
import type { AuditLogResponse } from "@/types/api";

interface AuditLogDetailDialogProps {
  entry: AuditLogResponse | null;
  onOpenChange: (open: boolean) => void;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-1.5 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="col-span-2 break-all">{value}</dd>
    </div>
  );
}

export function AuditLogDetailDialog({ entry, onOpenChange }: AuditLogDetailDialogProps) {
  return (
    <Dialog open={!!entry} onOpenChange={(open) => !open && onOpenChange(false)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono text-base">{entry?.action}</DialogTitle>
          <DialogDescription>Audit event details</DialogDescription>
        </DialogHeader>
        {entry ? (
          <dl className="divide-y">
            <Field label="Timestamp" value={formatDateTime(entry.created_at)} />
            <Field label="Actor" value={entry.actor_user_id ?? "System / unauthenticated"} />
            <Field label="Resource type" value={entry.resource_type ?? "—"} />
            <Field label="Resource ID" value={entry.resource_id ?? "—"} />
            <Field label="IP address" value={entry.ip_address ?? "—"} />
            <Field label="User agent" value={entry.user_agent ?? "—"} />
            <Field
              label="Context"
              value={
                entry.context ? (
                  <pre className="bg-muted overflow-x-auto rounded-md p-2 font-mono text-xs">
                    {JSON.stringify(entry.context, null, 2)}
                  </pre>
                ) : (
                  "—"
                )
              }
            />
          </dl>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
