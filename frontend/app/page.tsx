"use client";

import { useEffect, useState } from "react";
import { AppHeader } from "../components/AppHeader";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { LogsModal } from "../components/LogsModal";
import { ServiceStatusCard } from "../components/ServiceStatusCard";
import { StatusBadge } from "../components/StatusBadge";
import { TunnelCard } from "../components/TunnelCard";
import { api } from "../lib/api";
import type { GlobalStatus, LogResult } from "../lib/types";

export default function HomePage() {
  const [status, setStatus] = useState<GlobalStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState(false);
  const [copied, setCopied] = useState(false);
  const [logsService, setLogsService] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogResult | null>(null);
  const [confirm, setConfirm] = useState<null | "stopTunnel" | "disconnect" | "regenerate">(null);

  async function refresh() {
    try {
      setStatus(await api.status());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function runAction(action: () => Promise<unknown>) {
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
  }

  async function openLogs(service: string) {
    setLogsService(service);
    setLogs(await api.logs(service));
  }

  if (!status) {
    return <main className="shell"><AppHeader /><p className="card">Chargement de l’état local...</p></main>;
  }

  return (
    <main className="shell">
      <AppHeader version={status.version} />
      <section className="status-strip card">
        <div>
          <p className="eyebrow">État global</p>
          <h2>{status.message}</h2>
        </div>
        <StatusBadge state={status.state} />
      </section>
      {error ? <p className="error-box">{error}</p> : null}
      <TunnelCard
        tunnel={status.tunnel}
        loading={loadingAction}
        copied={copied}
        onCopy={() => {
          if (status.tunnel.chatgpt_mcp_url) {
            void navigator.clipboard?.writeText(status.tunnel.chatgpt_mcp_url);
            setCopied(true);
          }
        }}
        onStart={() => void runAction(api.startTunnel)}
        onStop={() => setConfirm("stopTunnel")}
        onRegenerate={() => setConfirm("regenerate")}
      />
      <section className="grid">
        <ServiceStatusCard title="Service local" kind="mcp" data={status.mcp} onLogs={() => void openLogs("mcp")} onAction={() => void runAction(api.restartMcp)} actionLabel="Redémarrer le service local" />
        <ServiceStatusCard title="Garmin MCP" kind="garmin" data={status.garmin} onLogs={() => void openLogs("auth")} onAction={() => setConfirm("disconnect")} actionLabel="Déconnexion" />
        <ServiceStatusCard title="Cloudflare Tunnel" kind="tunnel" data={status.tunnel} onLogs={() => void openLogs("cloudflare")} onAction={() => void runAction(api.pauseTunnel)} actionLabel="Pause" />
      </section>
      <div className="row wrap footer-actions">
        <a className="button-link" href="/tests">Ouvrir les tests</a>
        <button className="secondary" onClick={() => void refresh()}>Rafraîchir</button>
      </div>
      <LogsModal service={logsService} logs={logs} onClose={() => setLogsService(null)} onRefresh={() => logsService && void openLogs(logsService)} />
      <ConfirmDialog
        open={confirm !== null}
        title="Confirmation requise"
        message={confirm === "disconnect" ? "Voulez-vous vraiment vous déconnecter ? Les tokens Garmin locaux seront supprimés." : "Cette action modifie l’état du tunnel Cloudflare public."}
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
