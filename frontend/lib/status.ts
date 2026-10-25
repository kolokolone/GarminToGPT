import type {
  GlobalStatus,
  GarminAuthStatus,
  McpLocalStatus,
  McpStatus,
  TunnelStatus,
  McpLocalState,
  TunnelState,
  GlobalState,
  McpState,
} from "./types";

export function isGarminReady(garmin: GarminAuthStatus): boolean {
  return garmin.configured && (garmin.state === "valid" || garmin.state === "expiring_soon");
}

/* ─── Bridge-level aggregation ─── */

export type BridgeState = "ready" | "cut" | "starting" | "degraded" | "error";

export interface BridgeInfo {
  state: BridgeState;
  badgeLabel: string;
  badgeClass: string;
  title: string;
  message: string;
}

export function computeBridgeInfo(
  garmin: GarminAuthStatus,
  mcpLocal: McpLocalStatus | null,
  tunnel: TunnelStatus,
  globalState: GlobalState,
): BridgeInfo {
  const mcpRunning = mcpLocal?.status === "running";
  const mcpStopped = mcpLocal?.status === "stopped" || mcpLocal === null;
  const mcpStarting = mcpLocal?.status === "starting" || mcpLocal?.status === "stopping";
  const mcpError = mcpLocal?.status === "error";

  const tunnelRunning = tunnel.state === "running";
  const tunnelStarting = tunnel.state === "starting";
  const tunnelStopped = tunnel.state === "stopped";
  const tunnelError = tunnel.state === "error";

  const garminOk = isGarminReady(garmin);

  // Error takes priority
  if (globalState === "error" || mcpError || tunnelError) {
    return {
      state: "error",
      badgeLabel: "ERREUR",
      badgeClass: "badge-bridge-error",
      title: "Pont GarminToGPT à vérifier",
      message: "Un composant bloque l'accès aux outils Garmin.",
    };
  }

  // All good
  if (mcpRunning && tunnelRunning && garminOk) {
    return {
      state: "ready",
      badgeLabel: "PRÊT",
      badgeClass: "badge-bridge-ready",
      title: "Accès Garmin pour ChatGPT activé",
      message: "Tous les services sont opérationnels et le tunnel est prêt.",
    };
  }

  // MCP stopped => cut (regardless of tunnel)
  if (mcpStopped && !mcpStarting) {
    return {
      state: "cut",
      badgeLabel: "COUPÉ",
      badgeClass: "badge-bridge-cut",
      title: "Accès Garmin pour ChatGPT coupé",
      message: "Le MCP local est arrêté. ChatGPT ne peut pas accéder aux outils Garmin.",
    };
  }

  // Tunnel starting
  if (tunnelStarting && !tunnelRunning) {
    return {
      state: "starting",
      badgeLabel: "DÉMARRAGE",
      badgeClass: "badge-bridge-starting",
      title: "Lien ChatGPT en cours de création",
      message: "Le service prépare l'URL publique à utiliser dans ChatGPT.",
    };
  }

  // Partial / degraded
  return {
    state: "degraded",
    badgeLabel: "DÉGRADÉ",
    badgeClass: "badge-bridge-degraded",
    title: "Pont GarminToGPT partiellement prêt",
    message: "Un ou plusieurs composants nécessitent une vérification.",
  };
}

/* ─── Stepper ─── */

export interface StepInfo {
  key: string;
  label: string;
  sublabel: string;
  cssClass: "completed" | "current" | "error" | "degraded" | "";
}

