export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatDateTimeOrNever(iso: string | null): string {
  return iso ? formatDateTime(iso) : "Never";
}

export function initialsFor(name: string): string {
  return name.trim().slice(0, 1).toUpperCase() || "?";
}
