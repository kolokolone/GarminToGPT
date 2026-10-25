"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppHeader } from "../components/AppHeader";
import { LogsModal } from "../components/LogsModal";
import { ServiceStatusCard } from "../components/ServiceStatusCard";
import { api } from "../lib/api";
import {
  computeAccessInfo,
  computeBridgeInfo,
  computeStepperSteps,
  isGarminReady,
} from "../lib/status";
import type {
  GlobalStatus,
  LogResult,
  McpLocalStatus,
  TunnelStatus,
} from "../lib/types";

const INITIAL_TUNNEL: TunnelStatus = {
  state: "starting",
  provider: "openai",
  configured: false,
  tunnel_id: null,
  api_key_configured: false,
  binary_installed: false,
  binary_version: null,
  ready: false,
  health_status: null,
  health_url: null,
  ui_url: null,
  connector_url: "https://chatgpt.com/#settings/Connectors",
  pid: null,
  last_event: null,
  process: { status: "starting", pid: null, message: "" },
};

export default function HomePage() {
  const router = useRouter();
  const [status, setStatus] = useState<GlobalStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState(false);
  const [copied, setCopied] = useState(false);
  const [logsService, setLogsService] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogResult | null>(null);
  const [mcpLocal, setMcpLocal] = useState<McpLocalStatus | null>(null);
  const [mcpLoading, setMcpLoading] = useState(false);

  /* ── Data fetching ── */

  const refresh = useCallback(async () => {
    try {
      const s = await api.status();
      setStatus(s);
      setError(null);
      if (isGarminReady(s.garmin)) {
        setNotice(null);
      }
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

  // No key means the bridge cannot work: show the message briefly, then
  // send the user to the key management page.
  useEffect(() => {
    if (!status || status.garmin.configured) return;
    const timer = setTimeout(() => router.replace("/connexion"), 2500);
    return () => clearTimeout(timer);
  }, [status, router]);

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
      const result = (await action()) as { ok?: boolean; message?: string } | undefined;
      await refresh();
      if (result && result.ok === false) {
        setError(result.message ?? "Action tunnel impossible");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action impossible");
    } finally {
      setLoadingAction(false);
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

  const runAccessStart = useCallback(async () => {
    setMcpLoading(true);
    setMcpLocal((prev) => prev ? { ...prev, status: "starting" } : prev);
    try {
      const result = await api.startAccess();
      setStatus(result);
      // Notification métier selon l'état Garmin
      if (result.state === "needs_auth" || !result.garmin.configured) {
        setNotice(
          "Aucune clé API Garmin. Le pont MCP ne peut pas démarrer. " +
          "Ouvre /connexion pour connecter ton compte."
        );
      } else if (result.garmin.state === "expired") {
        setNotice(
          "La clé API Garmin est expirée ou invalide. Crée une nouvelle clé dans " +
          "Garmin Connect puis mets-la à jour dans /connexion."
        );
      } else if (result.garmin.state === "error") {
        setNotice(
          "La vérification de la clé API Garmin a échoué. Vérifie ta connexion réseau " +
          "puis réessaie depuis /connexion."
        );
      } else if (!result.tunnel.configured) {
        setNotice(
          "Tunnel OpenAI non configuré. Ouvre /tunnel pour renseigner le tunnel ID " +
          "et la runtime API key."
        );
      } else if (result.tunnel.state === "error") {
        setNotice(
          result.tunnel.last_event ??
          "Le tunnel OpenAI a échoué. Vérifie sa configuration dans /tunnel."
        );
      } else {
        setNotice(null);
      }
      await refreshMcp();
    } catch (err) {
      setMcpLocal((prev) =>
        prev ? { ...prev, status: "error", last_error: err instanceof Error ? err.message : "Action impossible" } : prev
      );
      setError(err instanceof Error ? err.message : "Action impossible");
    } finally {
      setMcpLoading(false);
    }
  }, [refreshMcp]);

  const runAccessStop = useCallback(async () => {
    setMcpLoading(true);
    setMcpLocal((prev) => prev ? { ...prev, status: "stopping" } : prev);
    try {
      const result = await api.stopAccess();
      setStatus(result);
      await refreshMcp();
    } catch (err) {
      setMcpLocal((prev) =>
        prev ? { ...prev, status: "error", last_error: err instanceof Error ? err.message : "Action impossible" } : prev
      );
      setError(err instanceof Error ? err.message : "Action impossible");
    } finally {
      setMcpLoading(false);
    }
  }, [refreshMcp]);

  const openLogs = useCallback(async (service: string) => {
    setLogsService(service);
    setLogs(null);
    setError(null);
    try {
      setLogs(await api.logs(service));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible de charger les logs");
    }
  }, []);

  const handleCopy = useCallback(() => {
    if (status?.tunnel.tunnel_id) {
      void navigator.clipboard?.writeText(status.tunnel.tunnel_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
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

  const tunnel = status?.tunnel ?? INITIAL_TUNNEL;
  const tunnelBadgeLabel = tunnel.ready
    ? "ACTIF"
    : tunnel.state === "starting"
      ? "DÉMARRAGE"
      : tunnel.state === "error"
        ? "ERREUR"
        : "ARRÊTÉ";
  const tunnelBadgeClass = tunnel.ready
    ? "badge-bridge-ready"
    : tunnel.state === "starting"
      ? "badge-bridge-starting"
      : tunnel.state === "error"
        ? "badge-bridge-error"
        : "badge-off";

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

      {/* Notice métier (clé absente, expirée ou erreur de vérification) */}
      {!status.garmin.configured ? (
        <p className="warning-box">
          Aucune clé API Garmin configurée. Redirection vers{" "}
          <a href="/connexion">/connexion</a> pour connecter ton compte…
        </p>
      ) : null}
      {notice ? <p className="warning-box">{notice}</p> : null}

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
              <button className="danger-lg" onClick={runAccessStop} disabled={mcpLoading}>
                {mcpLoading ? <span className="spinner" aria-hidden="true" /> : null}
                {accessInfo.primaryLabel}
              </button>
            ) : null}
            {accessInfo.primaryAction === "start" ? (
              <button className="primary-green" onClick={runAccessStart} disabled={mcpLoading}>
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
              <button className="primary-green" onClick={runAccessStart} disabled={mcpLoading}>
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

      {/* ── 4. OpenAI tunnel card ── */}
      <section className="card">
        <p className="section-label">TUNNEL OPENAI</p>
        <div className="row between" style={{ gap: "var(--space-2)", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: "1.05rem", wordBreak: "break-all" }}>
              {tunnel.tunnel_id ?? "Tunnel non configuré"}
            </h2>
            <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
              {tunnel.ready
                ? "Connecté au control plane OpenAI. ChatGPT peut utiliser Connection: Tunnel."
                : tunnel.configured
                  ? tunnel.last_event ?? "Tunnel OpenAI arrêté."
                  : "Aucun tunnel local configuré."}
            </p>
          </div>
          <span className={`badge badge-pill ${tunnelBadgeClass}`}>{tunnelBadgeLabel}</span>
        </div>

        {!tunnel.configured ? (
          <p className="warning-box">
            Tunnel OpenAI non configuré. <a href="/tunnel">Ouvre /tunnel</a> pour renseigner
            le tunnel ID et la runtime API key.
          </p>
        ) : null}

        <div className="row wrap" style={{ gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
          <button onClick={handleCopy} disabled={!tunnel.tunnel_id}>
            {copied ? "Copié" : "Copier l'ID"}
          </button>
          <a className="button-link" href={tunnel.connector_url} target="_blank" rel="noreferrer">
            Connecteurs ChatGPT
          </a>
          {tunnel.ui_url && (tunnel.state === "running" || tunnel.state === "starting") ? (
            <a className="button-link" href={tunnel.ui_url} target="_blank" rel="noreferrer">
              Tableau de bord tunnel
            </a>
          ) : null}
          {!tunnel.configured ? (
            <a className="button-link" href="/tunnel">Configurer le tunnel</a>
          ) : (
            <>
              {tunnel.state === "running" ? (
                <button className="secondary" onClick={() => void runAction(api.stopTunnel)} disabled={loadingAction}>
                  Arrêter le tunnel
                </button>
              ) : (
                <button className="secondary" onClick={() => void runAction(api.startTunnel)} disabled={loadingAction}>
                  Démarrer le tunnel
                </button>
              )}
              <button className="ghost" onClick={() => void runAction(api.restartTunnel)} disabled={loadingAction}>
                Redémarrer
              </button>
            </>
          )}
        </div>

        <div className="info-callout" style={{ marginTop: "var(--space-2)" }}>
          <span className="info-callout-icon">ℹ</span>
          <span>
            Dans ChatGPT → Settings → Connectors → <code>Connection: Tunnel</code>,
            sélectionne le tunnel ou colle son ID. Aucune URL publique à copier.
          </span>
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
          title="Tunnel OpenAI"
          kind="tunnel"
          data={status.tunnel}
          onLogs={() => void openLogs("tunnel")}
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
    </main>
  );
}
