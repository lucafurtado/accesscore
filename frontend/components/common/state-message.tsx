import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Inbox } from "lucide-react";

import { Button } from "@/components/ui/button";

interface StateMessageProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

function StateMessage({ icon: Icon = Inbox, title, description, action }: StateMessageProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-16 text-center">
      <Icon className="text-muted-foreground mb-2 h-8 w-8" aria-hidden="true" />
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="text-muted-foreground max-w-sm text-sm">{description}</p> : null}
      {action ? (
        <Button variant="outline" size="sm" className="mt-2" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState(props: Omit<StateMessageProps, "icon"> & { icon?: LucideIcon }) {
  return <StateMessage icon={Inbox} {...props} />;
}

export function ErrorState({
  description = "Something went wrong while loading this data.",
  onRetry,
  ...props
}: Omit<StateMessageProps, "icon" | "action"> & { onRetry?: () => void }) {
  return (
    <StateMessage
      icon={AlertTriangle}
      description={description}
      action={onRetry ? { label: "Try again", onClick: onRetry } : undefined}
      {...props}
    />
  );
}
