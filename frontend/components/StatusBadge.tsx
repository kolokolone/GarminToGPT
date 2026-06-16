import type { BadgeState } from "../lib/types";

const LABELS: Partial<Record<BadgeState, string>> = {
  ready: "prêt",
  degraded: "dégradé",
  needs_auth: "auth requise",
  connected: "connecté",
  no_token: "sans token",
  auth_invalid: "token invalide",
  running: "actif",
  starting: "démarrage",
  stopped: "arrêté",
  paused: "pause",
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
