export type GlobalState = "not_configured" | "needs_auth" | "ready" | "degraded" | "error";
export type GarminAuthState =
  | "not_configured"
  | "configured"
  | "valid"
  | "expiring_soon"
  | "expired"
  | "error";
export type KeySource = "file" | "env";
export type RotationSource = "declared" | "observed" | "unknown";
export type McpState = "stopped" | "starting" | "running" | "unhealthy" | "error";
export type McpLocalState = "running" | "stopped" | "starting" | "stopping" | "error";
export type TunnelState = "stopped" | "starting" | "running" | "error";
export type BadgeState = GlobalState | GarminAuthState | McpState | TunnelState | "success" | "failed" | "not_run" | "skipped" | McpLocalState;

export interface ProcessStatus {
  status: McpState;
  pid: number | null;
  message: string;
}

export interface HealthcheckResult {
  ok: boolean;
  target: string;
  message: string;
  status_code: number | null;
}

export interface GarminKeyInfo {
  source: KeySource | null;
  hint: string | null;
  fingerprint: string | null;
}

export interface GarminRotationInfo {
  expires_on: string | null;
  days_remaining: number | null;
  source: RotationSource;
  warning: boolean;
}

export interface GarminAuthStatus {
  state: GarminAuthState;
  configured: boolean;
  key: GarminKeyInfo;
  token_present: boolean;
  token_valid: boolean;
  token_expires_at: string | null;
  token_scopes: string[];
  rotation: GarminRotationInfo;
  last_verified_at: string | null;
  display_name: string | null;
  message: string;
  error: string | null;
}

export interface GarminAuthResult {
  ok: boolean;
  changed: boolean;
  message: string;
  status: GarminAuthStatus;
}

export interface McpStatus {
  state: McpState;
  host: string;
  port: number;
  endpoint: string;
  local_url: string;
  process: ProcessStatus;
  healthcheck: HealthcheckResult | null;
}

export interface McpLocalStatus {
  running: boolean;
  status: McpLocalState;
  pid: number | null;
  port: number;
  last_started_at: string | null;
  last_stopped_at: string | null;
  last_error: string | null;
}

export interface TunnelStatus {
  state: TunnelState;
  provider: "openai";
  configured: boolean;
  tunnel_id: string | null;
  api_key_configured: boolean;
  binary_installed: boolean;
  binary_version: string | null;
  ready: boolean;
  health_status: number | null;
  health_url: string | null;
  ui_url: string | null;
  connector_url: string;
  pid: number | null;
  last_event: string | null;
  process: ProcessStatus;
}

export interface TunnelConfigStatus {
  configured: boolean;
  tunnel_id: string | null;
  key_hint: string | null;
  source: "env" | "file" | "mixed" | "none";
  key_source: "env" | "file" | null;
  tunnel_id_source: "env" | "file" | null;
  editable: boolean;
  binary_installed: boolean;
  binary_version: string | null;
  message: string;
}

export interface TunnelConfigResult {
  ok: boolean;
  changed: boolean;
  message: string;
  config: TunnelConfigStatus;
  status: TunnelStatus;
}

export interface TunnelBinaryResult {
  ok: boolean;
  installed: boolean;
  version: string | null;
  path: string | null;
  message: string;
}

export interface GlobalStatus {
  app_name: string;
  version: string;
  state: GlobalState;
  message: string;
  backend_url: string;
  garmin: GarminAuthStatus;
  mcp: McpStatus;
  tunnel: TunnelStatus;
}

export interface ActionResult {
  ok: boolean;
  status: string;
  message: string;
  pid: number | null;
  state?: TunnelState | null;
}

export interface LogResult {
  service: string;
  lines: string[];
  truncated: boolean;
}

export interface TestDefinition {
  id: string;
  name: string;
  description: string;
}

export interface TestResult {
  id: string;
  name: string;
  state: "not_run" | "running" | "success" | "failed" | "skipped";
  duration_ms: number;
  message: string;
  suggestion: string | null;
}

export interface McpTool {
  name: string;
  risk: "read" | "write" | "unknown";
  reason: string;
}

export interface McpToolsResult {
  ok: boolean;
  message: string;
  tools: McpTool[];
}

export interface McpToolClassification {
  read_tools: string[];
  write_tools: string[];
  unknown_tools: string[];
}
