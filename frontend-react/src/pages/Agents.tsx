import { useCallback, useEffect, useState } from "react";
import { api, type AgentInfo } from "../api";
import { Empty, Field, Modal } from "../components/ui";
import { toast } from "../components/Toaster";

export function Agents() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [editing, setEditing] = useState<AgentInfo | null>(null);
  const [prompt, setPrompt] = useState("");

  const load = useCallback(async () => {
    try {
      setAgents(await api.get<AgentInfo[]>("/api/agents"));
    } catch (e) {
      toast(`Yüklenemedi: ${(e as Error).message}`, false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggle(a: AgentInfo) {
    try {
      await api.put(`/api/agents/${a.name}`, { enabled: !a.enabled });
      load();
    } catch (e) {
      toast(`Güncellenemedi: ${(e as Error).message}`, false);
    }
  }

  async function savePrompt() {
    if (!editing) return;
    try {
      await api.put(`/api/agents/${editing.name}`, { system_prompt: prompt });
      setEditing(null);
      toast("Prompt kaydedildi.");
      load();
    } catch (e) {
      toast(`Kaydedilemedi: ${(e as Error).message}`, false);
    }
  }

  return (
    <>
      <h1 className="text-xl font-bold">Ajanlar</h1>
      {agents.length === 0 ? (
        <Empty text="Ajan bulunamadı." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {agents.map((a) => (
            <div key={a.name} className="card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <b className="text-sm">
                  <span style={{ color: a.enabled ? "#10b981" : "#64748b" }}>●</span> {a.name}
                </b>
                <button className="text-xs text-accent-soft" onClick={() => toggle(a)}>
                  {a.enabled ? "Kapat" : "Aç"}
                </button>
              </div>
              <div className="text-xs text-muted">
                {a.enabled ? "Aktif" : "Devre dışı (akışta atlanır)"}
                {a.customized && <span style={{ color: "#f59e0b" }}> · özel prompt</span>}
              </div>
              <button
                className="text-xs text-accent-soft"
                onClick={() => {
                  setEditing(a);
                  setPrompt(a.system_prompt || "");
                }}
              >
                System promptu düzenle
              </button>
            </div>
          ))}
        </div>
      )}
      {editing && (
        <Modal title={editing.name} onClose={() => setEditing(null)}>
          <Field label="Varsayılan">
            <div className="text-xs rounded-md p-2 max-h-32 overflow-auto" style={{ background: "#0f172a", color: "#94a3b8" }}>
              {editing.default_prompt || "—"}
            </div>
          </Field>
          <Field label="Özel prompt (boş = varsayılan)">
            <textarea className="input" rows={5} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          </Field>
          <div className="flex justify-end">
            <button className="btn-primary" onClick={savePrompt}>
              Kaydet
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
