import { useCallback, useEffect, useState } from "react";
import { api, type Connection } from "../api";
import { Field, Modal } from "../components/ui";
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

export function Settings() {
  const [conns, setConns] = useState<Connection[]>([]);
  const [editing, setEditing] = useState<(Omit<Connection, "id"> & { id?: string }) | null>(null);
  const [form, setForm] = useState(BLANK);
  const [models, setModels] = useState<{ name: string; source?: string }[]>([]);
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
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!editing || editing.kind !== "llm") {
      setModels([]);
      return;
    }
    const q = editing.id
      ? `?conn_id=${encodeURIComponent(editing.id)}`
      : `?provider=${encodeURIComponent(editing.provider || "ollama")}`;
    api
      .get<{ name: string; source?: string }[]>(`/api/llm/models${q}`)
      .then(setModels)
      .catch(() => setModels([]));
  }, [editing?.id, editing?.kind, editing?.provider]); // eslint-disable-line react-hooks/exhaustive-deps

  function openNew() {
    setForm({ ...BLANK });
    setEditing({ ...BLANK });
  }
  function openEdit(c: Connection) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { token: _t, webhook_secret: _w, ...rest } = c;
    setForm({ ...rest, token: "", webhook_secret: "" });
    setEditing({ ...rest, token: "", webhook_secret: "" });
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
      const r = await api.post<{ ok: boolean; detail?: string; status?: number }>(
        `/api/connections/${id}/test`,
        {}
      );
      toast(`${r.ok ? "✓" : "✗"} ${r.detail || r.status}`, r.ok);
    } catch (e) {
      toast(`✗ ${(e as Error).message}`, false);
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

  const groups: [Kind, string][] = [
    ["github", "GitHub"],
    ["jira", "Jira"],
    ["llm", "LLM"],
  ];

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Bağlantılar</h1>
          <p className="text-sm text-muted">Tokenlar maskeli saklanır, asla listelenmez.</p>
        </div>
        <button className="btn-primary" onClick={openNew}>
          + Yeni Bağlantı
        </button>
      </div>

      {groups.map(([kind, label]) => (
        <div key={kind}>
          <h2 className="text-sm font-semibold text-muted">{label}</h2>
          <div className="grid gap-3 xl:grid-cols-2">
            {conns.filter((c) => c.kind === kind).map((c) => (
              <div key={c.id} className="card p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <b className="text-sm">{c.name}</b>
                  {c.is_default && <span className="text-xs text-ok">varsayılan</span>}
                </div>
                <div className="text-xs font-mono text-muted">{c.id}</div>
                <div className="text-xs text-muted">
                  {kind === "github" && `${c.base_url} · ${c.owner}`}
                  {kind === "jira" && `${c.base_url} · ${c.project_key}`}
                  {kind === "llm" && `${c.provider || "ollama"} · ${c.model}`}
                </div>
                <div className="flex gap-3 pt-1">
                  <button className="text-xs text-accent-soft" onClick={() => test(c.id)}>
                    Test
                  </button>
                  <button className="text-xs text-accent-soft" onClick={() => openEdit(c)}>
                    Düzenle
                  </button>
                  <button className="text-xs text-bad" onClick={() => remove(c.id)}>
                    Sil
                  </button>
                </div>
              </div>
            ))}
            {conns.filter((c) => c.kind === kind).length === 0 && (
              <div className="card p-4 text-xs text-muted">Kayıt yok.</div>
            )}
          </div>
        </div>
      ))}

      <div className="card p-4 flex items-center justify-between">
        <div>
          <b className="text-sm">Secret redaksiyonu</b>
          <div className="text-xs text-muted">LLM'e giden diff'lerdeki anahtarlar maskelenir.</div>
        </div>
        <input type="checkbox" checked={redact} onChange={(e) => toggleRedact(e.target.checked)} />
      </div>

      <div className="card p-4 text-xs text-muted font-mono">
        Webhook endpoint: {window.location.origin}/api/webhooks/github
      </div>

      {editing && (
        <Modal title={editing.id ? "Bağlantıyı Düzenle" : "Yeni Bağlantı"} onClose={() => setEditing(null)}>
          <Field label="Ad">
            <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </Field>
          <Field label="Tür">
            <select className="input" value={form.kind} onChange={(e) => set("kind", e.target.value)}>
              <option value="github">GitHub</option>
              <option value="jira">Jira</option>
              <option value="llm">LLM</option>
            </select>
          </Field>
          <Field label="Base URL">
            <input className="input font-mono" value={form.base_url} onChange={(e) => set("base_url", e.target.value)} />
          </Field>
          {form.kind === "github" && (
            <Field label="Owner">
              <input className="input" value={form.owner} onChange={(e) => set("owner", e.target.value)} />
            </Field>
          )}
          {form.kind === "jira" && (
            <>
              <Field label="E-posta">
                <input className="input" value={form.email} onChange={(e) => set("email", e.target.value)} />
              </Field>
              <Field label="Proje anahtarı">
                <input className="input" value={form.project_key} onChange={(e) => set("project_key", e.target.value)} />
              </Field>
            </>
          )}
          {form.kind === "llm" && (
            <>
              <Field label="Provider">
                <select className="input" value={form.provider} onChange={(e) => set("provider", e.target.value)}>
                  <option value="ollama">ollama</option>
                  <option value="openai">openai</option>
                  <option value="anthropic">anthropic</option>
                </select>
              </Field>
              <Field label={`Model${models.length ? ` (${models.length} kurulu)` : ""}`}>
                <input
                  className="input font-mono"
                  list="dan-models"
                  value={form.model}
                  onChange={(e) => set("model", e.target.value)}
                />
                <datalist id="dan-models">
                  {models.map((m) => (
                    <option key={m.name} value={m.name} />
                  ))}
                </datalist>
              </Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Sıcaklık">
                  <input
                    className="input"
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={form.temperature}
                    onChange={(e) => set("temperature", parseFloat(e.target.value) || 0)}
                  />
                </Field>
                <Field label="Max token">
                  <input
                    className="input"
                    type="number"
                    value={form.max_tokens}
                    onChange={(e) => set("max_tokens", parseInt(e.target.value, 10) || 2048)}
                  />
                </Field>
              </div>
            </>
          )}
          <Field label="Token (boş = değişmez)">
            <input
              className="input font-mono"
              type="password"
              value={form.token}
              placeholder={editing.token === "***masked***" ? "kayıtlı" : ""}
              onChange={(e) => set("token", e.target.value)}
            />
          </Field>
          {form.kind === "github" && (
            <Field label="Webhook secret (boş = değişmez)">
              <input
                className="input font-mono"
                type="password"
                value={form.webhook_secret}
                onChange={(e) => set("webhook_secret", e.target.value)}
              />
            </Field>
          )}
          <label className="flex items-center gap-2 text-xs text-muted mb-4">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => set("is_default", e.target.checked)}
            />
            Varsayılan yap
          </label>
          <div className="flex justify-end">
            <button className="btn-primary" onClick={save}>
              Kaydet
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
