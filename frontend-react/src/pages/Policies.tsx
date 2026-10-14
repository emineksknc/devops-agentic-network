import { useCallback, useEffect, useState } from "react";
import { api, type Connection, type Policy } from "../api";
import { Empty, Field, Modal } from "../components/ui";
import { toast } from "../components/Toaster";

const STATUSES = ["To Do", "In Progress", "In Review", "Done", "Blocked"];

const BLANK: Policy = {
  repo: "",
  jira_project: "",
  on_pass_transition: "In Review",
  on_fail_transition: "Blocked",
  auto_write_pass: true,
  auto_write_fail: false,
  require_approval: true,
  dry_run_default: true,
  github_conn_id: "",
  jira_conn_id: "",
};

export function Policies() {
  const [pols, setPols] = useState<Policy[]>([]);
  const [conns, setConns] = useState<Connection[]>([]);
  const [editing, setEditing] = useState<Policy | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([api.get<Policy[]>("/api/policies"), api.get<Connection[]>("/api/connections")]);
      setPols(p);
      setConns(c);
    } catch (e) {
      toast(`Yüklenemedi: ${(e as Error).message}`, false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const connName = (id: string) => conns.find((c) => c.id === id)?.name || "—";

  function openNew() {
    setEditing({ ...BLANK });
  }
  function openEdit(p: Policy) {
    setEditing({ ...p });
  }

  async function save(p: Policy) {
    try {
      await api.post("/api/policies", p);
      setEditing(null);
      toast(`${p.repo} kaydedildi.`);
      load();
    } catch (e) {
      toast(`Kaydedilemedi: ${(e as Error).message}`, false);
    }
  }

  async function remove(repo: string) {
    if (!confirm("Silinsin mi?")) return;
    try {
      await api.del(`/api/policies/${encodeURIComponent(repo)}`);
      load();
    } catch (e) {
      toast(`Silinemedi: ${(e as Error).message}`, false);
    }
  }

  async function test(p: Policy) {
    try {
      const r = await api.post<{ run_id: string }>("/api/runs", { repo: p.repo, dry_run: true, count: 3 });
      toast(`Test runu başlatıldı: #run-${r.run_id}`);
    } catch (e) {
      toast(`Test başlatılamadı: ${(e as Error).message}`, false);
    }
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Politikalar</h1>
        <button className="btn-primary" onClick={openNew}>
          + Yeni Politika
        </button>
      </div>
      {pols.length === 0 ? (
        <Empty text="Henüz politika yok. İlkini oluştur." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {pols.map((p) => (
            <div key={p.repo} className="card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <b className="text-sm">{p.repo}</b>
                <div className="flex gap-3">
                  <button className="text-xs text-accent-soft" onClick={() => test(p)}>
                    Test Et
                  </button>
                  <button className="text-xs text-accent-soft" onClick={() => openEdit(p)}>
                    Düzenle
                  </button>
                  <button className="text-xs text-bad" onClick={() => remove(p.repo)}>
                    Sil
                  </button>
                </div>
              </div>
              <div className="text-xs text-muted space-y-1">
                <div>Proje: {p.jira_project || "—"}</div>
                <div>
                  Geçerse → {p.on_pass_transition} {p.auto_write_pass ? "(otomatik)" : "(onaylı)"}
                </div>
                <div>
                  Kalırsa → {p.on_fail_transition} {p.auto_write_fail ? "(otomatik)" : "(onaylı)"}
                </div>
                <div>
                  GitHub: {connName(p.github_conn_id)} · Jira: {connName(p.jira_conn_id)}
                </div>
                {p.dry_run_default && <div>Dry-run varsayılan</div>}
              </div>
            </div>
          ))}
        </div>
      )}
      {editing && (
        <PolicyModal value={editing} conns={conns} onClose={() => setEditing(null)} onSave={save} onChange={setEditing} />
      )}
    </>
  );
}

function PolicyModal({
  value: p,
  conns,
  onClose,
  onSave,
  onChange,
}: {
  value: Policy;
  conns: Connection[];
  onClose: () => void;
  onSave: (p: Policy) => void;
  onChange: (p: Policy) => void;
}) {
  const [ghRepos, setGhRepos] = useState<string[]>([]);
  const [ghHint, setGhHint] = useState("");
  const [projects, setProjects] = useState<{ key: string; name: string }[]>([]);
  const [pjHint, setPjHint] = useState("");
  const [customRepo, setCustomRepo] = useState(false);

  // Baglanti secimi degisince listeleri O baglantidan doldur
  useEffect(() => {
    let alive = true;
    setGhRepos([]);
    setGhHint("");
    api
      .get<{ full_name: string }[]>(`/api/github/repos?conn_id=${encodeURIComponent(p.github_conn_id)}`)
      .then((r) => {
        if (alive) setGhRepos(r.map((x) => x.full_name));
      })
      .catch((e) => {
        if (alive) setGhHint((e as Error).message);
      });
    return () => {
      alive = false;
    };
  }, [p.github_conn_id]);

  useEffect(() => {
    let alive = true;
    setProjects([]);
    setPjHint("");
    api
      .get<{ key: string; name: string }[]>(`/api/jira/projects?conn_id=${encodeURIComponent(p.jira_conn_id)}`)
      .then((r) => {
        if (alive) setProjects(r);
      })
      .catch((e) => {
        if (alive) setPjHint((e as Error).message);
      });
    return () => {
      alive = false;
    };
  }, [p.jira_conn_id]);
  const set = (k: keyof Policy, v: string | boolean) => onChange({ ...p, [k]: v });
  const tgl = (k: "auto_write_pass" | "auto_write_fail" | "require_approval" | "dry_run_default", label: string) => (
    <label className="flex items-center gap-2 text-xs text-muted">
      <input type="checkbox" checked={p[k]} onChange={(e) => set(k, e.target.checked)} /> {label}
    </label>
  );
  const connOpts = (kind: string) =>
    conns
      .filter((c) => c.kind === kind)
      .map((c) => (
        <option key={c.id} value={c.id}>
          {c.name}
        </option>
      ));
  return (
    <Modal title="Politika" onClose={onClose}>
      <div className="grid grid-cols-2 gap-2">
        <Field label="GitHub bağlantısı">
          <select className="input" value={p.github_conn_id} onChange={(e) => set("github_conn_id", e.target.value)}>
            <option value="">Varsayılan</option>
            {connOpts("github")}
          </select>
        </Field>
        <Field label="Jira bağlantısı">
          <select className="input" value={p.jira_conn_id} onChange={(e) => set("jira_conn_id", e.target.value)}>
            <option value="">Varsayılan</option>
            {connOpts("jira")}
          </select>
        </Field>
      </div>
      <Field label="Repo (seçili GitHub bağlantısındaki gerçek depolar)">
        <select
          className="input font-mono"
          value={customRepo ? "__custom" : p.repo}
          onChange={(e) => {
            if (e.target.value === "__custom") {
              setCustomRepo(true);
              set("repo", "");
            } else {
              setCustomRepo(false);
              set("repo", e.target.value);
            }
          }}
        >
          <option value="">Seç…</option>
          {ghRepos.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
          <option value="__custom">Listede yok, elle yaz…</option>
        </select>
        {ghHint && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>{ghHint}</div>}
      </Field>
      {customRepo && (
        <Field label="Özel repo (org/repo)">
          <input className="input font-mono" value={p.repo} onChange={(e) => set("repo", e.target.value)} />
        </Field>
      )}
      <Field label="Jira projesi (seçili Jira bağlantısındaki gerçek projeler)">
        {projects.length > 0 ? (
          <select className="input font-mono" value={p.jira_project} onChange={(e) => set("jira_project", e.target.value)}>
            <option value="">Seç…</option>
            {projects.map((x) => (
              <option key={x.key} value={x.key}>
                {x.key} — {x.name}
              </option>
            ))}
          </select>
        ) : (
          <input
            className="input font-mono"
            value={p.jira_project}
            placeholder="SCRUM"
            onChange={(e) => set("jira_project", e.target.value)}
          />
        )}
        {pjHint && <div className="text-xs mt-1" style={{ color: "#f59e0b" }}>{pjHint}</div>}
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Geçerse geçiş">
          <select className="input" value={p.on_pass_transition} onChange={(e) => set("on_pass_transition", e.target.value)}>
            {STATUSES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Field>
        <Field label="Kalırsa geçiş">
          <select className="input" value={p.on_fail_transition} onChange={(e) => set("on_fail_transition", e.target.value)}>
            {STATUSES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Field>
      </div>
      <div className="space-y-2 mb-4">
        {tgl("auto_write_pass", "Geçerse otomatik yaz")}
        {tgl("auto_write_fail", "Kalırsa otomatik yaz")}
        {tgl("require_approval", "Onay zorunlu")}
        {tgl("dry_run_default", "Dry-run varsayılan")}
      </div>
      <div className="flex justify-end">
        <button className="btn-primary" onClick={() => onSave(p)}>
          Kaydet
        </button>
      </div>
    </Modal>
  );
}
