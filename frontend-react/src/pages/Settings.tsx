import { useCallback, useEffect, useState } from "react";
import { api, formatDateTime, isAdmin, timeAgo, type Connection } from "../api";
import { toast } from "../components/Toaster";

type Kind = "github" | "jira" | "llm";

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
type KindTab = "all" | Kind;

// Ayrı ayrı, bağımsız varsayılan yapılandırma şablonları
export const GITHUB_DEFAULTS: Omit<Connection, "id"> = {
  name: "GitHub Enterprise Core",
  kind: "github",
  base_url: "https://api.github.com",
  owner: "devops-agentic-org",
  email: "",
  token: "",
  project_key: "",
  provider: "",
  model: "",
  temperature: 0.3,
  max_tokens: 2048,
  webhook_secret: "whsec_09187a6b2c5d4e1f8e9a",
  is_default: false,
};

export const JIRA_DEFAULTS: Omit<Connection, "id"> = {
  name: "Jira Cloud Prod",
  kind: "jira",
  base_url: "https://agentic-devops.atlassian.net",
  owner: "",
  email: "automation-bot@company.io",
  token: "",
  project_key: "CLOUD",
  provider: "",
  model: "",
  temperature: 0.3,
  max_tokens: 2048,
  webhook_secret: "",
  is_default: false,
};

export const LLM_DEFAULTS: Record<"openai" | "anthropic" | "ollama" | "gemini", Omit<Connection, "id">> = {
  openai: {
    name: "OpenAI Gateway",
    kind: "llm",
    provider: "openai",
    model: "gpt-4o",
    base_url: "https://api.openai.com/v1",
    temperature: 0.2,
    max_tokens: 4096,
    token: "",
    owner: "",
    email: "",
    project_key: "",
    webhook_secret: "",
    is_default: false,
  },
  anthropic: {
    name: "Anthropic Claude Prod",
    kind: "llm",
    provider: "anthropic",
    model: "claude-3-7-sonnet",
    base_url: "https://api.anthropic.com/v1",
    temperature: 0.3,
    max_tokens: 8000,
    token: "",
    owner: "",
    email: "",
    project_key: "",
    webhook_secret: "",
    is_default: false,
  },
  ollama: {
    name: "Ollama Internal Cluster",
    kind: "llm",
    provider: "ollama",
    model: "llama3.3:70b",
    base_url: "http://localhost:11434",
    temperature: 0.1,
    max_tokens: 8192,
    token: "",
    owner: "",
    email: "",
    project_key: "",
    webhook_secret: "",
    is_default: false,
  },
  gemini: {
    name: "Google Gemini Engine",
    kind: "llm",
    provider: "gemini",
    model: "gemini-2.0-flash",
    base_url: "https://generativelanguage.googleapis.com",
    temperature: 0.2,
    max_tokens: 4096,
    token: "",
    owner: "",
    email: "",
    project_key: "",
    webhook_secret: "",
    is_default: false,
  },
};

export function getDefaultByKind(kind: Kind, provider: string = "openai"): Omit<Connection, "id"> {
  if (kind === "github") {
    return { ...GITHUB_DEFAULTS };
  }
  if (kind === "jira") {
    return { ...JIRA_DEFAULTS };
  }
  const p = (provider in LLM_DEFAULTS ? provider : "openai") as keyof typeof LLM_DEFAULTS;
  return { ...LLM_DEFAULTS[p] };
}

function maskEmail(email: string): string {
  const at = email.indexOf("@");
  if (at <= 1) return email || "—";
  return `${email[0]}***${email.slice(at)}`;
}

function initials(name: string): string {
  const clean = name.replace(/[^a-zA-Z0-9_.@-]/g, "").toUpperCase();
  return (clean.slice(0, 2) || "?").padEnd(2, "•");
}

