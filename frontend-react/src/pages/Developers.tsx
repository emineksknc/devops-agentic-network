import { useCallback, useEffect, useState } from "react";
import { api, type Developer } from "../api";
import { Chip } from "../components/badges";
import { Empty } from "../components/ui";
import { toast } from "../components/Toaster";

export function Developers() {
  const [devs, setDevs] = useState<Developer[]>([]);

  const load = useCallback(async () => {
    try {
      setDevs(await api.get<Developer[]>("/api/developers"));
    } catch (e) {
      toast(`Yüklenemedi: ${(e as Error).message}`, false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <h1 className="text-xl font-bold">Geliştiriciler</h1>
      {devs.length === 0 ? (
        <Empty text="Henüz run verisi yok." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {devs.map((d) => (
            <div key={d.author} className="card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <b className="text-sm">{d.author}</b>
                <span className="text-xs text-muted">{d.commits} commit</span>
              </div>
              <div className="text-xs text-muted">
                Engellenen: <span style={{ color: d.blocked ? "#f59e0b" : "#10b981" }}>{d.blocked}</span> · Repo: {d.repos}
              </div>
              {d.tickets.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {d.tickets.map((t) => (
                    <Chip key={t}>{t}</Chip>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
