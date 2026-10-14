import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type AuditRow } from "../api";
import { toast } from "../components/Toaster";

export function Audit() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [ticket, setTicket] = useState("");
  const [repo, setRepo] = useState("");

  const load = useCallback(async () => {
    try {
      setRows(
        await api.get<AuditRow[]>(`/api/audit?ticket=${encodeURIComponent(ticket)}&repo=${encodeURIComponent(repo)}`)
      );
    } catch (e) {
      toast(`Yüklenemedi: ${(e as Error).message}`, false);
    }
  }, [ticket, repo]);

  useEffect(() => {
    const h = setTimeout(load, 400);
    return () => clearTimeout(h);
  }, [load]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function download(name: string, text: string, type: string) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  function asCsv() {
    const head = "ticket,repo,run,state,transition,created_at\n";
    const q = (x: unknown) => `"${String(x ?? "").replace(/"/g, '""')}"`;
    return head + rows.map((a) => [a.ticket_id, a.repo, a.run_id, a.state, a.transition_to || "", a.created_at || ""].map(q).join(",")).join("\n");
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Denetim İzi</h1>
        <div className="flex gap-2">
          <button className="btn-ghost !py-1.5" onClick={() => download("denetim-izi.csv", asCsv(), "text/csv")}>
            CSV
          </button>
          <button
            className="btn-ghost !py-1.5"
            onClick={() => download("denetim-izi.json", JSON.stringify(rows, null, 2), "application/json")}
          >
            JSON
          </button>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row gap-2">
        <input className="input" placeholder="Bilet filtrele (örn. SCRUM-6)" value={ticket} onChange={(e) => setTicket(e.target.value)} />
        <input className="input" placeholder="Repo filtrele" value={repo} onChange={(e) => setRepo(e.target.value)} />
      </div>
      <div className="card p-4 overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs text-muted">
              <th className="pr-3 pb-1">Bilet</th>
              <th className="pr-3 pb-1">Repo</th>
              <th className="pr-3 pb-1">Run</th>
              <th className="pr-3 pb-1">Durum</th>
              <th className="pb-1">Zaman</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} style={{ borderTop: "1px solid #334155" }}>
                <td className="py-2 pr-3 font-mono text-xs text-accent-soft">{a.ticket_id}</td>
                <td className="py-2 pr-3 text-xs text-muted">{a.repo}</td>
                <td className="py-2 pr-3 text-xs">
                  <Link to={`/runs/${a.run_id}`} className="text-accent-soft">
                    #run-{a.run_id}
                  </Link>
                </td>
                <td className="py-2 pr-3 text-xs">
                  {a.state}
                  {a.transition_to ? ` → ${a.transition_to}` : ""}
                </td>
                <td className="py-2 text-xs text-muted">{(a.created_at || "").slice(0, 16).replace("T", " ")}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="py-4 text-xs text-muted">Kayıt yok.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-faint">Değiştirilemez salt-okunur kayıt.</p>
    </>
  );
}
