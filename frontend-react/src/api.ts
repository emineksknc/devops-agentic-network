async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = (await r.json().catch(() => ({}))) as { detail?: string } & Record<string, unknown>;
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data as T;
}

export const api = {
  get: <T>(p: string) => req<T>("GET", p),
  post: <T>(p: string, b?: unknown) => req<T>("POST", p, b),
  put: <T>(p: string, b?: unknown) => req<T>("PUT", p, b),
  del: <T>(p: string) => req<T>("DELETE", p),
};

export interface Run {
  run_id: string;
  repo: string;
  status: string;
  dry_run: boolean;
  blocked_count: number;
  commit_count: number;
  created_at: string;
}

export interface CommitUnit {
  sha?: string | null;
  short_sha?: string | null;
  message?: string | null;
  author?: string | null;
  jira_ids: string[];
  review_status?: string | null;
  review_comment?: string | null;
}

export interface JiraAction {
  ticket_id: string;
  commit_sha?: string | null;
  review_passed: boolean;
  state: string;
  comment_ok?: boolean | null;
  transition_to?: string | null;
  transition_ok?: boolean | null;
  skipped_reason?: string | null;
}

export interface RunDetail extends Run {
  final_report?: string | null;
  error?: string | null;
  commit_units: CommitUnit[];
  jira_actions: JiraAction[];
}

export interface Policy {
  repo: string;
  jira_project: string;
  on_pass_transition: string;
  on_fail_transition: string;
  auto_write_pass: boolean;
  auto_write_fail: boolean;
  require_approval: boolean;
  dry_run_default: boolean;
  github_conn_id: string;
  jira_conn_id: string;
}

export interface Connection {
  id: string;
  name: string;
  kind: "github" | "jira" | "llm";
  base_url: string;
  owner: string;
  email: string;
  token: string;
  project_key: string;
  provider: string;
  model: string;
  temperature: number;
  max_tokens: number;
  webhook_secret: string;
  is_default: boolean;
}

export interface AgentInfo {
  name: string;
  enabled: boolean;
  system_prompt: string;
  default_prompt: string;
  customized: boolean;
}

export interface Developer {
  author: string;
  commits: number;
  blocked: number;
  repos: number;
  last_seen?: string | null;
  tickets: string[];
}

export interface AuditRow {
  id: number;
  run_id: string;
  repo: string;
  trigger?: string;
  created_at?: string;
  ticket_id: string;
  review_passed: boolean;
  state: string;
  transition_to?: string | null;
  skipped_reason?: string | null;
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600) return `${Math.max(1, Math.floor(diff / 60))} dk önce`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} saat önce`;
  return new Date(iso).toLocaleString("tr-TR");
}
