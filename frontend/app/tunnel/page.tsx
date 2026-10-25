"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "../../components/AppHeader";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { LoadingButton } from "../../components/LoadingButton";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import type {
  TunnelBinaryResult,
  TunnelConfigResult,
  TunnelConfigStatus,
  TunnelStatus,
} from "../../lib/types";

const TUNNELS_PAGE = "https://platform.openai.com/settings/organization/tunnels";
const KEYS_PAGE = "https://platform.openai.com/settings/organization/api-keys";
const CHATGPT_CONNECTORS = "https://chatgpt.com/#settings/Connectors";

const SOURCE_LABEL: Record<string, string> = {
  env: "variable d'environnement",
  file: "fichier local 0600",
  mixed: "environnement + fichier",
  none: "non configurée",
};

export default function TunnelPage() {
  const [config, setConfig] = useState<TunnelConfigStatus | null>(null);
  const [status, setStatus] = useState<TunnelStatus | null>(null);
  const [tunnelId, setTunnelId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TunnelConfigResult | null>(null);
  const [binaryResult, setBinaryResult] = useState<TunnelBinaryResult | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [copied, setCopied] = useState(false);

  const applyConfig = useCallback((next: TunnelConfigStatus) => {
    setConfig(next);
    if (!next.configured) {
      setEditing(true);
      return;
    }
    setTunnelId(next.tunnel_id ?? "");
    if (next.editable) setEditing(false);
  }, []);

  const load = useCallback(async () => {
    const [nextConfig, nextStatus] = await Promise.all([
      api.tunnelConfig(),
      api.tunnelStatus(),
    ]);
    applyConfig(nextConfig);
    setStatus(nextStatus);
  }, [applyConfig]);

  useEffect(() => {
    void load().catch((err) =>
      setError(err instanceof Error ? err.message : "Impossible de charger le tunnel"),
    );
  }, [load]);

  useEffect(() => {
    if (status?.state !== "starting") return;
    const interval = setInterval(async () => {
      try {
        setStatus(await api.tunnelStatus());
      } catch {
        // Polling silencieux.
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [status?.state]);

  async function save() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.saveTunnelConfig({
        tunnel_id: tunnelId,
        api_key: apiKey,
      });
      applyConfig(response.config);
      setStatus(response.status);
      setResult(response);
      setApiKey("");
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tunnel refusé");
    } finally {
      setLoading(false);
    }
  }

  async function install() {
    setInstalling(true);
    setError(null);
    setBinaryResult(null);
    try {
      const response = await api.installTunnelClient();
      setBinaryResult(response);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Installation impossible");
    } finally {
      setInstalling(false);
    }
  }

  async function runAction(action: () => Promise<unknown>) {
    setLoading(true);
    setError(null);
    try {
      const result = (await action()) as { ok?: boolean; message?: string } | undefined;
      await load();
      if (result && result.ok === false) {
        setError(result.message ?? "Action tunnel impossible");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action tunnel impossible");
    } finally {
      setLoading(false);
      setConfirmDelete(false);
    }
  }

  async function removeConfig() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.removeTunnelConfig();
      applyConfig(response.config);
      setStatus(response.status);
      setResult(response);
      setTunnelId("");
      setApiKey("");
      setEditing(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible");
    } finally {
      setLoading(false);
      setConfirmDelete(false);
    }
  }

  function copyTunnelId() {
    if (!config?.tunnel_id) return;
    void navigator.clipboard?.writeText(config.tunnel_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!config || !status) {
    return (
      <main className="shell narrow">
        <AppHeader />
        <section className="card card-primary">
          <p className="section-label">TUNNEL OPENAI</p>
          <p style={{ color: "var(--muted)" }}>Chargement de l&rsquo;état du tunnel…</p>
        </section>
      </main>
    );
  }

  const configured = config.configured;
  const source = SOURCE_LABEL[config.source] ?? config.source;

  return (
    <main className="shell narrow">
      <AppHeader />

      <section className="card card-primary">
        <p className="section-label">TUNNEL OPENAI</p>
        <div className="row between" style={{ gap: "var(--space-2)", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: "18rem" }}>
            <h2 style={{ fontSize: "1.3rem", marginBottom: "0.5rem" }}>
              Connecter ChatGPT via Secure MCP Tunnel
            </h2>
            <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
              Le client OpenAI établit une connexion sortante vers le control plane.
              Aucune URL publique n&rsquo;est créée.
            </p>
          </div>
          <StatusBadge state={status.state} />
        </div>

        <div className="info-callout" style={{ marginTop: "var(--space-3)" }}>
          <span className="info-callout-icon">ℹ</span>
          <span>
            Dans ChatGPT, ouvre <a href={CHATGPT_CONNECTORS} target="_blank" rel="noreferrer">Settings → Connectors</a>,
            choisis <code>Connection: Tunnel</code>, puis sélectionne le tunnel ou colle son ID.
            Le client doit rester démarré pour les appels MCP.
          </span>
        </div>

        <div className="row wrap" style={{ marginTop: "var(--space-2)" }}>
          <a className="button-link ghost" href={TUNNELS_PAGE} target="_blank" rel="noreferrer">
            Platform Tunnels
          </a>
          <a className="button-link ghost" href={KEYS_PAGE} target="_blank" rel="noreferrer">
            Runtime API keys
          </a>
          <a className="button-link ghost" href={CHATGPT_CONNECTORS} target="_blank" rel="noreferrer">
            Connecteurs ChatGPT
          </a>
        </div>

        {error ? <p className="error-box">{error}</p> : null}
        {result ? <p className="success-box">{result.message}</p> : null}
        {binaryResult ? (
          <p className={binaryResult.ok ? "success-box" : "error-box"}>{binaryResult.message}</p>
        ) : null}

        {!configured || editing ? (
          <div style={{ marginTop: "var(--space-3)" }}>
            {!editing && configured ? null : (
              <>
                <div className="form-grid">
                  <label>
                    Tunnel ID
                    <input
                      value={tunnelId}
                      onChange={(event) => setTunnelId(event.target.value)}
                      autoComplete="off"
                      spellCheck={false}
                      placeholder="tunnel_…"
                      disabled={!config.editable}
                    />
                  </label>
                  <label>
                    Runtime API key OpenAI
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(event) => setApiKey(event.target.value)}
                      autoComplete="off"
                      spellCheck={false}
                      placeholder="sk-…"
                      disabled={!config.editable}
                    />
                  </label>
                </div>
                <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                  La clé doit être une runtime key avec les permissions Tunnels Read + Use.
                  Elle est vérifiée auprès d&rsquo;OpenAI avant d&rsquo;être enregistrée.
                </p>
                {!config.editable ? (
                  <p className="warning-box">
                    Configuration fournie par l&rsquo;environnement
                    (<code>CONTROL_PLANE_TUNNEL_ID</code> / <code>CONTROL_PLANE_API_KEY</code>).
                    Retire ces variables pour gérer le tunnel depuis cette page.
                  </p>
                ) : null}
                <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
                  <LoadingButton
                    loading={loading}
                    onClick={() => void save()}
                    className="primary-green"
                    disabled={!config.editable || !tunnelId.trim() || !apiKey.trim()}
                  >
                    Tester et enregistrer
                  </LoadingButton>
                  {config.configured ? (
                    <button className="secondary" onClick={() => setEditing(false)} disabled={loading}>
                      Annuler
                    </button>
                  ) : null}
                </div>
              </>
            )}
          </div>
        ) : null}
      </section>

      {configured ? (
        <section className="card">
          <div className="row between" style={{ gap: "var(--space-2)", flexWrap: "wrap" }}>
            <div>
              <p className="section-label">ÉTAT DU TUNNEL</p>
              <h2 style={{ fontSize: "1.1rem", wordBreak: "break-all" }}>
                {config.tunnel_id}
              </h2>
            </div>
            <div className="row" style={{ gap: "var(--space-1)" }}>
              <StatusBadge state={status.state} />
              <button className="ghost" onClick={copyTunnelId}>
                {copied ? "Copié" : "Copier l'ID"}
              </button>
            </div>
          </div>

          <p className={status.ready ? "success-box" : "warning-box"}>
            {status.ready
              ? "Tunnel prêt. ChatGPT peut utiliser Connection: Tunnel avec cet ID."
              : status.last_event ?? "Tunnel en attente de /readyz."}
          </p>

          <div className="details-grid">
            <div className="details-item">
              <span className="details-label">Clé runtime</span>
              <span className="details-value">{config.key_hint ?? "absente"}</span>
            </div>
            <div className="details-item">
              <span className="details-label">Source</span>
              <span className="details-value">{source}</span>
            </div>
            <div className="details-item">
              <span className="details-label">Client tunnel</span>
              <span className="details-value">
                {config.binary_installed
                  ? `installé (${config.binary_version ?? "version inconnue"})`
                  : "non installé"}
              </span>
            </div>
            <div className="details-item">
              <span className="details-label">Readiness</span>
              <span className="details-value">
                {status.ready ? "prêt" : status.health_status ? `HTTP ${status.health_status}` : "en attente"}
              </span>
            </div>
            <div className="details-item">
              <span className="details-label">Tableau de bord</span>
              <span className="details-value">
                {status.ui_url ? <a href={status.ui_url} target="_blank" rel="noreferrer">Ouvrir</a> : "-"}
              </span>
            </div>
            <div className="details-item">
              <span className="details-label">Dernier événement</span>
              <span className="details-value">{status.last_event ?? "-"}</span>
            </div>
          </div>

          <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
            {status.state === "running" ? (
              <button className="danger" onClick={() => void runAction(api.stopTunnel)} disabled={loading}>
                Arrêter le tunnel
              </button>
            ) : (
              <button className="primary-green" onClick={() => void runAction(api.startTunnel)} disabled={loading}>
                Démarrer le tunnel
              </button>
            )}
            <button className="secondary" onClick={() => void runAction(api.restartTunnel)} disabled={loading}>
              Redémarrer
            </button>
            {!config.binary_installed ? (
              <LoadingButton loading={installing} onClick={() => void install()} className="secondary">
                Installer le client
              </LoadingButton>
            ) : null}
            {config.editable ? (
              <button className="secondary" onClick={() => setEditing((value) => !value)}>
                {editing ? "Annuler la mise à jour" : "Mettre à jour"}
              </button>
            ) : null}
            <button className="danger" onClick={() => setConfirmDelete(true)} disabled={loading}>
              Supprimer la configuration
            </button>
          </div>

          {!config.editable ? (
            <p className="warning-box" style={{ marginTop: "var(--space-2)" }}>
              Le tunnel est configuré par l&rsquo;environnement
              (<code>CONTROL_PLANE_TUNNEL_ID</code> / <code>CONTROL_PLANE_API_KEY</code>).
              Retire ces variables pour gérer les valeurs depuis cette page.
            </p>
          ) : null}
        </section>
      ) : null}

      <div className="action-bar-center" style={{ marginTop: "var(--space-2)" }}>
        <a className="button-link ghost" href="/">Retour vers l&rsquo;accueil</a>
        <a className="button-link ghost" href="/tests">Ouvrir les tests</a>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Supprimer la configuration du tunnel ?"
        message="Le tunnel sera arrêté et les fichiers locaux (tunnel ID + runtime key) seront supprimés. Les variables d'environnement éventuelles restent prioritaires."
        confirmLabel="Supprimer"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => void removeConfig()}
      />
    </main>
  );
}
