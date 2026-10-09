import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, timeAgo, type RunDetail } from "../api";
import { Chip, StatusBadge } from "../components/badges";
import { toast } from "../components/Toaster";

export function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setRun(await api.get<RunDetail>(`/api/runs/${id}`));
    } catch {
      setError("Run bulunamadı.");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(approved: boolean) {
    try {
      const r = await api.post<RunDetail>(`/api/runs/${id}/approve`, { approved, note: "" });
      setRun(r);
      toast(approved ? "Onaylandı, Jira yazıldı." : "Reddedildi.");
    } catch (e) {
      toast(`İşlem başarısız: ${(e as Error).message}`, false);
    }
  }

  if (error) return <p className="text-sm text-bad">{error}</p>;
  if (!run) return <p className="text-sm text-muted">Yükleniyor…</p>;

  return (
    <>
      <Link to="/runs" className="hidden lg:inline text-xs text-muted hover:text-ink">
        ‹ Tüm Çalıştırmalar
      </Link>
      <div className="card p-4 flex flex-wrap items-center gap-2">
        <span className="font-mono font-bold text-accent-soft">#run-{run.run_id}</span>
        <span
          className="px-2 py-0.5 rounded text-xs font-semibold"
          style={
            run.dry_run
              ? { background: "rgba(245,158,11,.15)", color: "#f59e0b" }
              : { background: "rgba(16,185,129,.15)", color: "#10b981" }
          }
        >
          {run.dry_run ? "Dry-Run" : "Canlı"}
        </span>
        <StatusBadge status={run.status} />
        <span className="text-xs text-muted">
          {run.repo} · {timeAgo(run.created_at)}
        </span>
      </div>

      {run.status === "pending_approval" && (
        <div className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="text-sm">
            <b>Onay bekliyor:</b> <span className="text-muted">Jira'ya henüz yazılmadı. Planı inceleyip onayla.</span>
          </div>
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => decide(false)}>
              Reddet
            </button>
            <button className="btn-primary" onClick={() => decide(true)}>
              Onayla ve Yaz
            </button>
          </div>
        </div>
      )}

      <div className="card p-4">
        <h3 className="text-sm font-semibold mb-2">Sürüm Bülteni</h3>
        <div className="text-xs whitespace-pre-wrap text-muted">{run.final_report || run.error || "—"}</div>
      </div>

      {run.error && (
        <div className="card p-4" style={{ borderColor: "#ef4444" }}>
          <h3 className="text-sm font-semibold mb-1" style={{ color: "#ef4444" }}>
            Hata
          </h3>
          <div className="text-xs whitespace-pre-wrap text-muted">{run.error}</div>
        </div>
      )}

      {run.events && run.events.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Olay Günlüğü ({run.events.length})</h3>
          <div className="card p-4 space-y-1.5 max-h-72 overflow-auto">
            {run.events.map((e, i) => (
              <div key={i} className="flex gap-2 text-xs">
                <span className="font-mono shrink-0" style={{ color: "#818cf8" }}>
                  {e.node || "sistem"}
                </span>
                <span
                  className="shrink-0 w-2 h-2 rounded-full mt-1"
                  style={{
                    background: e.level === "error" ? "#ef4444" : e.level === "warning" ? "#f59e0b" : "#10b981",
                  }}
                />
                <span className="text-muted">{e.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Commitler ({run.commit_units.length})</h3>
        {run.commit_units.map((u) => (
          <div key={u.sha || u.short_sha} className="card p-4 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono text-accent-soft">{u.short_sha}</span>
              <StatusBadge status={u.review_status === "FAILED" ? "failed" : "success"} />
              {(u.jira_ids || []).map((t) => (
                <Chip key={t}>{t}</Chip>
              ))}
            </div>
            <div className="text-sm font-semibold">{u.message}</div>
            <div className="text-xs text-muted">Yazar: {u.author || "?"}</div>
            {u.review_comment && (
              <div className="text-xs rounded-md p-2" style={{ background: "#0b1326", color: "#c7c4d7" }}>
                {u.review_comment}
              </div>
            )}
          </div>
        ))}
      </div>

      {run.jira_actions.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Jira Aksiyonları</h3>
          {run.jira_actions.map((a, i) => (
            <div key={i} className="card px-3 py-2 flex flex-wrap items-center gap-2 text-xs">
              <Chip>{a.ticket_id}</Chip>
              <StatusBadge status={a.state} />
              {a.transition_to && <span className="text-muted">→ {a.transition_to}</span>}
              {a.skipped_reason && <span style={{ color: "#f59e0b" }}>{a.skipped_reason}</span>}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
