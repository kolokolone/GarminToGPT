"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "../components/AppHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { LogsModal } from "../components/LogsModal";
import { ServiceStatusCard } from "../components/ServiceStatusCard";
import { api } from "../lib/api";
import {
  computeAccessInfo,
  computeBridgeInfo,
  computeStepperSteps,
  isValidUrl,
} from "../lib/status";
import type {
  GlobalStatus,
  LogResult,
  McpLocalStatus,
  TunnelStatus,
} from "../lib/types";

const INITIAL_TUNNEL: TunnelStatus = {
  state: "starting",
  mode: "quick",
  public_url: null,
  chatgpt_mcp_url: null,
  pid: null,
  last_event: null,
  process: { status: "starting", pid: null, message: "" },
};

export default function HomePage() {
  const [status, setStatus] = useState<GlobalStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState(false);
  const [copied, setCopied] = useState(false);
  const [logsService, setLogsService] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogResult | null>(null);
  const [confirm, setConfirm] = useState<null | "stopTunnel" | "disconnect" | "regenerate">(null);
  const [mcpLocal, setMcpLocal] = useState<McpLocalStatus | null>(null);
  const [mcpLoading, setMcpLoading] = useState(false);

  /* ── Data fetching ── */

  const refresh = useCallback(async () => {
    try {
      setStatus(await api.status());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }, []);

  const refreshMcp = useCallback(async () => {
    try {
      setMcpLocal(await api.mcpLocalStatus());
    } catch {
      // silencieux pendant le polling
    }
  }, []);

  useEffect(() => {
    void refresh();
    void refreshMcp();
  }, [refresh, refreshMcp]);

  // Tunnel polling 3s (max 60s) while tunnel is starting
  const tunnelState = status?.tunnel.state ?? "stopped";
  useEffect(() => {
    if (tunnelState !== "starting") return;
    const interval = setInterval(async () => {
      try { setStatus(await api.status()); } catch { /* silencieux */ }
    }, 3000);
    const timeout = setTimeout(() => clearInterval(interval), 60000);
    return () => { clearInterval(interval); clearTimeout(timeout); };
  }, [tunnelState]);

  // MCP polling every 3s
  useEffect(() => {
    const interval = setInterval(async () => { await refreshMcp(); }, 3000);
    return () => clearInterval(interval);
  }, [refreshMcp]);

  /* ── Action handlers ── */

  const runAction = useCallback(async (action: () => Promise<unknown>) => {
    setLoadingAction(true);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action impossible");
    } finally {
      setLoadingAction(false);
      setConfirm(null);
    }
  }, [refresh]);

  const runMcpAction = useCallback(
    async (action: () => Promise<McpLocalStatus>, transientStatus: McpLocalStatus["status"]) => {
      setMcpLoading(true);
      setMcpLocal((prev) => prev ? { ...prev, status: transientStatus } : prev);
      try {
        const result = await action();
        setMcpLocal(result);
        await refresh();
      } catch (err) {
        setMcpLocal((prev) =>
          prev ? { ...prev, status: "error", last_error: err instanceof Error ? err.message : "Action MCP impossible" } : prev
        );
        setError(err instanceof Error ? err.message : "Action MCP impossible");
      } finally {
        setMcpLoading(false);
      }
    },
    [refresh],
  );

  const openLogs = useCallback(async (service: string) => {
    setLogsService(service);
    setError(null);
    try {
      setLogs(await api.logs(service));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible de charger les logs");
    }
  }, []);

  const handleCopy = useCallback(() => {
    if (status?.tunnel.chatgpt_mcp_url) {
      void navigator.clipboard?.writeText(status.tunnel.chatgpt_mcp_url);
      setCopied(true);
    }
  }, [status]);

  /* ── Derived state ── */

  const bridgeInfo = status
    ? computeBridgeInfo(status.garmin, mcpLocal, status.tunnel, status.state)
    : null;
  const stepperSteps = status
    ? computeStepperSteps(status.garmin, mcpLocal, status.tunnel)
    : [];
  const accessInfo = status
    ? computeAccessInfo(mcpLocal, status.tunnel, status.state)
    : null;

  const urlValid = status ? isValidUrl(status.tunnel.chatgpt_mcp_url) : false;
  const tunnel = status?.tunnel ?? INITIAL_TUNNEL;

  /* ── Helpers for URL display state ── */

  const urlDisplayText = (() => {
    if (urlValid) return tunnel.chatgpt_mcp_url!;
    if (tunnel.state === "starting") return "Lien en cours de création…";
    if (tunnel.state === "paused") return "Tunnel mis en pause";
    if (tunnel.state === "running" && !tunnel.chatgpt_mcp_url) return "Lien en attente…";
    return "Tunnel Cloudflare non actif";
  })();

  const urlBadgeLabel = (() => {
    if (urlValid) return "ACTIVE";
    if (tunnel.state === "starting") return "CRÉATION";
    if (tunnel.state === "running") return "ATTENTE";
    if (tunnel.state === "error") return "ERREUR";
    return "INDISPONIBLE";
  })();

  const urlBadgeClass = (() => {
    if (urlValid) return "badge-bridge-ready";
    if (tunnel.state === "starting") return "badge-bridge-starting";
    if (tunnel.state === "error") return "badge-bridge-error";
    return "badge-off";
  })();

  /* ── Loading state ── */

  if (!status) {
    return (
      <main className="shell">
        <AppHeader />
        <section className="card card-primary">
          <p className="section-label">ÉTAT DU PONT</p>
          <p style={{ color: "var(--muted)" }}>Chargement de l&rsquo;état local…</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      {/* ── 1. Header compact ── */}
      <AppHeader version={status.version} />

      {/* ── 2. Bridge Status Card with Stepper ── */}
      <section className="card card-primary bridge-card">
        <p className="section-label">ÉTAT DU PONT</p>
        <div className="bridge-header">
          <div style={{ flex: 1 }}>
            <h2 className="bridge-title">{bridgeInfo?.title ?? "Chargement…"}</h2>
            <p className="bridge-message">{bridgeInfo?.message ?? ""}</p>
          </div>
          {bridgeInfo ? (
            <span className={`badge badge-pill ${bridgeInfo.badgeClass}`}>
              {bridgeInfo.badgeLabel}
            </span>
          ) : null}
        </div>

        {/* Horizontal stepper (desktop) */}
        <ul className="stepper" aria-label="Progression du pont">
          {stepperSteps.map((step, idx) => (
            <li key={step.key} className={`stepper-step ${step.cssClass}`}>
              <span className="stepper-circle">
                {step.cssClass === "completed" ? "✓" : idx + 1}
              </span>
              <span className="stepper-label">{step.label}</span>
              <span className="stepper-sublabel">{step.sublabel}</span>
            </li>
          ))}
        </ul>

        {/* Vertical stepper (mobile) */}
        <ul className="stepper-vertical" aria-label="Progression du pont">
          {stepperSteps.map((step, idx) => (
            <li key={step.key} className={`stepper-step ${step.cssClass}`}>
              <span className="stepper-circle">
                {step.cssClass === "completed" ? "✓" : idx + 1}
              </span>
              <div>
                <span className="stepper-label">{step.label}</span>
                <span className="stepper-sublabel">{step.sublabel}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Error banner */}
      {error ? <p className="error-box">{error}</p> : null}

      {/* ── 3. Access ChatGPT Card ── */}
      {accessInfo ? (
        <section className="card card-primary access-card">
          <p className="section-label">ACCÈS CHATGPT À GARMIN</p>
          <div className="access-header">
            <div style={{ flex: 1 }}>
              <h2 className="access-title">{accessInfo.title}</h2>
              <p className="access-message">{accessInfo.message}</p>
            </div>
            <span className={`badge badge-pill ${accessInfo.badgeClass}`}>
              {accessInfo.badgeLabel}
            </span>
          </div>

          {/* Info callout */}
          <div className="info-callout" style={{ marginTop: "var(--space-3)" }}>
            <span className="info-callout-icon">ℹ</span>
            <span>
              {accessInfo.state === "active"
                ? "L'accès est actif. Coupez-le immédiatement après utilisation."
                : "Quand le MCP local est arrêté, ChatGPT ne peut plus accéder aux outils Garmin."}
            </span>
          </div>

          {/* Action buttons */}
          <div className="action-bar" style={{ marginTop: "var(--space-3)" }}>
            {accessInfo.primaryAction === "stop" ? (
              <button className="danger-lg" onClick={() => runMcpAction(api.stopMcp, "stopping")} disabled={mcpLoading}>
                {mcpLoading ? <span className="spinner" aria-hidden="true" /> : null}
                {accessInfo.primaryLabel}
              </button>
            ) : null}
            {accessInfo.primaryAction === "start" ? (
              <button className="primary-green" onClick={() => runMcpAction(api.startMcp, "starting")} disabled={mcpLoading}>
                {mcpLoading ? <span className="spinner" aria-hidden="true" /> : null}
                {accessInfo.primaryLabel}
              </button>
            ) : null}
            {accessInfo.primaryAction === "disabled" ? (
              <button disabled>
                <span className="spinner" aria-hidden="true" />
                {accessInfo.primaryLabel}
              </button>
            ) : null}
            {accessInfo.primaryAction === "retry" ? (
              <button className="primary-green" onClick={() => runMcpAction(api.startMcp, "starting")} disabled={mcpLoading}>
                {mcpLoading ? <span className="spinner" aria-hidden="true" /> : null}
                {accessInfo.primaryLabel}
              </button>
            ) : null}

            {/* Secondary action */}
            {accessInfo.secondaryAction === "restart" ? (
              <button className="secondary" onClick={() => runMcpAction(api.restartMcp, "starting")} disabled={mcpLoading}>
                {accessInfo.secondaryLabel}
              </button>
            ) : null}
            {accessInfo.secondaryAction === "start" && accessInfo.primaryAction !== "start" ? (
              <button className="secondary" onClick={() => runMcpAction(api.startMcp, "starting")} disabled={mcpLoading}>
                {accessInfo.secondaryLabel}
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      {/* ── 4. URL Card ── */}
      <section className="card">
        <p className="section-label">URL À COLLER DANS CHATGPT</p>
        <div className="row wrap" style={{ gap: "var(--space-2)" }}>
          <div className="url-field" style={{ flex: 1, minWidth: 0 }}>
            {urlValid ? (
              <code>{tunnel.chatgpt_mcp_url}</code>
            ) : (
              <span className="url-field-placeholder">{urlDisplayText}</span>
            )}
          </div>
          <div className="row" style={{ gap: "var(--space-1)", flexShrink: 0 }}>
            <button onClick={handleCopy} disabled={!urlValid}>
              {copied ? "Copié" : "Copier"}
            </button>
            <button className="secondary" onClick={() => setConfirm("regenerate")} disabled={loadingAction}>
              Régénérer le lien
            </button>
          </div>
          <span className={`badge badge-pill ${urlBadgeClass}`}>{urlBadgeLabel}</span>
        </div>
      </section>

      {/* ── 5. Tech Cards Grid ── */}
      <section className="grid-3">
        <ServiceStatusCard
          title="Service local"
          kind="mcp"
          data={status.mcp}
          mcpLocal={mcpLocal}
          onLogs={() => void openLogs("mcp")}
        />
        <ServiceStatusCard
          title="Garmin MCP"
          kind="garmin"
          data={status.garmin}
          onLogs={() => void openLogs("auth")}
        />
        <ServiceStatusCard
          title="Cloudflare Tunnel"
          kind="tunnel"
          data={status.tunnel}
          onLogs={() => void openLogs("cloudflare")}
        />
      </section>

      {/* ── 6. Secondary Action Bar ── */}
      <div className="action-bar-center">
        <button className="ghost" onClick={() => void openLogs("mcp")}>
          Afficher les logs
        </button>
        <a className="button-link ghost" href="/tests">
          Ouvrir les tests
        </a>
        <button className="ghost" onClick={() => void refresh()} disabled={loadingAction}>
          Rafraîchir
        </button>
      </div>

      {/* ── Modals ── */}
      <LogsModal
        service={logsService}
        logs={logs}
        error={logsService ? error : null}
        onClose={() => { setLogsService(null); setError(null); }}
        onRefresh={() => logsService && void openLogs(logsService)}
      />
      <ConfirmDialog
        open={confirm !== null}
        title="Confirmation requise"
        message={
          confirm === "disconnect"
            ? "Voulez-vous vraiment vous déconnecter ? Les tokens Garmin locaux seront supprimés."
            : "Cette action modifie l'état du tunnel Cloudflare public."
        }
        confirmLabel="Confirmer"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm === "stopTunnel") void runAction(api.stopTunnel);
          if (confirm === "disconnect") void runAction(api.disconnect);
          if (confirm === "regenerate") void runAction(api.regenerateTunnel);
        }}
      />
    </main>
  );
}
