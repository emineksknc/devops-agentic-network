import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, canApprove, timeAgo, type Policy, type Run } from "../api";
import { StatusBadge } from "../components/badges";
import { Empty, Field, Modal } from "../components/ui";
import { toast } from "../components/Toaster";

export function Runs() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [repoFilter, setRepoFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [modelFilter, setModelFilter] = useState("all");
  const [verdictFilter, setVerdictFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [customRepo, setCustomRepo] = useState(false);
  const [form, setForm] = useState({ repo: "", user_goal: "", count: 3, dry_run: true });

  const load = useCallback(async () => {
    try {
      const [r, p] = await Promise.all([api.get<Run[]>("/api/runs"), api.get<Policy[]>("/api/policies")]);
      setRuns(r);
      setPolicies(p);
    } catch (e) {
      toast(`Run listesi alınamadı: ${(e as Error).message}`, false);
    }
  }, []);

  useEffect(() => {
    load();
    const h = setInterval(load, 15000);
    return () => clearInterval(h);
  }, [load]);

  const repos = [...new Set(runs.map((r) => r.repo))];
  const models = [...new Set(runs.map((r) => r.llm_model || "").filter(Boolean))];
  const q = query.trim().toLowerCase();
  const counts = {
    all: runs.length,
    success: runs.filter((r) => r.status === "success").length,
    blocked: runs.filter((r) => ["partially_blocked", "pending_approval"].includes(r.status)).length,
    failed: runs.filter((r) => ["failed", "rejected"].includes(r.status)).length,
    queued: runs.filter((r) => ["queued", "running"].includes(r.status)).length,
  };
  const visible = runs.filter(
    (r) =>
      (repoFilter === "all" || r.repo === repoFilter) &&
      (statusFilter === "all" || r.status === statusFilter) &&
      (modelFilter === "all" || (r.llm_model || "") === modelFilter) &&
      (verdictFilter === "all" ||
        (verdictFilter === "failed" && (r.failed_count || 0) > 0) ||
        (verdictFilter === "mismatch" && (r.mismatch_count || 0) > 0) ||
        (verdictFilter === "clean" && (r.failed_count || 0) === 0 && (r.mismatch_count || 0) === 0)) &&
      (!q || r.run_id.toLowerCase().includes(q) || r.repo.toLowerCase().includes(q))
  );
  const stats: [string, number, string][] = [
    ["Toplam", counts.all, "#f8fafc"],
    ["Başarılı", counts.success, "#10b981"],
    ["Engellenen", counts.blocked, "#f59e0b"],
    ["Canlı/Kuyruk", counts.queued, "#818cf8"],
  ];

  async function create() {
    if (!form.repo.trim()) {
      toast("Önce repo seç.", false);
      return;
    }
    try {
      const r = await api.post<Run>("/api/runs", {
        repo: form.repo,
        user_goal: form.user_goal || undefined,
        count: form.count,
        dry_run: form.dry_run,
      });
      setShowNew(false);
      toast(`Run başlatıldı: #run-${r.run_id}`);
      load();
    } catch (e) {
      toast(`Başlatılamadı: ${(e as Error).message}`, false);
    }
  }

  return (
    <>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold">Çalıştırmalar</h1>
          <p className="text-sm text-muted">Otonom ajan çalıştırmaları ve doğrulama süreçleri</p>
        </div>
        <button className="btn-primary" onClick={() => setShowNew(true)} disabled={!canApprove()} title={canApprove() ? "" : "Run başlatmak için approver yetkisi gerekir"}>
          + Yeni Run Başlat
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {stats.map(([label, n, color]) => (
          <div key={label} className="card p-3">
            <div className="text-xs text-muted mb-1">{label}</div>
            <div className="text-2xl font-bold" style={{ color }}>
              {n}
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <select className="input sm:max-w-xs" value={repoFilter} onChange={(e) => setRepoFilter(e.target.value)}>
          <option value="all">Tüm Depolar</option>
          {repos.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <select className="input sm:max-w-xs" value={modelFilter} onChange={(e) => setModelFilter(e.target.value)}>
          <option value="all">Tüm Modeller</option>
          {models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <input
          className="input font-mono sm:max-w-xs"
          placeholder="run id / repo ara…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {(
            [
              ["all", `Tümü (${counts.all})`],
              ["success", `Başarılı (${counts.success})`],
              ["partially_blocked", `Engellenen (${counts.blocked})`],
              ["failed", `Hata (${counts.failed})`],
              ["queued", `Kuyrukta (${counts.queued})`],
            ] as [string, string][]
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setStatusFilter(v)}
              className={`px-3 py-1.5 rounded-full text-xs ${statusFilter === v ? "font-semibold" : "text-muted"}`}
              style={statusFilter === v ? { background: "#494bd6", color: "#fff" } : { background: "#222a3d" }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {(
            [
              ["all", "Tümü"],
              ["failed", "Riskli"],
              ["mismatch", "Kapsam dışı"],
              ["clean", "Sorunsuz"],
            ] as [string, string][]
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setVerdictFilter(v)}
              className={`px-3 py-1.5 rounded-full text-xs ${verdictFilter === v ? "font-semibold" : "text-muted"}`}
              style={verdictFilter === v ? { background: "#494bd6", color: "#fff" } : { background: "#222a3d" }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {visible.length === 0 ? (
        <Empty text="Kriterlere uygun run yok. İlk çalıştırmayı başlat." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {visible.map((r) => (
            <Link key={r.run_id} to={`/runs/${r.run_id}`} className="card p-4 hover:border-accent transition-colors">
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono font-bold text-sm text-accent-soft">#run-{r.run_id}</span>
                  <span
                    className="px-2 py-0.5 rounded text-xs font-semibold"
                    style={
                      r.dry_run
                        ? { background: "rgba(245,158,11,.15)", color: "#f59e0b" }
                        : { background: "rgba(16,185,129,.15)", color: "#10b981" }
                    }
                  >
                    {r.dry_run ? "Dry-Run" : "Canlı"}
                  </span>
                  <span className="text-xs text-muted">{timeAgo(r.created_at)}</span>
                </div>
                <StatusBadge status={r.status} />
              </div>
              <div className="text-sm font-semibold truncate">{r.repo}</div>
              {(r.llm_model || r.llm_provider) && (
                <div className="text-xs font-mono text-muted truncate">
                  {r.llm_provider ? `${r.llm_provider} · ` : ""}{r.llm_model || "?"}
                </div>
              )}
              <div className="flex items-center justify-between pt-2 text-xs text-muted">
                <span>
                  {r.commit_count} commit ·{" "}
                  <span style={{ color: r.blocked_count ? "#f59e0b" : "#10b981" }}>
                    {r.blocked_count} engellenen
                  </span>
                </span>
                <span className="text-accent-soft">İncele ›</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showNew && (
        <Modal
          title="Yeni Run Başlat"
          onClose={() => {
            setShowNew(false);
            setCustomRepo(false);
          }}
        >
          <Field label="Repo (politikası olanlar listelenir)">
            <select
              className="input font-mono"
              value={customRepo ? "__custom" : form.repo}
              onChange={(e) => {
                if (e.target.value === "__custom") {
                  setCustomRepo(true);
                  setForm({ ...form, repo: "" });
                } else {
                  setCustomRepo(false);
                  const pol = policies.find((p) => p.repo === e.target.value);
                  setForm({
                    ...form,
                    repo: e.target.value,
                    dry_run: pol ? pol.dry_run_default : form.dry_run,
                  });
                }
              }}
            >
              <option value="">Seç…</option>
              {policies.map((p) => (
                <option key={p.repo} value={p.repo}>
                  {p.repo} → {p.jira_project || "?"}
                </option>
              ))}
              <option value="__custom">Özel repo yaz…</option>
            </select>
          </Field>
          {customRepo && (
            <Field label="Özel repo (org/repo)">
              <input
                className="input font-mono"
                value={form.repo}
                placeholder="org/backend-api"
                onChange={(e) => setForm({ ...form, repo: e.target.value })}
              />
            </Field>
          )}
          <Field label="Hedef (boş = varsayılan)">
            <input
              className="input"
              value={form.user_goal}
              onChange={(e) => setForm({ ...form, user_goal: e.target.value })}
            />
          </Field>
          <Field label="Commit sayısı">
            <input
              className="input"
              type="number"
              min={1}
              max={20}
              value={form.count}
              onChange={(e) => setForm({ ...form, count: parseInt(e.target.value, 10) || 3 })}
            />
          </Field>
          <label className="flex items-center gap-2 text-xs text-muted mb-4">
            <input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} />
            Dry-run (Jira'ya yazma, önce planı göster)
          </label>
          <div className="flex justify-end">
            <button className="btn-primary" onClick={create}>
              Başlat
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