export function computeStepperSteps(
  garmin: GarminAuthStatus,
  mcpLocal: McpLocalStatus | null,
  tunnel: TunnelStatus,
): StepInfo[] {
  const garminOk = isGarminReady(garmin);
  const mcpRunning = mcpLocal?.status === "running";
  const mcpStarting = mcpLocal?.status === "starting" || mcpLocal?.status === "stopping";
  const mcpError = mcpLocal?.status === "error";
  const mcpStopped = mcpLocal?.status === "stopped" || mcpLocal === null;

  const tunnelRunning = tunnel.state === "running";
  const tunnelStarting = tunnel.state === "starting";
  const tunnelError = tunnel.state === "error";

  const connectorReady = tunnelRunning && tunnel.tunnel_id !== null;

  // Step 1: Garmin
  const step1: StepInfo = garminOk
    ? { key: "garmin", label: "Garmin connecté", sublabel: "Clé API Garmin valide", cssClass: "completed" }
    : {
        key: "garmin",
        label: "Garmin connecté",
        sublabel: garmin.configured ? "Clé API à vérifier" : "Aucune clé API",
        cssClass: garmin.configured ? "degraded" : "",
      };

  // Step 2: MCP local
  const step2: StepInfo = mcpRunning
    ? { key: "mcp", label: "MCP local actif", sublabel: "Service local en écoute", cssClass: "completed" }
    : mcpStarting
      ? { key: "mcp", label: "MCP local actif", sublabel: "Démarrage en cours", cssClass: "current" }
      : mcpError
        ? { key: "mcp", label: "MCP local actif", sublabel: "Erreur du service local", cssClass: "error" }
        : { key: "mcp", label: "MCP local actif", sublabel: "Service arrêté", cssClass: "" };

  // Step 3: Tunnel OpenAI
  const step3: StepInfo = tunnelRunning
    ? { key: "tunnel", label: "Tunnel OpenAI actif", sublabel: "Tunnel prêt", cssClass: "completed" }
    : tunnelStarting
      ? { key: "tunnel", label: "Tunnel OpenAI actif", sublabel: "En attente de /readyz", cssClass: "current" }
      : tunnelError
        ? { key: "tunnel", label: "Tunnel OpenAI actif", sublabel: "Erreur du tunnel", cssClass: "error" }
        : { key: "tunnel", label: "Tunnel OpenAI actif", sublabel: "Tunnel arrêté", cssClass: "" };

  // Step 4: ChatGPT connector
  const step4: StepInfo = connectorReady
    ? { key: "url", label: "Tunnel visible dans ChatGPT", sublabel: "Connection: Tunnel + tunnel ID", cssClass: "completed" }
    : tunnelRunning && !tunnel.tunnel_id
      ? { key: "url", label: "Tunnel visible dans ChatGPT", sublabel: "Tunnel ID manquant", cssClass: "degraded" }
      : tunnelStarting
        ? { key: "url", label: "Tunnel visible dans ChatGPT", sublabel: "En attente de /readyz", cssClass: "current" }
        : { key: "url", label: "Tunnel visible dans ChatGPT", sublabel: "Tunnel indisponible", cssClass: "" };

  return [step1, step2, step3, step4];
}

/* ─── Access state (ChatGPT -> Garmin) ─── */

export type AccessState = "active" | "cut" | "starting" | "check";

export interface AccessInfo {
  state: AccessState;
  badgeLabel: string;
  badgeClass: string;
  title: string;
  message: string;
  primaryAction: "start" | "stop" | "disabled" | "retry";
  primaryLabel: string;
  secondaryAction: "restart" | "start" | "none";
  secondaryLabel: string;
}

export function computeAccessInfo(
  mcpLocal: McpLocalStatus | null,
  tunnel: TunnelStatus,
  globalState: GlobalState,
): AccessInfo {
  const mcpRunning = mcpLocal?.status === "running";
  const mcpStopped = mcpLocal?.status === "stopped" || mcpLocal === null;
  const mcpStarting = mcpLocal?.status === "starting";
  const mcpStopping = mcpLocal?.status === "stopping";
  const mcpError = mcpLocal?.status === "error";
  const tunnelRunning = tunnel.state === "running";
  const tunnelStarting = tunnel.state === "starting";

  if (mcpRunning && tunnelRunning) {
    return {
      state: "active",
      badgeLabel: "ACTIF",
      badgeClass: "badge-access-active",
      title: "ChatGPT peut accéder à vos outils Garmin",
      message:
        "Le MCP local et le tunnel OpenAI sont actifs. ChatGPT utilise le tunnel via Connection: Tunnel.",
      primaryAction: "stop",
      primaryLabel: "Couper l'accès ChatGPT",
      secondaryAction: "restart",
      secondaryLabel: "Redémarrer le service local",
    };
  }

  if (mcpRunning && !tunnelRunning) {
    return {
      state: tunnelStarting ? "starting" : "check",
      badgeLabel: tunnelStarting ? "DÉMARRAGE" : "TUNNEL ARRÊTÉ",
      badgeClass: tunnelStarting ? "badge-access-starting" : "badge-access-cut",
      title: tunnelStarting ? "Tunnel OpenAI en cours de démarrage" : "Tunnel OpenAI arrêté",
      message: tunnelStarting
        ? "Le tunnel répond bientôt. En attente de /readyz."
        : "Le MCP local fonctionne, mais le tunnel OpenAI est arrêté. Démarre-le pour que ChatGPT voie le serveur.",
      primaryAction: tunnelStarting ? "disabled" : "start",
      primaryLabel: tunnelStarting ? "Démarrage en cours…" : "Démarrer le tunnel",
      secondaryAction: "none",
      secondaryLabel: "",
    };
  }

  if (mcpStopped && !mcpStarting) {
    const noTunnel = tunnel.state === "stopped" || tunnel.state === "starting";
    return {
      state: "cut",
      badgeLabel: "COUPÉ",
      badgeClass: "badge-access-cut",
      title: "ChatGPT ne peut pas accéder à vos outils Garmin",
      message: noTunnel
        ? "Le service MCP local et le tunnel OpenAI sont arrêtés. Démarre l'accès pour rétablir la connexion."
        : "Le service MCP local est arrêté. Le tunnel OpenAI ne peut pas joindre les outils Garmin.",
      primaryAction: "start",
      primaryLabel: "Activer l'accès ChatGPT",
      secondaryAction: "start",
      secondaryLabel: "Démarrer le service local",
    };
  }

  if (mcpStarting || mcpStopping) {
    return {
      state: "starting",
      badgeLabel: "DÉMARRAGE",
      badgeClass: "badge-access-starting",
      title: "Accès ChatGPT à Garmin en cours",
      message: "Le service local est en cours de démarrage. L'accès sera disponible dans quelques instants.",
      primaryAction: "disabled",
      primaryLabel: "Démarrage en cours…",
      secondaryAction: "none",
      secondaryLabel: "",
    };
  }

  if (mcpError) {
    return {
      state: "check",
      badgeLabel: "À VÉRIFIER",
      badgeClass: "badge-access-check",
      title: "Accès ChatGPT à Garmin à vérifier",
      message: "Le service MCP local a rencontré une erreur. Vérifie les logs pour plus de détails.",
      primaryAction: "retry",
      primaryLabel: "Réessayer",
      secondaryAction: "start",
      secondaryLabel: "Démarrer le service local",
    };
  }

  return {
    state: "check",
    badgeLabel: "À VÉRIFIER",
    badgeClass: "badge-access-check",
    title: "Accès ChatGPT à Garmin à vérifier",
    message: "Impossible de déterminer l'état de l'accès ChatGPT.",
    primaryAction: "start",
    primaryLabel: "Activer l'accès ChatGPT",
    secondaryAction: "start",
    secondaryLabel: "Démarrer le service local",
  };
}