function TestBadge({ c }: { c: Connection }) {
  if (c.is_disabled) {
    return (
      <span className="px-2 py-0.5 rounded bg-surface-container font-mono text-xs text-outline">
        Durduruldu
      </span>
    );
  }
  if (!c.last_tested_at) {
    return <span className="text-xs text-outline font-mono">—</span>;
  }
  const ok = c.last_test_ok !== false;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono tracking-wide ${
        ok
          ? "bg-tertiary-container/30 text-tertiary"
          : "bg-error-container/40 text-error"
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          ok ? "bg-tertiary" : "bg-error"
        }`}
      />
      {ok ? `${c.last_test_status || 200} OK` : `${c.last_test_status || "Hata"}`}
      {c.last_latency_ms !== undefined ? ` • ${c.last_latency_ms}ms` : ""}
    </span>
  );
}

export function Settings() {
  const [conns, setConns] = useState<Connection[]>([]);
  const [editing, setEditing] = useState<(Omit<Connection, "id"> & { id?: string }) | null>(null);
  const [form, setForm] = useState(GITHUB_DEFAULTS);
  const [models, setModels] = useState<{ name: string; source?: string }[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [hasSecrets, setHasSecrets] = useState({ token: false, secret: false });
  const [tokenModified, setTokenModified] = useState(false);
  const [secretModified, setSecretModified] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showWebhookSecret, setShowWebhookSecret] = useState(false);
  const [users, setUsers] = useState<
    { id: string; username: string; role: string; created_at: string; email?: string; last_login_at?: string }[]
  >([]);
  const [newUser, setNewUser] = useState({ username: "", email: "", role: "viewer" });
  const [freshPassword, setFreshPassword] = useState<{ username: string; password: string } | null>(null);
  const [connQuery, setConnQuery] = useState("");
  const [kindTab, setKindTab] = useState<KindTab>("all");
  const [redact, setRedact] = useState(true);
  const [apiVersion, setApiVersion] = useState("");

  const load = useCallback(async () => {
    try {
      const [c, s, h] = await Promise.all([
        api.get<Connection[]>("/api/connections"),
        api.get<{ redact_secrets: boolean }>("/api/settings"),
        api.get<{ version: string }>("/api/health"),
      ]);
      setConns(c);
      setRedact(s.redact_secrets);
      setApiVersion(h.version || "");
    } catch (e) {
      toast(`Yüklenemedi: ${(e as Error).message}`, false);
    }
    try {
      setUsers(
        await api.get<
          { id: string; username: string; role: string; created_at: string; email?: string; last_login_at?: string }[]
        >("/api/auth/users")
      );
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
      : `?provider=${encodeURIComponent(editing.provider || "openai")}`;
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

  function openNew(kind?: Kind) {
    const targetKind: Kind = kind || (kindTab === "all" ? "github" : kindTab);
    const initialForm = getDefaultByKind(targetKind, "openai");
    setForm(initialForm);
    setEditing(initialForm);
    setShowPassword(false);
    setShowWebhookSecret(false);
    setTokenModified(false);
    setSecretModified(false);
    setHasSecrets({ token: false, secret: false });
  }

  function openEdit(c: Connection) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { token: _t, webhook_secret: _w, ...rest } = c;
    setForm({ ...rest, token: "", webhook_secret: "" });
    setEditing({ ...rest, token: "", webhook_secret: "" });
    setShowPassword(false);
    setShowWebhookSecret(false);
    setTokenModified(false);
    setSecretModified(false);
    setHasSecrets({ token: _t === "***masked***", secret: _w === "***masked***" });
  }

  function switchTab(newKind: Kind) {
    if (form.kind === newKind) return;

    if (!editing?.id) {
      // Yeni bağlantı ekleme modu: Seçilen türe ait ayrı varsayılan değerleri yükle
      const nextForm = getDefaultByKind(newKind, form.provider || "openai");
      setForm(nextForm);
      setEditing(nextForm);
      setHasSecrets({ token: false, secret: false });
      setTokenModified(false);
      setSecretModified(false);
    } else {
      // Düzenleme modu: Tür değiştirildiğinde mevcut ID korunur
      set("kind", newKind);
    }
  }

  function switchProvider(p: "openai" | "anthropic" | "ollama" | "gemini") {
    const pDefaults = LLM_DEFAULTS[p];
    if (!pDefaults) return;

    setForm((prev) => {
      const isOriginal = editing?.id && editing.provider === p;
      return {
        ...prev,
        provider: p,
        name: isOriginal ? editing.name : pDefaults.name,
        base_url: isOriginal ? editing.base_url : pDefaults.base_url,
        model: isOriginal ? editing.model : pDefaults.model,
        temperature: isOriginal ? editing.temperature : pDefaults.temperature,
        max_tokens: isOriginal ? editing.max_tokens : pDefaults.max_tokens,
      };
    });
    setEditing((prev) => (prev ? { ...prev, provider: p } : prev));
  }

  function resetToDefaults() {
    if (form.kind === "github") {
      setForm((prev) => ({
        ...prev,
        name: GITHUB_DEFAULTS.name,
        base_url: GITHUB_DEFAULTS.base_url,
        owner: GITHUB_DEFAULTS.owner,
        webhook_secret: GITHUB_DEFAULTS.webhook_secret,
      }));
      toast("GitHub varsayılan değerleri yüklendi.");
    } else if (form.kind === "jira") {
      setForm((prev) => ({
        ...prev,
        name: JIRA_DEFAULTS.name,
        base_url: JIRA_DEFAULTS.base_url,
        email: JIRA_DEFAULTS.email,
        project_key: JIRA_DEFAULTS.project_key,
      }));
      toast("Jira varsayılan değerleri yüklendi.");
    } else {
      const p = (form.provider in LLM_DEFAULTS ? form.provider : "openai") as keyof typeof LLM_DEFAULTS;
      const pDef = LLM_DEFAULTS[p];
      setForm((prev) => ({
        ...prev,
        name: pDef.name,
        base_url: pDef.base_url,
        model: pDef.model,
        temperature: pDef.temperature,
        max_tokens: pDef.max_tokens,
      }));
      toast(`${p.toUpperCase()} varsayılan değerleri yüklendi.`);
    }
  }

  async function setDefaultConnection(c: Connection) {
    try {
      await api.put(`/api/connections/${c.id}`, {
        name: c.name,
        kind: c.kind,
        base_url: c.base_url,
        owner: c.owner,
        email: c.email,
        token: "",
        project_key: c.project_key,
        provider: c.provider,
        model: c.model,
        temperature: c.temperature,
        max_tokens: c.max_tokens,
        webhook_secret: "",
        is_default: true,
      });
      const kindLabel = c.kind === "github" ? "GitHub" : c.kind === "jira" ? "Jira" : "LLM";
      toast(`"${c.name}" varsayılan ${kindLabel} bağlantısı olarak ayarlandı.`);
      load();
    } catch (e) {
      toast(`Varsayılan ayarlanamadı: ${(e as Error).message}`, false);
    }
  }

  async function save() {
    try {
      const payload = { ...form };
      // Düzenleme sırasında token değiştirilmediyse backend'e boş gönder, şifreli anahtar korunsun
      if (editing?.id && !tokenModified && hasSecrets.token) {
        payload.token = "";
      }
      if (editing?.id && !secretModified && hasSecrets.secret) {
        payload.webhook_secret = "";
      }

      if (!payload.name) {
        payload.name =
          payload.kind === "github"
            ? `GitHub (${payload.owner || "Default"})`
            : payload.kind === "jira"
            ? "Jira Cloud"
            : `${(payload.provider || "LLM").toUpperCase()} Gateway`;
      }

      if (editing?.id) {
        await api.put(`/api/connections/${editing.id}`, payload);
      } else {
        await api.post<Connection>("/api/connections", payload);
      }
      setEditing(null);
      toast("Bağlantı başarıyla kaydedildi.");
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
      toast(
        `${r.ok ? "✓" : "✗"} ${r.detail || r.status}${r.latency_ms !== undefined ? ` • ${r.latency_ms}ms` : ""}`,
        r.ok
      );
      load();
    } catch (e) {
      toast(`✗ ${(e as Error).message}`, false);
    }
  }

  async function toggleConn(c: Connection) {
    try {
      await api.post(`/api/connections/${c.id}/toggle`, {});
      toast(c.is_disabled ? "Bağlantı etkinleştirildi." : "Bağlantı pasife alındı.");
      load();
    } catch (e) {
      toast(`İşlem başarısız: ${(e as Error).message}`, false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Bu bağlantıyı silmek istediğinize emin misiniz?")) return;
    try {
      await api.del(`/api/connections/${id}`);
      toast("Bağlantı silindi.");
      load();
    } catch (e) {
      toast(`Silinemedi: ${(e as Error).message}`, false);
    }
  }

  async function toggleRedact(v: boolean) {
    try {
      await api.put("/api/settings", { redact_secrets: v });
      setRedact(v);
      toast(v ? "Secret redaksiyonu etkinleştirildi." : "Secret redaksiyonu kapatıldı.");
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
    (c.base_url || "").toLowerCase().includes(q) ||
    (c.owner || "").toLowerCase().includes(q);

  const shownKinds: Kind[] = (["github", "jira", "llm"] as Kind[]).filter(
    (k) => kindTab === "all" || kindTab === k
  );

  function rowActions(c: Connection) {
    return (
      <div className="inline-flex items-center gap-1 justify-end">
        <button
          className="px-2 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface font-medium text-xs transition-colors flex items-center gap-1"
          title="Bağlantıyı doğrula"
          onClick={() => test(c.id)}
        >
          <span>⚡</span>
          <span>Test</span>
        </button>
        {isAdmin() && (
          <>
            <button
              className="p-1 rounded hover:bg-surface-container text-outline hover:text-on-surface transition-colors"
              title="Düzenle"
              onClick={() => openEdit(c)}
            >
              <span className="material-symbols-outlined text-[16px]">edit</span>
            </button>
            <button
              className="p-1 rounded hover:bg-surface-container text-outline hover:text-on-surface transition-colors"
              title={c.is_disabled ? "Etkinleştir" : "Pasife al"}
              onClick={() => toggleConn(c)}
            >
              <span className="material-symbols-outlined text-[16px]">
                {c.is_disabled ? "play_arrow" : "pause"}
              </span>
            </button>
            {!c.is_default && (
              <button
                className="p-1 rounded hover:bg-surface-container text-outline hover:text-on-surface transition-colors"
                title="Varsayılan yap"
                onClick={() => setDefaultConnection(c)}
              >
                <span className="material-symbols-outlined text-[16px]">star</span>
              </button>
            )}
            <button
              className="p-1 rounded hover:bg-error-container/40 text-error transition-colors"
              title="Sil"
              onClick={() => remove(c.id)}
            >
              <span className="material-symbols-outlined text-[16px]">delete</span>
            </button>
          </>
        )}
      </div>
    );
  }

  // Standart API key önizleme değeri (SAHTE anahtar ASLA gösterilmez;
  // Göster'e basınca gerçek değer tek seferlik uçtan çekilir)
  const isKeySaved = hasSecrets.token;
  const currentKeyDisplay =
    tokenModified || !isKeySaved ? form.token : "••••••••••••";

  return (
    <div className="flex flex-col w-full space-y-6 pb-12 text-on-surface">
      {/* Top Command & Status Bar */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-2xl font-bold tracking-tight text-on-surface">
                Bağlantılar ve Entegrasyonlar
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-tertiary-container/30 text-tertiary font-mono text-[11px] tracking-wide uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse" />
                FASTAPI v{apiVersion || "?"} • AKTİF
              </span>
            </div>
            <p className="text-sm text-on-surface-variant max-w-3xl">
              FastAPI mikroservisleri, VCS depoları ve LLM çıkarım uç noktaları için merkezi oturum &amp; gizli anahtar ağı.
            </p>
          </div>

          {/* Global Actions */}
          <div className="flex items-center gap-3 flex-wrap self-start lg:self-auto">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-low border border-outline-variant/30 shadow-sm cursor-pointer select-none"
              onClick={() => isAdmin() && toggleRedact(!redact)}
              title="Secret Redaksiyonu (LLM isteklerindeki gizli anahtarlar maskelenir)"
            >
              <span className="material-symbols-outlined text-outline text-[18px]">key</span>
              <span className="text-xs text-on-surface-variant">Secret Redaksiyonu</span>
              <button
                className={`w-8 h-4 rounded-full relative transition-colors focus:outline-none ${
                  redact ? "bg-primary-container" : "bg-surface-container-highest"
                }`}
                type="button"
                aria-checked={redact}
              >
                <span
                  className={`block w-3 h-3 bg-surface-container-lowest rounded-full absolute top-0.5 transition-transform ${
                    redact ? "right-0.5 translate-x-0" : "left-0.5 -translate-x-0"
                  }`}
                />
              </button>
            </div>

            {isAdmin() && (
              <button
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-container hover:bg-primary-container/90 text-on-primary-container font-semibold text-sm rounded shadow-sm transition-all"
                onClick={() => openNew("llm")}
              >
                <span className="material-symbols-outlined text-[18px]">add_circle</span>
                <span>+ Yeni Bağlantı Ekle</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter Bar & Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface-container-low border border-outline-variant/20 p-2 rounded">
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
                className={`px-3 py-1 rounded text-xs transition-colors flex items-center gap-1.5 ${
                  kindTab === v
                    ? "bg-surface-container-highest text-on-surface font-semibold shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                }`}
              >
                <span>{label}</span>
                <span className="font-mono text-[11px] text-outline">
                  {counts[v]}
                </span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 px-3 py-1 bg-surface-container border border-outline-variant/30 rounded w-full sm:w-64">
            <span className="material-symbols-outlined text-outline text-[16px]">search</span>
            <input
              className="bg-transparent border-none text-on-surface placeholder:text-outline text-xs focus:outline-none w-full"
              placeholder="Bağlantı veya uç nokta ara..."
              type="text"
              value={connQuery}
              onChange={(e) => setConnQuery(e.target.value)}
            />
            <span className="px-1.5 py-0.5 rounded bg-surface-container-high text-outline font-mono text-[10px]">
              ⌘K
            </span>
          </div>
        </div>
      </div>

      {/* Tables by Category */}
      {shownKinds.map((kind) => {
        const rows = conns.filter((c) => c.kind === kind && matchQ(c));

        if (kind === "github") {
          return (
            <div key="github" className="flex flex-col">
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">source</span>
                  <h2 className="text-base font-semibold text-on-surface">
                    VCS &amp; Kod Depoları (GitHub Enterprise)
                  </h2>
                </div>
                <span className="font-mono text-xs text-outline">Cluster Sync: Auto-Poll (30s)</span>
              </div>
              <div className="overflow-x-auto rounded bg-surface-container-low border border-outline-variant/20 shadow-sm">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-surface-container text-outline uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Bağlantı Adı</th>
                      <th className="py-2.5 px-4">Tür &amp; Adres</th>
                      <th className="py-2.5 px-4">Auth Durumu</th>
                      <th className="py-2.5 px-4">Webhook</th>
                      <th className="py-2.5 px-4">Test Sonucu</th>
                      <th className="py-2.5 px-4">Son Senkronizasyon</th>
                      <th className="py-2.5 px-4 text-right">İşlemler</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10 text-on-surface">
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-4 px-4 text-center text-outline">
                          Eşleşen GitHub bağlantısı bulunamadı.
                        </td>
                      </tr>
                    ) : (
                      rows.map((c) => (
                        <tr
                          key={c.id}
                          className={`hover:bg-surface-container-high/40 transition-colors ${
                            c.is_disabled ? "opacity-50" : ""
                          }`}
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  c.is_disabled ? "bg-outline" : "bg-tertiary"
                                }`}
                              />
                              <span className="font-medium text-on-surface">{c.name}</span>
                              {c.is_default && (
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-container text-tertiary font-mono">
                                  varsayılan
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono text-on-surface-variant">
                            <span>{c.base_url || "github.com"}</span>
                            {c.owner && (
                              <>
                                <span className="text-outline mx-1">/</span>
                                <span className="text-secondary">org: {c.owner}</span>
                              </>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {c.token ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container font-mono text-tertiary">
                                <span className="w-1.5 h-1.5 rounded-full bg-tertiary" /> Token: Kayıtlı
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded bg-surface-container-high font-mono text-outline">
                                Kayıtlı Değil
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded font-mono ${
                                c.webhook_secret
                                  ? "bg-surface-container text-on-surface-variant"
                                  : "text-outline"
                              }`}
                            >
                              {c.webhook_secret ? (c.is_disabled ? "Pasif" : "Aktif") : "Yok"}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <TestBadge c={c} />
                          </td>
                          <td className="py-3 px-4 font-mono text-outline">
                            {c.last_tested_at
                              ? timeAgo(c.last_tested_at)
                              : c.created_at
                              ? formatDateTime(c.created_at)
                              : "—"}
                          </td>
                          <td className="py-3 px-4 text-right">{rowActions(c)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          );
        }

        if (kind === "jira") {
          return (
            <div key="jira" className="flex flex-col">
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary text-[20px]">task_alt</span>
                  <h2 className="text-base font-semibold text-on-surface">
                    Atlassian / Jira Entegrasyonları
                  </h2>
                </div>
                <span className="font-mono text-xs text-outline">Webhook Event Bus: Çevrimiçi</span>
              </div>
              <div className="overflow-x-auto rounded bg-surface-container-low border border-outline-variant/20 shadow-sm">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-surface-container text-outline uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Entegrasyon</th>
                      <th className="py-2.5 px-4">Hedef Site &amp; Proje</th>
                      <th className="py-2.5 px-4">Yetkili Hesap</th>
                      <th className="py-2.5 px-4">Token Durumu</th>
                      <th className="py-2.5 px-4">Test / Senkronizasyon</th>
                      <th className="py-2.5 px-4 text-right">İşlemler</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10 text-on-surface">
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-4 px-4 text-center text-outline">
                          Eşleşen Jira bağlantısı bulunamadı.
                        </td>
                      </tr>
                    ) : (
                      rows.map((c) => (
                        <tr
                          key={c.id}
                          className={`hover:bg-surface-container-high/40 transition-colors ${
                            c.is_disabled ? "opacity-50" : ""
                          }`}
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  c.is_disabled ? "bg-outline" : "bg-tertiary"
                                }`}
                              />
                              <span className="font-medium text-on-surface">{c.name}</span>
                              {c.is_default && (
                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-container text-tertiary font-mono">
                                  varsayılan
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono">
                            <span className="text-on-surface">{c.base_url || "—"}</span>
                            {c.project_key && (
                              <span className="ml-2 px-1.5 py-0.5 rounded bg-surface-container text-primary-fixed-dim">
                                PROJE: {c.project_key}
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 font-mono text-on-surface-variant">
                            {maskEmail(c.email || "")}
                          </td>
                          <td className="py-3 px-4">
                            {c.token ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container font-mono text-tertiary">
                                <span className="w-1.5 h-1.5 rounded-full bg-tertiary" /> API Token: Kayıtlı
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded bg-surface-container-high font-mono text-outline">
                                Kayıtlı Değil
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <TestBadge c={c} />
                          </td>
                          <td className="py-3 px-4 text-right">{rowActions(c)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          );
        }

        if (kind === "llm") {
          return (
            <div key="llm" className="flex flex-col">
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary-container text-[20px]">smart_toy</span>
                  <h2 className="text-base font-semibold text-on-surface">
                    LLM &amp; Yapay Zeka Çıkarım Sağlayıcıları
                  </h2>
                </div>
                <div className="flex items-center gap-2 font-mono text-xs text-outline">
                  <span>Inference Engine: Ollama / OpenAI Router</span>
                </div>
              </div>
              <div className="overflow-x-auto rounded bg-surface-container-low border border-outline-variant/20 shadow-sm">
                <table className="w-full text-left text-xs whitespace-nowrap">
                  <thead className="bg-surface-container text-outline uppercase tracking-wider font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Sağlayıcı &amp; Model</th>
                      <th className="py-2.5 px-4">Uç Nokta / Adres</th>
                      <th className="py-2.5 px-4">Sıcaklık &amp; Token Limiti</th>
                      <th className="py-2.5 px-4">Ping &amp; Güvenlik</th>
                      <th className="py-2.5 px-4">API Token</th>
                      <th className="py-2.5 px-4 text-right">İşlemler</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10 text-on-surface">
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-4 px-4 text-center text-outline">
                          Eşleşen LLM sağlayıcısı bulunamadı.
                        </td>
                      </tr>
                    ) : (
                      rows.map((c) => (
                        <tr
                          key={c.id}
                          className={`hover:bg-surface-container-high/40 transition-colors ${
                            c.is_disabled ? "opacity-50" : ""
                          }`}
                        >
                          <td className="py-3 px-4">
                            <div className="flex flex-col">
                              <span className="font-medium text-on-surface flex items-center gap-2">
                                <span
                                  className={`w-2 h-2 rounded-full ${
                                    c.is_disabled ? "bg-outline" : "bg-tertiary"
                                  }`}
                                />
                                {c.name}
                                {c.is_default && (
                                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-container text-tertiary font-mono">
                                    varsayılan
                                  </span>
                                )}
                              </span>
                              <span className="font-mono text-outline pl-4">
                                {c.model || "—"}{" "}
                                <span className="text-secondary text-[11px]">({c.provider || "ollama"})</span>
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-4 font-mono text-on-surface-variant">
                            {c.base_url || "—"}
                          </td>
                          <td className="py-3 px-4 font-mono">
                            <span className="text-secondary">Temp: {c.temperature}</span>
                            <span className="text-outline mx-1">•</span>
                            <span className="text-outline">Max: {c.max_tokens}</span>
                          </td>
                          <td className="py-3 px-4">
                            <TestBadge c={c} />
                          </td>
                          <td className="py-3 px-4 font-mono">
                            {c.token ? (
                              <span className="inline-flex items-center gap-1 font-mono text-tertiary">
                                <span className="w-1.5 h-1.5 rounded-full bg-tertiary" /> API Key: Kayıtlı
                              </span>
                            ) : c.provider === "ollama" ? (
                              <span className="text-outline">Gerekmiyor (Dahili Ağ)</span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded bg-surface-container-high font-mono text-outline">
                                Kayıtlı Değil
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">{rowActions(c)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          );
        }

        return null;
      })}

      {/* Admin Konsol Erişim & Rol Yönetimi (Full Width) */}
      {isAdmin() && (
        <div className="flex flex-col rounded bg-surface-container-low border border-outline-variant/20 p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-outline-variant/10">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-surface-container flex items-center justify-center text-primary">
                <span className="material-symbols-outlined text-[20px]">admin_panel_settings</span>
              </div>
              <div>
                <h3 className="text-base font-semibold text-on-surface">
                  Admin Konsol Erişim &amp; Rol Yönetimi
                </h3>
                <p className="text-xs text-on-surface-variant">
                  FastAPI API Gateway ve Bağlantı yapılandırma yetkileri
                </p>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-tertiary-container/20 text-tertiary text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary" />
              Admin Yetkisi Doğrulandı
            </span>
          </div>

          {/* Users Table */}
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-left text-xs whitespace-nowrap">
              <thead className="bg-surface-container text-outline uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Kullanıcı</th>
                  <th className="py-2.5 px-3">E-posta</th>
                  <th className="py-2.5 px-3">Rol / Yetki Kapsamı</th>
                  <th className="py-2.5 px-3">Son Giriş</th>
                  <th className="py-2.5 px-3">Oluşturuldu</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/10 text-on-surface">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-surface-container-high/30 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-6 h-6 rounded-full flex items-center justify-center font-mono text-[10px] text-white"
                          style={{
                            background:
                              u.role === "admin"
                                ? "#494bd6"
                                : u.role === "approver"
                                ? "#2f3aa3"
                                : "#262a35",
                          }}
                        >
                          {initials(u.username)}
                        </div>
                        <span className="font-mono font-medium text-on-surface">{u.username}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-outline">{u.email || "—"}</td>
                    <td className="py-2.5 px-3">
                      <select
                        className="bg-surface-container text-on-surface border border-outline-variant/30 rounded px-2.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                        value={u.role}
                        onChange={async (e) => {
                          try {
                            await api.put(`/api/auth/users/${u.id}`, { role: e.target.value });
                            toast("Rol başarıyla güncellendi.");
                            load();
                          } catch (err) {
                            toast(`Rol güncellenemedi: ${(err as Error).message}`, false);
                          }
                        }}
                      >
                        <option value="admin">Admin (Tam Yetki)</option>
                        <option value="approver">Approver (Onay Yetkilisi)</option>
                        <option value="viewer">Viewer (Salt Okunur)</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-outline">
                      {u.last_login_at ? timeAgo(u.last_login_at) : "—"}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-outline">{formatDateTime(u.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Quick Inline User Add Form */}
          <div className="mt-auto bg-surface-container p-3 rounded flex flex-col sm:flex-row items-center gap-2">
            <input
              className="bg-surface-container-lowest text-on-surface placeholder:text-outline font-mono text-xs px-3 py-1.5 rounded w-full sm:w-1/3 focus:outline-none border border-outline-variant/20"
              placeholder="Kullanıcı Adı"
              type="text"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
            />
            <input
              className="bg-surface-container-lowest text-on-surface placeholder:text-outline text-xs px-3 py-1.5 rounded w-full sm:w-1/3 focus:outline-none border border-outline-variant/20"
              placeholder="E-posta (opsiyonel)"
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
            />
            <select
              className="bg-surface-container-lowest text-on-surface text-xs px-2.5 py-1.5 rounded w-full sm:w-1/4 focus:outline-none border border-outline-variant/20"
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            >
              <option value="viewer">Viewer</option>
              <option value="approver">Approver</option>
              <option value="admin">Admin</option>
            </select>
            <button
              className="w-full sm:w-auto px-4 py-1.5 bg-primary hover:bg-primary/90 text-on-primary font-semibold text-xs rounded flex items-center justify-center gap-1 transition-colors whitespace-nowrap"
              onClick={async () => {
                if (!newUser.username.trim()) {
                  toast("Kullanıcı adı gereklidir.", false);
                  return;
                }
                try {
                  const pwd = Array.from(crypto.getRandomValues(new Uint8Array(12)))
                    .map((b) => "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"[b % 56])
                    .join("");
                  await api.post("/api/auth/register", {
                    username: newUser.username.trim(),
                    password: pwd,
                    email: newUser.email.trim(),
                  });
                  setFreshPassword({ username: newUser.username.trim(), password: pwd });
                  setNewUser({ username: "", email: "", role: "viewer" });
                  toast("Yeni kullanıcı başarıyla oluşturuldu.");
                  load();
                } catch (err) {
                  toast(`Açılamadı: ${(err as Error).message}`, false);
                }
              }}
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
              <span>Ekle</span>
            </button>
          </div>

          {freshPassword && (
            <div className="mt-3 p-3 rounded bg-surface-container-lowest border border-tertiary/40 text-xs font-mono flex items-center justify-between">
              <div>
                <span className="text-tertiary font-semibold">Parola Üretildi:</span>{" "}
                <span className="text-on-surface">{freshPassword.username}</span> için geçici parola:{" "}
                <b className="text-primary px-1.5 py-0.5 rounded bg-surface-container">
                  {freshPassword.password}
                </b>{" "}
                <span className="text-outline text-[11px]">(Tekrar gösterilmeyecek, kopyalayın)</span>
              </div>
              <button
                className="text-primary hover:underline text-xs"
                onClick={() => setFreshPassword(null)}
              >
                Kapat
              </button>
            </div>
          )}
        </div>
      )}

      {/* Webhook endpoint card */}
      <div className="p-3 rounded bg-surface-container-low border border-outline-variant/20 flex items-center justify-between text-xs font-mono text-outline">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-outline text-[16px]">terminal</span>
          <span>Webhook Endpoint:</span>
          <span className="text-on-surface">{window.location.origin}/api/webhooks/github</span>
        </div>
        <button
          className="text-primary hover:underline text-xs"
          onClick={() => {
            navigator.clipboard.writeText(`${window.location.origin}/api/webhooks/github`);
            toast("Webhook adresi panoya kopyalandı.");
          }}
        >
          Kopyala
        </button>
      </div>

      {/* ========================================================= */}
      {/* Centered POP-UP MODAL (Wider 2-Column Responsive Layout)   */}
      {/* Fits Base URL, Temperature, Max Tokens cleanly NO scrollbar */}
      {/* ========================================================= */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          {/* Backdrop clickable */}
          <div
            className="fixed inset-0"
            onClick={() => setEditing(null)}
            aria-hidden="true"
          />

          {/* Modal Container: max-w-2xl width gives ample room for 2-column layout */}
          <div
            className="relative z-10 w-full max-w-2xl bg-surface-container-low border border-outline-variant/30 rounded-xl shadow-2xl p-6 flex flex-col gap-4 overflow-visible"
            onKeyDown={(e) => {
              const t = e.target as HTMLElement;
              if (e.key === "Enter" && !/^(SELECT|TEXTAREA|BUTTON)$/.test(t.tagName)) {
                e.preventDefault();
                save();
              }
            }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-1 border-b border-outline-variant/10">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary-container text-[22px]">
                  tune
                </span>
                <h3 className="text-base font-semibold text-on-surface">
                  {editing.id ? "Bağlantıyı Düzenle" : "Hızlı Yapılandırma &amp; Bağlantı Önizleme"}
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="text-xs text-outline hover:text-primary transition-colors flex items-center gap-1 font-mono"
                  onClick={resetToDefaults}
                  title="Bu sekme için önerilen varsayılan değerleri yükler"
                >
                  <span className="material-symbols-outlined text-[14px]">restart_alt</span>
                  <span>Varsayılanları Yükle</span>
                </button>
                <span className="text-outline font-mono text-xs">Esc</span>
                <button
                  type="button"
                  className="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
                  onClick={() => setEditing(null)}
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>
            </div>

            {/* Category Select Tabs: Tab değiştiğinde türe özel varsayılanlar yüklenir */}
            <div className="flex items-center gap-1 p-1 bg-surface-container rounded mb-1">
              {(
                [
                  ["github", "GitHub"],
                  ["jira", "Jira"],
                  ["llm", "LLM Sağlayıcı"],
                ] as [Kind, string][]
              ).map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  className={`flex-1 py-1.5 rounded text-xs transition-colors text-center font-medium ${
                    form.kind === k
                      ? "bg-primary-container text-on-primary-container font-semibold shadow-sm"
                      : "text-outline hover:text-on-surface"
                  }`}
                  onClick={() => switchTab(k)}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Form Inputs with 2-Column Balanced Grid */}
            <div className="flex flex-col gap-3.5">
              {/* ===================== LLM TAB ===================== */}
              {form.kind === "llm" && (
                <>
                  {/* Row 1: Sağlayıcı (Provider) & Model Seçimi side-by-side */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1.5">
                        Sağlayıcı (Provider)
                      </label>
                      <div className="grid grid-cols-4 gap-1">
                        {(["openai", "anthropic", "ollama", "gemini"] as const).map((p) => (
                          <button
                            key={p}
                            type="button"
                            className={`py-1.5 px-2 rounded font-mono text-xs text-center transition-all ${
                              form.provider === p
                                ? "bg-surface-container-highest text-on-surface font-semibold shadow-sm ring-1 ring-primary/30"
                                : "bg-surface-container text-outline hover:text-on-surface"
                            }`}
                            onClick={() => switchProvider(p)}
                          >
                            {p === "openai"
                              ? "OpenAI"
                              : p === "anthropic"
                              ? "Anthropic"
                              : p === "ollama"
                              ? "Ollama"
                              : "Gemini"}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <label className="text-xs text-on-surface-variant font-medium">
                          Model Seçimi
                        </label>
                        <button
                          type="button"
                          className="text-xs font-mono text-primary hover:underline flex items-center gap-0.5"
                          onClick={loadModels}
                          disabled={modelsLoading}
                        >
                          <span
                            className={`material-symbols-outlined text-[14px] ${
                              modelsLoading ? "animate-spin" : ""
                            }`}
                          >
                            refresh
                          </span>
                          <span>Modelleri Yenile</span>
                        </button>
                      </div>
                      {models.length > 0 ? (
                        <select
                          className="w-full bg-surface-container text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border-none"
                          value={form.model}
                          onChange={(e) => set("model", e.target.value)}
                        >
                          {!models.some((m) => m.name === form.model) && (
                            <option value={form.model}>{form.model || "— Model Seçin —"}</option>
                          )}
                          {models.map((m) => (
                            <option key={m.name} value={m.name}>
                              {m.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <select
                          className="w-full bg-surface-container text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border-none"
                          value={form.model}
                          onChange={(e) => set("model", e.target.value)}
                        >
                          {form.provider === "openai" && (
                            <>
                              <option value="gpt-4o">gpt-4o (varsayılan - en yüksek akıl yürütme)</option>
                              <option value="gpt-4o-mini">gpt-4o-mini (hızlı düşük maliyetli çıkarım)</option>
                              <option value="o1-preview">o1-preview (ileri düzey sistem optimizasyonu)</option>
                            </>
                          )}
                          {form.provider === "anthropic" && (
                            <>
                              <option value="claude-3-7-sonnet">claude-3-7-sonnet (önerilen)</option>
                              <option value="claude-3-5-sonnet">claude-3-5-sonnet</option>
                              <option value="claude-3-5-haiku">claude-3-5-haiku (hızlı)</option>
                            </>
                          )}
                          {form.provider === "ollama" && (
                            <>
                              <option value="llama3.3:70b">llama3.3:70b (lokal k8s cluster)</option>
                              <option value="qwen2.5-coder:14b">qwen2.5-coder:14b</option>
                              <option value="deepseek-r1:14b">deepseek-r1:14b</option>
                              <option value="mistral:latest">mistral:latest</option>
                            </>
                          )}
                          {form.provider === "gemini" && (
                            <>
                              <option value="gemini-2.0-flash">gemini-2.0-flash (en hızlı &amp; güncel)</option>
                              <option value="gemini-1.5-pro">gemini-1.5-pro (büyük bağlam)</option>
                              <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                            </>
                          )}
                        </select>
                      )}
                    </div>
                  </div>

                  {/* Row 2: Uç Nokta (Base URL) & Sıcaklık / Max Token side-by-side */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Uç Nokta / Base URL
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. http://localhost:11434 veya https://api.openai.com/v1"
                        value={form.base_url}
                        onChange={(e) => set("base_url", e.target.value)}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-xs text-on-surface-variant font-medium mb-1">
                          Sıcaklık (Temp)
                        </label>
                        <input
                          className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                          type="number"
                          step="0.05"
                          min="0"
                          max="1"
                          value={form.temperature}
                          onChange={(e) => set("temperature", parseFloat(e.target.value) || 0)}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-on-surface-variant font-medium mb-1">
                          Max Token
                        </label>
                        <input
                          className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                          type="number"
                          value={form.max_tokens}
                          onChange={(e) => set("max_tokens", parseInt(e.target.value, 10) || 2048)}
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* ===================== GITHUB TAB ===================== */}
              {form.kind === "github" && (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Bağlantı Adı
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. GitHub Enterprise Core"
                        value={form.name}
                        onChange={(e) => set("name", e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Organizasyon / Depo Sahibi (Owner)
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. devops-agentic-org"
                        value={form.owner}
                        onChange={(e) => set("owner", e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        GitHub API URL
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="https://api.github.com"
                        value={form.base_url}
                        onChange={(e) => set("base_url", e.target.value)}
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs text-on-surface-variant font-medium">
                          Webhook Gizli Anahtarı (Secret)
                        </label>
                        {hasSecrets.secret || secretModified ? (
                          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-tertiary">
                            <span className="w-1.5 h-1.5 rounded-full bg-tertiary" /> Kayıtlı
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-outline">
                            <span className="w-1.5 h-1.5 rounded-full bg-outline" /> Boş
                          </span>
                        )}
                      </div>
                      <div className="relative flex items-center">
                        <input
                          className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded pr-20 focus:outline-none border border-outline-variant/20 focus:border-primary"
                          type={showWebhookSecret ? "text" : "password"}
                          value={
                            secretModified || !hasSecrets.secret
                              ? form.webhook_secret
                              : "••••••••••••"
                          }
                          placeholder={hasSecrets.secret ? "" : "whsec_..."}
                          onFocus={() => {
                            if (!secretModified && hasSecrets.secret) {
                              setSecretModified(true);
                              set("webhook_secret", "");
                            }
                          }}
                          onChange={(e) => {
                            setSecretModified(true);
                            set("webhook_secret", e.target.value);
                          }}
                        />
                        <button
                          type="button"
                          className="absolute right-2 px-2 py-0.5 rounded bg-surface-container hover:bg-surface-container-high text-outline font-mono text-xs"
                          onClick={async (e) => {
                            e.preventDefault();
                            if (!showWebhookSecret && !secretModified && hasSecrets.secret && editing?.id) {
                              try {
                                const r = await api.get<{ value: string }>(
                                  `/api/connections/${editing.id}/secret?field=webhook_secret`
                                );
                                set("webhook_secret", r.value || "");
                                setSecretModified(true);
                              } catch (err) {
                                toast(`Açılamadı: ${(err as Error).message}`, false);
                                return;
                              }
                            }
                            setShowWebhookSecret(!showWebhookSecret);
                          }}
                        >
                          {showWebhookSecret ? "Gizle" : "Göster"}
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* ===================== JIRA TAB ===================== */}
              {form.kind === "jira" && (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Entegrasyon Adı
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. Jira Cloud Prod"
                        value={form.name}
                        onChange={(e) => set("name", e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Jira Domain / Site Adresi
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. agentic-devops.atlassian.net"
                        value={form.base_url}
                        onChange={(e) => set("base_url", e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Hizmet Hesabı E-postası
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. automation-bot@company.io"
                        type="email"
                        value={form.email}
                        onChange={(e) => set("email", e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-on-surface-variant font-medium mb-1">
                        Varsayılan Proje Anahtarı (Project Key)
                      </label>
                      <input
                        className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded focus:outline-none border border-outline-variant/20 focus:border-primary"
                        placeholder="örn. CLOUD, SCRUM"
                        value={form.project_key}
                        onChange={(e) => set("project_key", e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}

              {/* ===================== STANDARD API TOKEN / SECRET KEY INPUT ===================== */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-on-surface-variant font-medium">
                    {form.kind === "llm"
                      ? "API Token / Secret Key"
                      : form.kind === "github"
                      ? "GitHub Personal Access Token (PAT)"
                      : "Jira API Token"}
                  </label>
                  {isKeySaved || (tokenModified && !!form.token) ? (
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] text-tertiary">
                      <span className="w-1.5 h-1.5 rounded-full bg-tertiary" /> Kayıtlı
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] text-outline">
                      <span className="w-1.5 h-1.5 rounded-full bg-outline" /> Boş (Kayıtsız)
                    </span>
                  )}
                </div>

                <div className="relative flex items-center">
                  <input
                    className="w-full bg-surface-container-lowest text-on-surface font-mono text-xs px-3 py-2 rounded pr-20 focus:outline-none border border-outline-variant/20 focus:border-primary"
                    type={showPassword ? "text" : "password"}
                    value={currentKeyDisplay}
                    placeholder={
                      isKeySaved
                        ? ""
                        : form.kind === "github"
                        ? "ghp_..."
                        : form.kind === "jira"
                        ? "jira_pat_..."
                        : form.provider === "ollama"
                        ? "Gerekmiyor (Dahili Ağ)"
                        : "sk-proj-..."
                    }
                    onFocus={() => {
                      if (!tokenModified && isKeySaved) {
                        setTokenModified(true);
                        set("token", "");
                      }
                    }}
                    onChange={(e) => {
                      setTokenModified(true);
                      set("token", e.target.value);
                    }}
                  />
                  <button
                    type="button"
                    className="absolute right-2 px-2.5 py-0.5 rounded bg-surface-container hover:bg-surface-container-high text-outline font-mono text-xs transition-colors"
                    onClick={async (e) => {
                      e.preventDefault();
                      if (!showPassword && !tokenModified && isKeySaved && editing?.id) {
                        try {
                          const r = await api.get<{ value: string }>(
                            `/api/connections/${editing.id}/secret?field=token`
                          );
                          set("token", r.value || "");
                          setTokenModified(true);
                        } catch (err) {
                          toast(`Açılamadı: ${(err as Error).message}`, false);
                          return;
                        }
                      }
                      setShowPassword(!showPassword);
                    }}
                  >
                    {showPassword ? "Gizle" : "Göster"}
                  </button>
                </div>
                <span className="block mt-1 text-[11px] text-outline">
                  Boş bırakırsanız mevcut şifreli anahtar korunur, değişmez.
                </span>
              </div>

              {/* Set as Default Checkbox for this Kind */}
              <label className="flex items-center gap-2 text-xs text-on-surface-variant cursor-pointer select-none">
                <input
                  type="checkbox"
                  className="rounded bg-surface-container border-outline-variant text-primary focus:ring-0"
                  checked={form.is_default}
                  onChange={(e) => set("is_default", e.target.checked)}
                />
                <span>
                  Bu {form.kind === "github" ? "GitHub" : form.kind === "jira" ? "Jira" : "LLM"} bağlantısını bu tür için varsayılan yap
                </span>
              </label>

              {/* Warning Callout for Webhooks/Breaking */}
              <div className="bg-error-container/20 border border-error/30 rounded flex items-start gap-2 p-2.5">
                <span className="material-symbols-outlined text-error text-[18px] shrink-0 mt-0.5">
                  warning
                </span>
                <div className="text-on-surface text-[11px] leading-tight">
                  <span className="font-semibold text-error">DİKKAT:</span> Bu sağlayıcı veya token
                  değiştirildiğinde aktif FastAPI proxy uç noktalarının bağlantısı yeniden başlatılır.
                </div>
              </div>
            </div>

            {/* Modal Action Footer */}
            <div className="flex items-center justify-between pt-2 mt-1 border-t border-outline-variant/10">
              <div className="flex items-center gap-2 font-mono text-xs text-outline">
                <span className="px-1.5 py-0.5 rounded bg-surface-container">[Enter] Kaydet</span>
                <span className="px-1.5 py-0.5 rounded bg-surface-container">[Esc] Kapat</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="px-3.5 py-1.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface-variant font-medium text-xs transition-colors"
                  onClick={() => setEditing(null)}
                >
                  İptal
                </button>
                <button
                  type="button"
                  className="px-4 py-2 rounded bg-primary-container hover:bg-primary-container/90 text-on-primary-container font-semibold text-xs transition-all shadow-sm"
                  onClick={save}
                >
                  Değişiklikleri Kaydet
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
