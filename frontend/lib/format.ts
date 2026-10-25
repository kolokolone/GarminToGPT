export function formatDate(value: string | null): string {
  if (!value) return "Jamais vérifié";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatDay(value: string | null): string {
  if (!value) return "Non renseignée";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(
    new Date(`${value}T12:00:00`),
  );
}

export function commandToString(command: string[] | null): string {
  return command?.map((part) => (part.includes(" ") ? `"${part}"` : part)).join(" ") ?? "";
}