/* ─── Tech card helpers ─── */

export interface TechCardInfo {
  iconClass: string;
  iconLabel: string;
  badgeLabel: string;
  badgeClass: string;
  summary: string;
}

export function getMcpLocalTechInfo(mcpLocal: McpLocalStatus | null): TechCardInfo {
  switch (mcpLocal?.status) {
    case "running":
      return { iconClass: "green", iconLabel: "●", badgeLabel: "ACTIF", badgeClass: "badge-running", summary: "Le service MCP local est en cours d'exécution." };
    case "starting":
    case "stopping":
      return { iconClass: "blue", iconLabel: "◐", badgeLabel: "DÉMARRAGE", badgeClass: "badge-starting", summary: "Le service MCP local démarre." };
    case "error":
      return { iconClass: "red", iconLabel: "✕", badgeLabel: "ERREUR", badgeClass: "badge-error", summary: "Le service MCP local nécessite une vérification." };
    default:
      return { iconClass: "gray", iconLabel: "○", badgeLabel: "ARRÊTÉ", badgeClass: "badge-off", summary: "Le service MCP local est arrêté." };
  }
}

export function getGarminTechInfo(garmin: GarminAuthStatus): TechCardInfo {
  switch (garmin.state) {
    case "valid":
      return { iconClass: "green", iconLabel: "●", badgeLabel: "VALIDE", badgeClass: "badge-connected", summary: "Clé API Garmin valide, accès Garmin Connect opérationnel." };
    case "expiring_soon":
      return { iconClass: "orange", iconLabel: "!", badgeLabel: "EXPIRE BIENTÔT", badgeClass: "badge-degraded", summary: garmin.message };
    case "configured":
      return { iconClass: "blue", iconLabel: "◐", badgeLabel: "CONFIGURÉE", badgeClass: "badge-starting", summary: "Clé API enregistrée, vérification recommandée." };
    case "expired":
      return { iconClass: "red", iconLabel: "✕", badgeLabel: "EXPIRÉE", badgeClass: "badge-error", summary: garmin.message };
    case "error":
      return { iconClass: "red", iconLabel: "✕", badgeLabel: "ERREUR", badgeClass: "badge-error", summary: garmin.message };
    default:
      return { iconClass: "gray", iconLabel: "○", badgeLabel: "NON CONFIGURÉE", badgeClass: "badge-off", summary: "Ajoute une clé API Garmin dans /connexion." };
  }
}

export function getTunnelTechInfo(tunnel: TunnelStatus): TechCardInfo {
  switch (tunnel.state) {
    case "running":
      return { iconClass: "green", iconLabel: "●", badgeLabel: "ACTIF", badgeClass: "badge-running", summary: "Tunnel OpenAI prêt; ChatGPT peut l'utiliser." };
    case "starting":
      return { iconClass: "blue", iconLabel: "◐", badgeLabel: "DÉMARRAGE", badgeClass: "badge-starting", summary: "En attente de /readyz du tunnel OpenAI." };
    case "error":
      return { iconClass: "red", iconLabel: "✕", badgeLabel: "ERREUR", badgeClass: "badge-error", summary: tunnel.last_event ?? "Le tunnel OpenAI a rencontré une erreur." };
    default:
      return { iconClass: "gray", iconLabel: "○", badgeLabel: "ARRÊTÉ", badgeClass: "badge-off", summary: "Le tunnel OpenAI est arrêté." };
  }
}
