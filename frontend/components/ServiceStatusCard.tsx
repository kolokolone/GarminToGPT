import { formatDate } from "../lib/format";
import {
  getMcpLocalTechInfo,
  getGarminTechInfo,
  getTunnelTechInfo,
} from "../lib/status";
import type { GarminAuthStatus, McpLocalStatus, McpStatus, TunnelStatus } from "../lib/types";

/**
 * Compact technical status card used in the 3-card grid on the home page.
 * Renders icon, title, badge, summary text, and a 2-column details grid.
 * No primary action buttons — only a "Logs" button.
 */
export function ServiceStatusCard({
  title,
  kind,
  data,
  onLogs,
  mcpLocal,
}: {
  title: string;
  kind: "mcp" | "garmin" | "tunnel";
  data: GarminAuthStatus | McpStatus | TunnelStatus;
  onLogs?: () => void;
  mcpLocal?: McpLocalStatus | null;
}) {
  return (
    <article className="card card-compact tech-card">
      {kind === "mcp" && mcpLocal ? <McpTechContent mcpLocal={mcpLocal} data={data as McpStatus} onLogs={onLogs} /> : null}
      {kind === "garmin" ? <GarminTechContent data={data as GarminAuthStatus} onLogs={onLogs} /> : null}
      {kind === "tunnel" ? <TunnelTechContent data={data as TunnelStatus} onLogs={onLogs} /> : null}
    </article>
  );
}

function TechCardHeader({
  title,
  iconClass,
  iconLabel,
  badgeLabel,
  badgeClass,
}: {
  title: string;
  iconClass: string;
  iconLabel: string;
  badgeLabel: string;
  badgeClass: string;
}) {
  return (
    <div className="tech-card-header">
      <div className="tech-card-header-left">
        <span className={`tech-card-icon ${iconClass}`}>{iconLabel}</span>
        <span className="tech-card-title">{title}</span>
      </div>
      <span className={`badge ${badgeClass}`}>{badgeLabel}</span>
    </div>
  );
}

function McpTechContent({ mcpLocal, data, onLogs }: { mcpLocal: McpLocalStatus; data: McpStatus; onLogs?: () => void }) {
  const info = getMcpLocalTechInfo(mcpLocal);
  return (
    <>
      <TechCardHeader title="Service local" {...info} />
      <p className="tech-card-summary">{info.summary}</p>
      <div className="details-grid">
        <div className="details-item">
          <span className="details-label">Endpoint</span>
          <span className="details-value">{data.local_url}</span>
        </div>
        <div className="details-item">
          <span className="details-label">PID</span>
          <span className="details-value">{data.process.pid ?? "-"}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Port</span>
          <span className="details-value">{mcpLocal.port}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Healthcheck</span>
          <span className="details-value">{data.healthcheck?.message ?? "non lancé"}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Dernier démarrage</span>
          <span className="details-value">{formatDate(mcpLocal.last_started_at)}</span>
        </div>
        {mcpLocal.last_error ? (
          <div className="details-item">
            <span className="details-label">Dernière erreur</span>
            <span className="details-value" style={{ color: "var(--red)" }}>{mcpLocal.last_error}</span>
          </div>
        ) : null}
      </div>
      {onLogs ? (
        <div style={{ marginTop: "var(--space-2)" }}>
          <button className="secondary" onClick={onLogs}>Afficher les logs</button>
        </div>
      ) : null}
    </>
  );
}

function GarminTechContent({ data, onLogs }: { data: GarminAuthStatus; onLogs?: () => void }) {
  const info = getGarminTechInfo(data);
  return (
    <>
      <TechCardHeader title="Garmin MCP" {...info} />
      <p className="tech-card-summary">{info.summary}</p>
      <div className="details-grid">
        <div className="details-item">
          <span className="details-label">Token</span>
          <span className="details-value">{data.token_found ? "détecté" : "absent"}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Validité</span>
          <span className="details-value">{data.token_valid ? "valide" : "à vérifier"}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Dernière connexion</span>
          <span className="details-value">{formatDate(data.last_successful_auth)}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Message</span>
          <span className="details-value">{data.message}</span>
        </div>
      </div>
      {onLogs ? (
        <div style={{ marginTop: "var(--space-2)" }}>
          <button className="secondary" onClick={onLogs}>Afficher les logs</button>
        </div>
      ) : null}
    </>
  );
}

function TunnelTechContent({ data, onLogs }: { data: TunnelStatus; onLogs?: () => void }) {
  const info = getTunnelTechInfo(data);
  return (
    <>
      <TechCardHeader title="Cloudflare Tunnel" {...info} />
      <p className="tech-card-summary">{info.summary}</p>
      <div className="details-grid">
        <div className="details-item">
          <span className="details-label">Mode</span>
          <span className="details-value">{data.mode}</span>
        </div>
        <div className="details-item">
          <span className="details-label">PID</span>
          <span className="details-value">{data.pid ?? "-"}</span>
        </div>
        <div className="details-item">
          <span className="details-label">URL publique</span>
          <span className="details-value">{data.public_url ?? "non détectée"}</span>
        </div>
        <div className="details-item">
          <span className="details-label">Dernier événement</span>
          <span className="details-value">{data.last_event ?? "-"}</span>
        </div>
      </div>
      {onLogs ? (
        <div style={{ marginTop: "var(--space-2)" }}>
          <button className="secondary" onClick={onLogs}>Afficher les logs</button>
        </div>
      ) : null}
    </>
  );
}
