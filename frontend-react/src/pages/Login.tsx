import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setRole, setToken } from "../api";
import { Field } from "../components/ui";
import { toast } from "../components/Toaster";

export function Login() {
  const nav = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function submit() {
    if (username.trim().length < 3 || password.length < 8) {
      toast("Kullanıcı adı (3+) ve parola (8+) gir.", false);
      return;
    }
    try {
      if (mode === "register") {
        const u = await api.post<{ username: string; role: string }>("/api/auth/register", {
          username: username.trim(),
          password,
        });
        toast(`Kaydedildi (${u.role}). Şimdi giriş yap.`);
        setMode("login");
        return;
      }
      const r = await api.post<{ token: string; user: { role: string } }>("/api/auth/login", {
        username: username.trim(),
        password,
      });
      setToken(r.token);
      setRole(r.user?.role || "");
      nav("/runs", { replace: true });
    } catch (e) {
      toast((e as Error).message, false);
    }
  }

  return (
    <div className="mx-auto max-w-sm card p-6 space-y-4 mt-10">
      <div>
        <h1 className="text-xl font-bold">DevOps Agentic</h1>
        <p className="text-sm text-muted">
          {mode === "login" ? "Devam etmek için giriş yap." : "Hesap oluştur. İlk hesap yönetici olur."}
        </p>
      </div>
      <Field label="Kullanıcı adı">
        <input
          className="input"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </Field>
      <Field label="Parola">
        <input
          className="input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </Field>
      <button className="btn-primary w-full" onClick={submit}>
        {mode === "login" ? "Giriş Yap" : "Kaydol"}
      </button>
      <button className="text-xs text-accent-soft w-full" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "Hesabın yok mu? Kaydol" : "Zaten hesabın var mı? Giriş yap"}
      </button>
    </div>
  );
}
