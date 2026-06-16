import { formatDate } from "../lib/format";
import type { GarminAuthStatus, McpStatus, TunnelStatus } from "../lib/types";
import { StatusBadge } from "./StatusBadge";

export function ServiceStatusCard({
  title,
  kind,
  data,
  onLogs,
  onAction,
  actionLabel,
}: {
  title: string;
  kind: "garmin" | "mcp" | "tunnel";
  data: GarminAuthStatus | McpStatus | TunnelStatus;
  onLogs: () => void;
  onAction?: () => void;
  actionLabel?: string;
}) {
  const state = "state" in data ? data.state : "unknown";
  return (
    <article className="card service-card">
      <div className="card-title-row">
        <h2>{title}</h2>
        <StatusBadge state={state} />
      </div>
      {kind === "garmin" ? <GarminDetails data={data as GarminAuthStatus} /> : null}
      {kind === "mcp" ? <McpDetails data={data as McpStatus} /> : null}
      {kind === "tunnel" ? <TunnelDetails data={data as TunnelStatus} /> : null}
      <div className="row wrap">
        <button className="secondary" onClick={onLogs}>Afficher les logs</button>
        {onAction && actionLabel ? <button onClick={onAction}>{actionLabel}</button> : null}
      </div>
    </article>
  );
}

function GarminDetails({ data }: { data: GarminAuthStatus }) {
  return (
    <dl className="details">
      <div><dt>Token</dt><dd>{data.token_found ? "détecté" : "absent"}</dd></div>
      <div><dt>Validité</dt><dd>{data.token_valid ? "valide" : "à vérifier"}</dd></div>
      <div><dt>Dernière connexion</dt><dd>{formatDate(data.last_successful_auth)}</dd></div>
      <div><dt>Message</dt><dd>{data.message}</dd></div>
    </dl>
  );
}

function McpDetails({ data }: { data: McpStatus }) {
  return (
    <dl className="details">
      <div><dt>Endpoint local</dt><dd>{data.local_url}</dd></div>
      <div><dt>PID</dt><dd>{data.process.pid ?? "-"}</dd></div>
      <div><dt>Healthcheck</dt><dd>{data.healthcheck?.message ?? "non lancé"}</dd></div>
    </dl>
  );
}

function TunnelDetails({ data }: { data: TunnelStatus }) {
  return (
    <dl className="details">
      <div><dt>Mode</dt><dd>{data.mode}</dd></div>
      <div><dt>PID</dt><dd>{data.pid ?? "-"}</dd></div>
      <div><dt>URL publique</dt><dd>{data.public_url ?? "non détectée"}</dd></div>
      <div><dt>Dernier événement</dt><dd>{data.last_event ?? "-"}</dd></div>
    </dl>
  );
}
