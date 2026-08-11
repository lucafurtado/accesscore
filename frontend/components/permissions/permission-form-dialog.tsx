"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { permissionsApi } from "@/lib/api/permissions";

interface PermissionFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

// Remounted (via key, see below) each time the dialog opens, so fields
// always start blank without needing a reset effect.
function PermissionForm({
  onOpenChange,
  onSaved,
}: {
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const [resource, setResource] = useState("");
  const [action, setAction] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await permissionsApi.create({ resource, action, description: description || null });
      toast.success(`Created ${resource}:${action}`);
      onOpenChange(false);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <DialogHeader>
        <DialogTitle>Create permission</DialogTitle>
        <DialogDescription>
          Permissions are identified by a resource:action pair, e.g. <code>users:read</code>.
        </DialogDescription>
      </DialogHeader>

      <div className="grid grid-cols-2 gap-4 py-4">
        <div className="space-y-2">
          <Label htmlFor="perm-resource">Resource</Label>
          <Input
            id="perm-resource"
            placeholder="users"
            required
            value={resource}
            onChange={(e) => setResource(e.target.value)}
            disabled={isSubmitting}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="perm-action">Action</Label>
          <Input
            id="perm-action"
            placeholder="read"
            required
            value={action}
            onChange={(e) => setAction(e.target.value)}
            disabled={isSubmitting}
          />
        </div>
        <div className="col-span-2 space-y-2">
          <Label htmlFor="perm-description">Description</Label>
          <Input
            id="perm-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isSubmitting}
          />
        </div>
        {error ? (
          <p role="alert" className="text-destructive col-span-2 text-sm">
            {error}
          </p>
        ) : null}
      </div>

      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          onClick={() => onOpenChange(false)}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create permission"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function PermissionFormDialog({ open, onOpenChange, onSaved }: PermissionFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <PermissionForm key={String(open)} onOpenChange={onOpenChange} onSaved={onSaved} />
      </DialogContent>
    </Dialog>
  );
}
