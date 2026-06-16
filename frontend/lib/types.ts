export type GlobalState = "not_configured" | "needs_auth" | "ready" | "degraded" | "error";
export type GarminState =
  | "unknown"
  | "no_token"
  | "token_found"
  | "connected"
  | "auth_invalid"
  | "reauth_required"
  | "error";
export type McpState = "stopped" | "starting" | "running" | "unhealthy" | "error";
export type TunnelState = "stopped" | "starting" | "running" | "paused" | "expired" | "error";
export type BadgeState = GlobalState | GarminState | McpState | TunnelState | "success" | "failed" | "not_run" | "skipped";

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

export interface GarminAuthStatus {
  state: GarminState;
  token_found: boolean;
  token_valid: boolean;
  last_successful_auth: string | null;
  message: string;
}

export interface GarminAuthResult {
  ok: boolean;
  assisted: boolean;
  message: string;
  command: string[] | null;
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

export interface TunnelStatus {
  state: TunnelState;
  mode: "quick" | "named";
  public_url: string | null;
  chatgpt_mcp_url: string | null;
  pid: number | null;
  last_event: string | null;
  process: ProcessStatus;
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
  public_url?: string | null;
  chatgpt_mcp_url?: string | null;
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
