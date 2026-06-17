import type {
  GlobalStatus,
  GarminAuthStatus,
  McpLocalStatus,
  McpStatus,
  TunnelStatus,
  McpLocalState,
  TunnelState,
  GlobalState,
  GarminState,
  McpState,
} from "./types";

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
  const tunnelStopped = tunnel.state === "stopped" || tunnel.state === "paused" || tunnel.state === "expired";
  const tunnelError = tunnel.state === "error";

  const garminOk = garmin.token_found && garmin.token_valid;

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
  const garminOk = garmin.token_found && garmin.token_valid;
  const mcpRunning = mcpLocal?.status === "running";
  const mcpStarting = mcpLocal?.status === "starting" || mcpLocal?.status === "stopping";
  const mcpError = mcpLocal?.status === "error";
  const mcpStopped = mcpLocal?.status === "stopped" || mcpLocal === null;

  const tunnelRunning = tunnel.state === "running";
  const tunnelStarting = tunnel.state === "starting";
  const tunnelError = tunnel.state === "error";
  const tunnelStopped = tunnel.state === "stopped" || tunnel.state === "paused" || tunnel.state === "expired";

  const urlReady = tunnelRunning && tunnel.chatgpt_mcp_url !== null;

  // Step 1: Garmin
  const step1: StepInfo = garminOk
    ? { key: "garmin", label: "Garmin connecté", sublabel: "Connexion à Garmin OK", cssClass: "completed" }
    : { key: "garmin", label: "Garmin connecté", sublabel: "Connexion à vérifier", cssClass: garmin.token_found ? "degraded" : "" };

  // Step 2: MCP local
  const step2: StepInfo = mcpRunning
    ? { key: "mcp", label: "MCP local actif", sublabel: "Service local en écoute", cssClass: "completed" }
    : mcpStarting
      ? { key: "mcp", label: "MCP local actif", sublabel: "Démarrage en cours", cssClass: "current" }
      : mcpError
        ? { key: "mcp", label: "MCP local actif", sublabel: "Erreur du service local", cssClass: "error" }
        : { key: "mcp", label: "MCP local actif", sublabel: "Service arrêté", cssClass: "" };

  // Step 3: Tunnel
  const step3: StepInfo = tunnelRunning
    ? { key: "tunnel", label: "Tunnel Cloudflare actif", sublabel: "Tunnel sécurisé opérationnel", cssClass: "completed" }
    : tunnelStarting
      ? { key: "tunnel", label: "Tunnel Cloudflare actif", sublabel: "Tunnel en démarrage", cssClass: "current" }
      : tunnelError
        ? { key: "tunnel", label: "Tunnel Cloudflare actif", sublabel: "Erreur du tunnel", cssClass: "error" }
        : { key: "tunnel", label: "Tunnel Cloudflare actif", sublabel: "Tunnel arrêté", cssClass: "" };

  // Step 4: URL
  const step4: StepInfo = urlReady
    ? { key: "url", label: "URL ChatGPT prête", sublabel: "Lien disponible et prêt à l'emploi", cssClass: "completed" }
    : tunnelRunning && !tunnel.chatgpt_mcp_url
      ? { key: "url", label: "URL ChatGPT prête", sublabel: "Lien en attente", cssClass: "degraded" }
      : tunnelStarting
        ? { key: "url", label: "URL ChatGPT prête", sublabel: "Lien en cours de création", cssClass: "current" }
        : { key: "url", label: "URL ChatGPT prête", sublabel: "URL indisponible", cssClass: "" };

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

  if (mcpRunning) {
    return {
      state: "active",
      badgeLabel: "ACTIF",
      badgeClass: "badge-access-active",
      title: "ChatGPT peut accéder à vos outils Garmin",
      message: "Le MCP local est actif et le tunnel est ouvert. ChatGPT peut utiliser les outils Garmin via l'URL ci-dessous.",
      primaryAction: "stop",
      primaryLabel: "Couper l'accès ChatGPT",
      secondaryAction: "restart",
      secondaryLabel: "Redémarrer le service local",
    };
  }

  if (mcpStopped && !mcpStarting) {
    const noTunnel = tunnelStoppedOrStarting(tunnel) && !tunnelRunning;
    return {
      state: "cut",
      badgeLabel: "COUPÉ",
      badgeClass: "badge-access-cut",
      title: "ChatGPT ne peut pas accéder à vos outils Garmin",
      message: noTunnel
        ? "Le service MCP local et le tunnel sont arrêtés. Démarrez le service local pour rétablir l'accès."
        : "Le service MCP local est arrêté. Même si le tunnel Cloudflare existe encore, les outils Garmin ne sont plus accessibles.",
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
      message: "Le service MCP local a rencontré une erreur. Vérifiez les logs pour plus de détails.",
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

function tunnelStoppedOrStarting(t: TunnelStatus): boolean {
  return ["stopped", "starting", "paused", "expired"].includes(t.state);
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
  if (garmin.token_found && garmin.token_valid) {
    return { iconClass: "green", iconLabel: "●", badgeLabel: "CONNECTÉ", badgeClass: "badge-connected", summary: "Connexion à Garmin établie et valide." };
  }
  if (!garmin.token_found) {
    return { iconClass: "gray", iconLabel: "○", badgeLabel: "NON CONNECTÉ", badgeClass: "badge-off", summary: "Connexion Garmin à vérifier." };
  }
  if (garmin.state === "auth_invalid" || garmin.state === "reauth_required") {
    return { iconClass: "orange", iconLabel: "!", badgeLabel: "À VÉRIFIER", badgeClass: "badge-degraded", summary: "La connexion Garmin nécessite une nouvelle authentification." };
  }
  return { iconClass: "red", iconLabel: "✕", badgeLabel: "ERREUR", badgeClass: "badge-error", summary: "La connexion Garmin nécessite une nouvelle authentification." };
}

export function getTunnelTechInfo(tunnel: TunnelStatus): TechCardInfo {
  switch (tunnel.state) {
    case "running":
      return { iconClass: "green", iconLabel: "●", badgeLabel: "ACTIF", badgeClass: "badge-running", summary: "Le tunnel sécurisé est opérationnel." };
    case "starting":
      return { iconClass: "blue", iconLabel: "◐", badgeLabel: "DÉMARRAGE", badgeClass: "badge-starting", summary: "Le tunnel est en cours de démarrage." };
    case "paused":
      return { iconClass: "orange", iconLabel: "‖", badgeLabel: "PAUSE", badgeClass: "badge-paused", summary: "Le tunnel est en pause." };
    case "error":
      return { iconClass: "red", iconLabel: "✕", badgeLabel: "ERREUR", badgeClass: "badge-error", summary: "Le tunnel a rencontré une erreur." };
    default:
      return { iconClass: "gray", iconLabel: "○", badgeLabel: "ARRÊTÉ", badgeClass: "badge-off", summary: "Le tunnel est arrêté." };
  }
}

/* ─── URL helpers ─── */

const TRYCLOUDFLARE_MCP_URL = /^https:\/\/[a-zA-Z0-9.-]+\.trycloudflare\.com\/mcp\/?$/;

export function isValidUrl(url: string | null): url is string {
  return url !== null && TRYCLOUDFLARE_MCP_URL.test(url);
}
