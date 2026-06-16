import { formatDate } from "../lib/format";
import type { GarminAuthStatus, McpLocalStatus, McpStatus, TunnelStatus } from "../lib/types";
import { LoadingButton } from "./LoadingButton";
import { StatusBadge } from "./StatusBadge";

export function ServiceStatusCard({
  title,
  kind,
  data,
  onLogs,
  onAction,
  actionLabel,
  mcpLocal,
  mcpLoading,
  onMcpStart,
  onMcpStop,
  onMcpRestart,
}: {
  title: string;
  kind: "garmin" | "mcp" | "tunnel";
  data: GarminAuthStatus | McpStatus | TunnelStatus;
  onLogs: () => void;
  onAction?: () => void;
  actionLabel?: string;
  mcpLocal?: McpLocalStatus | null;
  mcpLoading?: boolean;
  onMcpStart?: () => void;
  onMcpStop?: () => void;
  onMcpRestart?: () => void;
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
      {kind === "mcp" && mcpLocal ? <McpLocalDetails status={mcpLocal} /> : null}
      {kind === "tunnel" ? <TunnelDetails data={data as TunnelStatus} /> : null}
      {kind === "mcp" ? (
        <McpControls
          localStatus={mcpLocal}
          loading={mcpLoading ?? false}
          onStart={onMcpStart}
          onStop={onMcpStop}
          onRestart={onMcpRestart}
          onLogs={onLogs}
        />
      ) : (
        <div className="row wrap">
          <button className="secondary" onClick={onLogs}>Afficher les logs</button>
          {onAction && actionLabel ? <button onClick={onAction}>{actionLabel}</button> : null}
        </div>
      )}
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

function McpLocalDetails({ status }: { status: McpLocalStatus }) {
  return (
    <dl className="details">
      <div><dt>Port</dt><dd>{status.port}</dd></div>
      <div><dt>Dernier démarrage</dt><dd>{formatDate(status.last_started_at)}</dd></div>
      <div><dt>Dernier arrêt</dt><dd>{formatDate(status.last_stopped_at)}</dd></div>
      {status.last_error ? <div><dt>Dernière erreur</dt><dd className="error-text">{status.last_error}</dd></div> : null}
    </dl>
  );
}

function McpControls({
  localStatus,
  loading,
  onStart,
  onStop,
  onRestart,
  onLogs,
}: {
  localStatus?: McpLocalStatus | null;
  loading: boolean;
  onStart?: () => void;
  onStop?: () => void;
  onRestart?: () => void;
  onLogs?: () => void;
}) {
  const running = localStatus?.status === "running";
  const stopped = localStatus?.status === "stopped";
  const starting = localStatus?.status === "starting";
  const stopping = localStatus?.status === "stopping";
  const errored = localStatus?.status === "error";

  return (
    <>
      <p className="helper-text">
        Le tunnel Cloudflare peut rester ouvert. Quand le MCP local est arrêté,
        ChatGPT ne peut plus accéder aux outils Garmin.
      </p>
      <div className="row wrap">
        <button className="secondary" onClick={onLogs}>Afficher les logs</button>
        {running ? (
          <LoadingButton className="danger" loading={loading || stopping} onClick={onStop}>
            Arrêter le MCP local
          </LoadingButton>
        ) : (
          <LoadingButton loading={loading || starting} onClick={onStart}>
            Démarrer le MCP local
          </LoadingButton>
        )}
        {running || errored ? (
          <LoadingButton className="secondary" loading={loading} onClick={onRestart}>
            Redémarrer le MCP local
          </LoadingButton>
        ) : null}
      </div>
    </>
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
