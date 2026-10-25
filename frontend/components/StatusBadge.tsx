import type { BadgeState } from "../lib/types";

const LABELS: Partial<Record<BadgeState, string>> = {
  ready: "prêt",
  degraded: "dégradé",
  needs_auth: "clé requise",
  configured: "configurée",
  valid: "valide",
  expiring_soon: "expire bientôt",
  expired: "expirée",
  not_configured: "non configurée",
  running: "actif",
  starting: "démarrage",
  stopped: "arrêté",
  unhealthy: "instable",
  error: "erreur",
  success: "succès",
  failed: "échec",
  not_run: "non lancé",
  skipped: "ignoré",
};

export function StatusBadge({ state }: { state: BadgeState }) {
  return <span className={`badge badge-${state}`}>{LABELS[state] ?? state}</span>;
}
