function stripHtml(s: string): string {
  return s
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 160);
}

const TOKEN_KEY = "dan_token";
const ROLE_KEY = "dan_role";

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(t: string) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* yoksay */
  }
}

export function getRole(): string {
  try {
    return localStorage.getItem(ROLE_KEY) || "";
  } catch {
    return "";
  }
}

export function setRole(r: string) {
  try {
    if (r) localStorage.setItem(ROLE_KEY, r);
    else localStorage.removeItem(ROLE_KEY);
  } catch {
    /* yoksay */
  }
}

export function isAdmin(): boolean {
  return getRole() === "admin";
}

export function canApprove(): boolean {
  const r = getRole();
  return r === "admin" || r === "approver";
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  let r: Response;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    r = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    throw new Error(`API'ye ulaşılamadı (${path}). Server çalışıyor mu, proxy localhost'u engelliyor mu?`);
  }
  const text = await r.text();
  let data: { detail?: string } & Record<string, unknown> = {};
  try {
    data = text ? (JSON.parse(text) as typeof data) : {};
  } catch {
    throw new Error(`API JSON dışı yanıt döndürdü (HTTP ${r.status}): ${stripHtml(text) || "boş gövde"}`);
  }
  if (r.status === 401 && !path.startsWith("/api/auth/") && window.location.pathname !== "/login") {
    // Oturum bitmis/yok: girise gonder (login sayfasinda ve auth uclarinda donguye girme)
    setToken("");
    setRole("");
    window.location.assign("/login");
    throw new Error("Oturum sona ermiş, giriş gerekiyor.");
  }
  if (!r.ok) throw new Error(stripHtml(String(data.detail || `HTTP ${r.status}`)));
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
  llm_provider?: string;
  llm_model?: string;
  failed_count?: number;
  mismatch_count?: number;
}

export interface CommitUnit {
  sha?: string | null;
  short_sha?: string | null;
  message?: string | null;
  author?: string | null;
  jira_ids: string[];
  review_status?: string | null;
  review_comment?: string | null;
  jira_people?: Record<string, { assignee?: string; creator?: string }>;
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

export interface RunEvent {
  created_at: string;
  node: string;
  level: string;
  message: string;
}

export interface RunDetail extends Run {
  final_report?: string | null;
  error?: string | null;
  jira_base_url?: string;
  finished_at?: string | null;
  duration_seconds?: number | null;
  commit_units: CommitUnit[];
  jira_actions: JiraAction[];
  events: RunEvent[];
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
  is_disabled?: boolean;
  created_at?: string;
  disabled_at?: string;
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

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(totalSeconds?: number | null): string {
  if (totalSeconds === undefined || totalSeconds === null) return "—";
  const s = Math.max(0, Math.floor(totalSeconds));
  if (s < 60) return `${s} sn`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} dk ${s % 60} sn`;
  return `${Math.floor(m / 60)} sa ${m % 60} dk`;
}
