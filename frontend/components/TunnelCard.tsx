import type { TunnelStatus } from "../lib/types";
import { LoadingButton } from "./LoadingButton";
import { StatusBadge } from "./StatusBadge";

export function TunnelCard({
  tunnel,
  loading,
  copied,
  onCopy,
  onStart,
  onStop,
  onRegenerate,
}: {
  tunnel: TunnelStatus;
  loading: boolean;
  copied: boolean;
  onCopy: () => void;
  onStart: () => void;
  onStop: () => void;
  onRegenerate: () => void;
}) {
  const url = tunnel.chatgpt_mcp_url ?? "Tunnel Cloudflare non actif";
  return (
    <article className="card hero-card">
      <div className="card-title-row">
        <div>
          <p className="eyebrow">URL MCP pour ChatGPT</p>
          <h2>{url}</h2>
        </div>
        <StatusBadge state={tunnel.state} />
      </div>
      <p className="warning">
        Tant que le tunnel est actif, l’URL publique peut exposer les outils MCP Garmin. Éteins-le dès que tu n’en as plus besoin.
      </p>
      <div className="row wrap">
        <button onClick={onCopy} disabled={!tunnel.chatgpt_mcp_url}>{copied ? "Copié" : "Copier"}</button>
        {tunnel.state === "running" ? (
          <LoadingButton className="danger" loading={loading} onClick={onStop}>Éteindre le tunnel</LoadingButton>
        ) : (
          <LoadingButton loading={loading} onClick={onStart}>Allumer le tunnel</LoadingButton>
        )}
        <LoadingButton className="secondary" loading={loading} onClick={onRegenerate}>Regénérer le lien</LoadingButton>
      </div>
    </article>
  );
}
