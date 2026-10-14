import { useCallback, useEffect, useState } from "react";
import { api, formatDateTime, isAdmin, timeAgo, type Connection } from "../api";
import { StatusBadge } from "../components/badges";
import { toast } from "../components/Toaster";

type Kind = "github" | "jira" | "llm";
type KindTab = "all" | Kind;

const BLANK: Omit<Connection, "id"> = {
  name: "",
  kind: "github",
  base_url: "",
  owner: "",
  email: "",
  token: "",
  project_key: "",
  provider: "ollama",
  model: "",
  temperature: 0.3,
  max_tokens: 2048,
  webhook_secret: "",
  is_default: false,
};

const KIND_LABEL: Record<Kind, string> = { github: "GitHub", jira: "Jira", llm: "LLM Sağlayıcıları" };

function maskEmail(email: string): string {
  const at = email.indexOf("@");
  if (at <= 1) return email || "—";
  return `${email[0]}***${email.slice(at)}`;
}

function initials(name: string): string {
  const clean = name.replace(/[^a-zA-Z0-9_.@-]/g, "").toUpperCase();
  return (clean.slice(0, 2) || "?").padEnd(2, "•");
}

function Icon({ d }: { d: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

const P_EDIT = "M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z";
const P_TRASH = "M3 6h18 M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14z M10 11v6 M14 11v6";
const P_PAUSE = "M9 4v16 M15 4v16";
const P_PLAY = "M6 4l14 8-14 8V4z";
const P_SEARCH = "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M21 21l-4.35-4.35";

function TestBadge({ c }: { c: Connection }) {
  if (c.is_disabled) {
    return <span className="text-xs text-muted">Durduruldu</span>;
  }
  if (!c.last_tested_at) {
    return <span className="text-xs text-muted">—</span>;
  }
  const ok = c.last_test_ok !== false;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono"
      style={
        ok
          ? { background: "rgba(16,185,129,.12)", color: "#34d399" }
          : { background: "rgba(239,68,68,.12)", color: "#f87171" }
      }
    >
      <span
        className="inline-block rounded-full"
        style={{ width: 6, height: 6, background: ok ? "#34d399" : "#f87171" }}
      />
      {ok ? `${c.last_test_status || 200} OK` : `${c.last_test_status || "Hata"}`} · {c.last_latency_ms ?? 0}ms
    </span>
  );
}

export function Settings() {
  const [conns, setConns] = useState<Connection[]>([]);
  const [editing, setEditing] = useState<(Omit<Connection, "id"> & { id?: string }) | null>(null);
  const [form, setForm] = useState(BLANK);
  const [models, setModels] = useState<{ name: string; source?: string }[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [hasSecrets, setHasSecrets] = useState({ token: false, secret: false });
  const [users, setUsers] = useState<{ id: string; username: string; role: string; created_at: string; last_login_at?: string }[]>([]);
  const [newUser, setNewUser] = useState({ username: "", password: "" });
  const [connQuery, setConnQuery] = useState("");
  const [kindTab, setKindTab] = useState<KindTab>("all");
  const [redact, setRedact] = useState(true);

  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([
        api.get<Connection[]>("/api/connections"),
        api.get<{ redact_secrets: boolean }>("/api/settings"),
      ]);
      setConns(c);
      setRedact(s.redact_secrets);
    } catch (e) {
      toast(`Yüklenemedi: ${(e as Error).message}`, false);
    }
    try {
      setUsers(await api.get<{ id: string; username: string; role: string; created_at: string; last_login_at?: string }[]>("/api/auth/users"));
    } catch {
      setUsers([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadModels = useCallback(async () => {
    if (!editing || editing.kind !== "llm") {
      setModels([]);
      return;
    }
    const q = editing.id
      ? `?conn_id=${encodeURIComponent(editing.id)}`
      : `?provider=${encodeURIComponent(editing.provider || "ollama")}`;
    setModelsLoading(true);
    try {
      const list = await api.get<{ name: string; source?: string }[]>(`/api/llm/models${q}`);
      setModels(list);
      if (!form.model && list.length > 0) set("model", list[0].name);
    } catch {
      setModels([]);
    } finally {
      setModelsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing?.id, editing?.kind, editing?.provider]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  useEffect(() => {
    if (!editing) return;
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") setEditing(null);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [editing]);

  function openNew() {
    setForm({ ...BLANK });
    setEditing({ ...BLANK });
    setHasSecrets({ token: false, secret: false });
  }
  function openEdit(c: Connection) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { token: _t, webhook_secret: _w, ...rest } = c;
    setForm({ ...rest, token: "", webhook_secret: "" });
    setEditing({ ...rest, token: "", webhook_secret: "" });
    setHasSecrets({ token: _t === "***masked***", secret: _w === "***masked***" });
  }

  async function save() {
    try {
      if (editing?.id) await api.put(`/api/connections/${editing.id}`, form);
      else await api.post<Connection>("/api/connections", form);
      setEditing(null);
      toast("Kaydedildi.");
      load();
    } catch (e) {
      toast(`Kaydedilemedi: ${(e as Error).message}`, false);
    }
  }

  async function test(id: string) {
    try {
      const r = await api.post<{ ok: boolean; detail?: string; status?: number; latency_ms?: number }>(
        `/api/connections/${id}/test`,
        {}
      );
      toast(`${r.ok ? "✓" : "✗"} ${r.detail || r.status}${r.latency_ms !== undefined ? ` · ${r.latency_ms}ms` : ""}`, r.ok);
      load();
    } catch (e) {
      toast(`✗ ${(e as Error).message}`, false);
    }
  }

  async function toggleConn(c: Connection) {
    try {
      await api.post(`/api/connections/${c.id}/toggle`, {});
      toast(c.is_disabled ? "Bağlantı açıldı." : "Bağlantı kapatıldı.");
      load();
    } catch (e) {
      toast(`Olmadı: ${(e as Error).message}`, false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Silinsin mi?")) return;
    try {
      await api.del(`/api/connections/${id}`);
      load();
    } catch (e) {
      toast(`Silinemedi: ${(e as Error).message}`, false);
    }
  }

  async function toggleRedact(v: boolean) {
    try {
      await api.put("/api/settings", { redact_secrets: v });
      setRedact(v);
    } catch (e) {
      toast(`Kaydedilemedi: ${(e as Error).message}`, false);
    }
  }

  const set = (k: keyof typeof BLANK, v: string | boolean | number) =>
    setForm((f) => {
      const next = { ...f, [k]: v };
      setEditing((e) => (e ? { ...e, [k]: v } : e));
      return next;
    });

  const counts: Record<KindTab, number> = {
    all: conns.length,
    github: conns.filter((c) => c.kind === "github").length,
    jira: conns.filter((c) => c.kind === "jira").length,
    llm: conns.filter((c) => c.kind === "llm").length,
  };
  const q = connQuery.trim().toLowerCase();
  const matchQ = (c: Connection) =>
    !q ||
    c.name.toLowerCase().includes(q) ||
    c.id.toLowerCase().includes(q) ||
    (c.model || "").toLowerCase().includes(q) ||
    (c.base_url || "").toLowerCase().includes(q);
  const shownKinds: Kind[] = (["github", "jira", "llm"] as Kind[]).filter(
    (k) => kindTab === "all" || kindTab === k
  );

  const iconBtn =
    "p-1 rounded text-muted hover:text-ink hover:bg-[#1e293b] transition-colors";
  const iconDanger =
    "p-1 rounded text-bad hover:bg-[rgba(239,68,68,.15)] transition-colors";

  function rowActions(c: Connection) {
    return (
      <div className="inline-flex items-center gap-1">
        <button className="px-2 py-1 rounded text-xs text-muted hover:text-ink hover:bg-[#1e293b] transition-colors" title="Bağlantıyı doğrula" onClick={() => test(c.id)}>
          ⚡ Test
        </button>
        {isAdmin() && (
          <>
            <button className={iconBtn} title="Düzenle" onClick={() => openEdit(c)}>
              <Icon d={P_EDIT} />
            </button>
            <button className={iconBtn} title={c.is_disabled ? "Etkinleştir" : "Pasife al"} onClick={() => toggleConn(c)}>
              <Icon d={c.is_disabled ? P_PLAY : P_PAUSE} />
            </button>
            <button className={iconDanger} title="Sil" onClick={() => remove(c.id)}>
              <Icon d={P_TRASH} />
            </button>
          </>
        )}
      </div>
    );
  }

  function githubRows(rows: Connection[]) {
    return (
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead>
            <tr className="text-left text-xs text-muted uppercase">
              <th className="px-4 py-2.5 font-semibold">Bağlantı Adı</th>
              <th className="px-4 py-2.5 font-semibold">Tür &amp; Adres</th>
              <th className="px-4 py-2.5 font-semibold">Auth Durumu</th>
              <th className="px-4 py-2.5 font-semibold">Webhook</th>
              <th className="px-4 py-2.5 font-semibold">Test Sonucu</th>
              <th className="px-4 py-2.5 font-semibold">Son Senkronizasyon</th>
              <th className="px-4 py-2.5 font-semibold text-right">İşlemler</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-3 text-xs text-muted">
                  Kayıt yok.
                </td>
              </tr>
            )}
            {rows.map((c) => (
              <tr key={c.id} className={`hover:bg-[#1e293b]/40 transition-colors ${c.is_disabled ? "opacity-50" : ""}`}>
                <td className="px-4 py-3">
                  <span className="font-semibold">
                    <span
                      className="inline-block rounded-full mr-2"
                      style={{ width: 8, height: 8, background: c.is_disabled ? "#64748b" : "#10b981" }}
                    />
                    {c.name}
                    {c.is_default && <span className="text-xs text-ok"> · varsayılan</span>}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs font-mono text-muted">
                  {c.base_url} <span className="text-faint">/</span> org: {c.owner || "—"}
                </td>
                <td className="px-4 py-3">
                  {c.token ? (
                    <span className="inline-flex items-center gap-1.5 text-xs font-mono" style={{ color: "#34d399" }}>
                      <span className="inline-block rounded-full" style={{ width: 6, height: 6, background: "#34d399" }} />
                      Token: Kayıtlı
                    </span>
                  ) : (
                    <span className="text-xs text-muted">Kayıtlı Değil</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs font-mono text-muted">
                  {c.webhook_secret ? (c.is_disabled ? "Pasif" : "Aktif") : "Yok"}
                </td>
                <td className="px-4 py-3">
                  <TestBadge c={c} />
                </td>
                <td className="px-4 py-3 text-xs font-mono text-muted">
                  {c.last_tested_at ? timeAgo(c.last_tested_at) : c.created_at ? formatDateTime(c.created_at) : "—"}
                </td>
                <td className="px-4 py-3 text-right">{rowActions(c)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function jiraRows(rows: Connection[]) {
    return (
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead>
            <tr className="text-left text-xs text-muted uppercase">
              <th className="px-4 py-2.5 font-semibold">Entegrasyon</th>
              <th className="px-4 py-2.5 font-semibold">Hedef Site &amp; Proje</th>
              <th className="px-4 py-2.5 font-semibold">Yetkili Hesap</th>
              <th className="px-4 py-2.5 font-semibold">Token Durumu</th>
              <th className="px-4 py-2.5 font-semibold">Test / Senkronizasyon</th>
              <th className="px-4 py-2.5 font-semibold text-right">İşlemler</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-3 text-xs text-muted">
                  Kayıt yok.
                </td>
              </tr>
            )}
            {rows.map((c) => (
              <tr key={c.id} className={`hover:bg-[#1e293b]/40 transition-colors ${c.is_disabled ? "opacity-50" : ""}`}>
                <td className="px-4 py-3">
                  <span className="font-semibold">
                    <span
                      className="inline-block rounded-full mr-2"
                      style={{ width: 8, height: 8, background: c.is_disabled ? "#64748b" : "#10b981" }}
                    />
                    {c.name}
                    {c.is_default && <span className="text-xs text-ok"> · varsayılan</span>}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs font-mono">
                  {c.base_url}{" "}
                  {c.project_key && (
                    <span className="ml-1 px-1.5 py-0.5 rounded" style={{ background: "#0f172a", color: "#818cf8" }}>
                      PROJE: {c.project_key}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs font-mono text-muted">{maskEmail(c.email)}</td>
                <td className="px-4 py-3">
                  {c.token ? (
                    <span className="inline-flex items-center gap-1.5 text-xs font-mono" style={{ color: "#34d399" }}>
                      <span className="inline-block rounded-full" style={{ width: 6, height: 6, background: "#34d399" }} />
                      API Token: Kayıtlı
                    </span>
                  ) : (
                    <span className="text-xs text-muted">Kayıtlı Değil</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <TestBadge c={c} />
                </td>
                <td className="px-4 py-3 text-right">{rowActions(c)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function llmRows(rows: Connection[]) {
    return (
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead>
            <tr className="text-left text-xs text-muted uppercase">
              <th className="px-4 py-2.5 font-semibold">Sağlayıcı &amp; Model</th>
              <th className="px-4 py-2.5 font-semibold">Uç Nokta / Adres</th>
              <th className="px-4 py-2.5 font-semibold">Sıcaklık &amp; Token Limiti</th>
              <th className="px-4 py-2.5 font-semibold">Ping &amp; Güvenlik</th>
              <th className="px-4 py-2.5 font-semibold">API Token</th>
              <th className="px-4 py-2.5 font-semibold text-right">İşlemler</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-3 text-xs text-muted">
                  Kayıt yok.
                </td>
              </tr>
            )}
            {rows.map((c) => (
              <tr key={c.id} className={`hover:bg-[#1e293b]/40 transition-colors ${c.is_disabled ? "opacity-50" : ""}`}>
                <td className="px-4 py-3">
                  <span className="font-semibold">
                    <span
                      className="inline-block rounded-full mr-2"
                      style={{ width: 8, height: 8, background: c.is_disabled ? "#64748b" : "#10b981" }}
                    />
                    {c.name}
                    {c.is_default && <span className="text-xs text-ok"> · varsayılan</span>}
                  </span>
                  <div className="text-xs font-mono text-muted ml-4">{c.model || "—"}</div>
                </td>
                <td className="px-4 py-3 text-xs font-mono text-muted">{c.base_url || "—"}</td>
                <td className="px-4 py-3 text-xs font-mono text-muted">
                  Temp: {c.temperature} • Max: {c.max_tokens}
                </td>
                <td className="px-4 py-3">
                  <TestBadge c={c} />
                </td>
                <td className="px-4 py-3 text-xs font-mono text-muted">
                  {c.token ? (
                    <span className="inline-flex items-center gap-1.5" style={{ color: "#34d399" }}>
                      <span className="inline-block rounded-full" style={{ width: 6, height: 6, background: "#34d399" }} />
                      API Key: Kayıtlı
                    </span>
                  ) : (
                    "Gerekmiyor"
                  )}
                </td>
                <td className="px-4 py-3 text-right">{rowActions(c)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">Bağlantılar ve Entegrasyonlar</h1>
            <StatusBadge status="running" />
          </div>
          <p className="text-sm text-muted">
            GitHub depoları, Jira siteleri ve LLM uç noktaları için merkezi bağlantı ağı.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            className="flex items-center gap-2 px-3 py-1.5 rounded card text-xs text-muted"
            onClick={() => isAdmin() && toggleRedact(!redact)}
            disabled={!isAdmin()}
            title="Secret redaksiyonu (LLM'e giden diff'lerdeki anahtarlar maskelenir)"
          >
            Secret Redaksiyonu
            <span
              className="inline-block w-8 h-4 rounded-full relative transition-colors"
              style={{ background: redact ? "#494bd6" : "#334155" }}
            >
              <span
                className="block w-3 h-3 rounded-full absolute top-0.5 transition-all"
                style={{ background: "#f8fafc", left: redact ? undefined : "2px", right: redact ? "2px" : undefined }}
              />
            </span>
          </button>
          {isAdmin() && (
            <button className="btn-primary" onClick={openNew}>
              + Yeni Bağlantı
            </button>
          )}
        </div>
      </div>

      <div className="card p-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-1 overflow-x-auto">
          {(
            [
              ["all", "Tümü"],
              ["github", "GitHub"],
              ["jira", "Jira"],
              ["llm", "LLM Sağlayıcıları"],
            ] as [KindTab, string][]
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setKindTab(v)}
              className={`px-3 py-1 rounded text-xs ${kindTab === v ? "font-semibold" : "text-muted"}`}
              style={kindTab === v ? { background: "#2d3449", color: "#fff" } : undefined}
            >
              {label} <span className="font-mono text-faint">{counts[v]}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 px-2">
          <Icon d={P_SEARCH} />
          <input
            className="bg-transparent border-none text-sm focus:outline-none w-full sm:w-56"
            placeholder="Bağlantı veya uç nokta ara…"
            value={connQuery}
            onChange={(e) => setConnQuery(e.target.value)}
          />
          <kbd className="px-1.5 py-0.5 rounded text-[10px] font-mono text-faint" style={{ border: "1px solid #334155" }}>
            ⌘K
          </kbd>
        </div>
      </div>

      {shownKinds.map((kind) => (
        <div key={kind}>
          <h2 className="text-sm font-semibold mb-1">
            {kind === "github" && "VCS & Kod Depoları"}
            {kind === "jira" && "Atlassian / Jira Entegrasyonları"}
            {kind === "llm" && "LLM & Yapay Zeka Çıkarım Sağlayıcıları"}
          </h2>
          {kind === "github" && githubRows(conns.filter((c) => c.kind === "github" && matchQ(c)))}
          {kind === "jira" && jiraRows(conns.filter((c) => c.kind === "jira" && matchQ(c)))}
          {kind === "llm" && llmRows(conns.filter((c) => c.kind === "llm" && matchQ(c)))}
        </div>
      ))}

      {isAdmin() && users.length > 0 && (
        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <b className="text-sm">Admin Konsol Erişim &amp; Rol Yönetimi</b>
              <div className="text-xs text-muted">Kayıt davet usulüdür; yeni hesabı buradan açarsın.</div>
            </div>
            <StatusBadge status="success" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr className="text-left text-xs text-muted uppercase">
                  <th className="px-3 py-2 font-semibold">Kullanıcı</th>
                  <th className="px-3 py-2 font-semibold">Rol / Yetki Kapsamı</th>
                  <th className="px-3 py-2 font-semibold">Son Giriş</th>
                  <th className="px-3 py-2 font-semibold">Oluşturuldu</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-[#1e293b]/40 transition-colors">
                    <td className="px-3 py-2">
                      <span
                        className="inline-flex items-center justify-center rounded-full mr-2 text-[10px] font-mono"
                        style={{ width: 24, height: 24, background: "#2d3449", color: "#818cf8" }}
                      >
                        {initials(u.username)}
                      </span>
                      <span className="font-mono">{u.username}</span>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        className="input sm:max-w-xs"
                        value={u.role}
                        onChange={async (e) => {
                          try {
                            await api.put(`/api/auth/users/${u.id}`, { role: e.target.value });
                            toast("Rol güncellendi.");
                            load();
                          } catch (err) {
                            toast(`Olmadı: ${(err as Error).message}`, false);
                          }
                        }}
                      >
                        <option value="viewer">Viewer (Salt Okunur)</option>
                        <option value="approver">Approver (Onay Yetkilisi)</option>
                        <option value="admin">Admin (Tam Yetki)</option>
                      </select>
                    </td>
                    <td className="px-3 py-2 text-xs font-mono text-muted">
                      {u.last_login_at ? timeAgo(u.last_login_at) : "—"}
                    </td>
                    <td className="px-3 py-2 text-xs font-mono text-muted">
                      {formatDateTime(u.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid sm:grid-cols-4 gap-2">
            <input
              className="input font-mono"
              placeholder="kullanıcı adı"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
            />
            <input
              className="input font-mono"
              type="password"
              placeholder="parola (8+)"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            />
            <span className="text-xs text-muted self-center">Yeni hesap viewer açılır.</span>
            <button
              className="btn-primary"
              onClick={async () => {
                try {
                  await api.post("/api/auth/register", {
                    username: newUser.username.trim(),
                    password: newUser.password,
                  });
                  setNewUser({ username: "", password: "" });
                  toast("Kullanıcı açıldı (viewer).");
                  load();
                } catch (err) {
                  toast(`Açılamadı: ${(err as Error).message}`, false);
                }
              }}
            >
              + Ekle
            </button>
          </div>
        </div>
      )}

      <div className="card p-4 text-xs text-muted font-mono">
        Webhook endpoint: {window.location.origin}/api/webhooks/github
      </div>

      {editing && (
        <>
          <div
            className="fixed inset-0 z-40"
            style={{ background: "rgba(2,6,23,.6)" }}
            onClick={() => setEditing(null)}
          />
          <aside className="fixed top-0 right-0 bottom-0 z-50 w-full sm:max-w-md overflow-y-auto card !rounded-none p-4 space-y-3">
            <div className="flex items-center justify-between">
              <b className="text-sm">Hızlı Yapılandırma &amp; Bağlantı Önizleme</b>
              <span className="text-xs font-mono text-faint">Esc</span>
            </div>
            <div className="flex gap-1 p-1 rounded card">
              {(["github", "jira", "llm"] as Kind[]).map((k) => (
                <button
                  key={k}
                  className={`flex-1 py-1 rounded text-xs ${form.kind === k ? "font-semibold" : "text-muted"}`}
                  style={form.kind === k ? { background: "#494bd6", color: "#fff" } : undefined}
                  onClick={() => set("kind", k)}
                >
                  {k === "llm" ? "LLM Sağlayıcı" : KIND_LABEL[k]}
                </button>
              ))}
            </div>
            <div>
              <label className="block text-xs mb-1 text-muted">Ad</label>
              <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs mb-1 text-muted">Base URL</label>
              <input className="input font-mono" value={form.base_url} onChange={(e) => set("base_url", e.target.value)} />
            </div>
            {form.kind === "github" && (
              <div>
                <label className="block text-xs mb-1 text-muted">Owner</label>
                <input className="input" value={form.owner} onChange={(e) => set("owner", e.target.value)} />
              </div>
            )}
            {form.kind === "jira" && (
              <>
                <div>
                  <label className="block text-xs mb-1 text-muted">E-posta</label>
                  <input className="input" value={form.email} onChange={(e) => set("email", e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs mb-1 text-muted">Proje anahtarı (örn. TTA)</label>
                  <input
                    className="input font-mono"
                    value={form.project_key}
                    onChange={(e) => set("project_key", e.target.value)}
                  />
                </div>
              </>
            )}
            {form.kind === "llm" && (
              <>
                <div>
                  <label className="block text-xs mb-1 text-muted">Sağlayıcı (Provider)</label>
                  <div className="grid grid-cols-4 gap-1">
                    {(["openai", "anthropic", "ollama", "gemini"] as string[]).map((p) => (
                      <button
                        key={p}
                        type="button"
                        className={`py-1.5 px-2 rounded text-xs font-mono text-center ${form.provider === p ? "font-semibold" : "text-muted"}`}
                        style={form.provider === p ? { background: "#2d3449", color: "#fff" } : { background: "#0f172a" }}
                        onClick={() => set("provider", p)}
                      >
                        {p === "openai" ? "OpenAI" : p === "anthropic" ? "Anthropic" : p === "ollama" ? "Ollama" : "Gemini"}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs text-muted">Model Seçimi</label>
                    <button
                      type="button"
                      className="text-xs text-accent-soft"
                      onClick={loadModels}
                      disabled={modelsLoading}
                    >
                      {modelsLoading ? "…" : "↻ Modelleri Yenile"}
                    </button>
                  </div>
                  {models.length > 0 ? (
                    <select
                      className="input font-mono"
                      value={form.model}
                      onChange={(e) => set("model", e.target.value)}
                    >
                      {!models.some((m) => m.name === form.model) && (
                        <option value={form.model}>{form.model || "— seç —"}</option>
                      )}
                      {models.map((m) => (
                        <option key={m.name} value={m.name}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      className="input font-mono"
                      placeholder="örn. qwen3:14b"
                      value={form.model}
                      onChange={(e) => set("model", e.target.value)}
                    />
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs mb-1 text-muted">Sıcaklık</label>
                    <input
                      className="input"
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={form.temperature}
                      onChange={(e) => set("temperature", parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs mb-1 text-muted">Max token</label>
                    <input
                      className="input"
                      type="number"
                      value={form.max_tokens}
                      onChange={(e) => set("max_tokens", parseInt(e.target.value, 10) || 2048)}
                    />
                  </div>
                </div>
              </>
            )}
            <div>
              <span className="flex items-center justify-between text-xs mb-1">
                <span className="text-muted">Token {form.kind === "llm" ? "/ Secret Key" : ""} (boş = değişmez)</span>
                {hasSecrets.token ? (
                  <span style={{ color: "#10b981" }}>● Kayıtlı</span>
                ) : (
                  <span className="text-muted">○ Kayıtlı değil</span>
                )}
              </span>
              <input
                className="input font-mono"
                type="password"
                value={form.token}
                onChange={(e) => set("token", e.target.value)}
              />
              <span className="block mt-1 text-xs text-muted">
                Boş bırakırsan mevcut şifreli anahtar korunur, değişmez.
              </span>
            </div>
            {form.kind === "github" && (
              <div>
                <span className="flex items-center justify-between text-xs mb-1">
                  <span className="text-muted">Webhook secret (boş = değişmez)</span>
                  {hasSecrets.secret ? (
                    <span style={{ color: "#10b981" }}>● Kayıtlı</span>
                  ) : (
                    <span className="text-muted">○ Kayıtlı değil</span>
                  )}
                </span>
                <input
                  className="input font-mono"
                  type="password"
                  value={form.webhook_secret}
                  onChange={(e) => set("webhook_secret", e.target.value)}
                />
              </div>
            )}
            <label className="flex items-center gap-2 text-xs text-muted">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(e) => set("is_default", e.target.checked)}
              />
              Varsayılan yap
            </label>
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs font-mono text-faint">[Esc] Kapat</span>
              <div className="flex gap-2">
                <button className="btn-ghost" onClick={() => setEditing(null)}>
                  İptal
                </button>
                {isAdmin() && (
                  <button className="btn-primary" onClick={save}>
                    Değişiklikleri Kaydet
                  </button>
                )}
              </div>
            </div>
          </aside>
        </>
      )}
    </>
  );
}
