/* Ayarlar: sablon tasarim aynen korunur, ici canli API'ye baglanir.
   Kartlar varsayilan baglantilari duzenler (github-default, jira-default, llm-default). */
(function () {
  if (!window.DAN) return;
  const { api, esc } = window.DAN;
  const $ = (s) => document.querySelector(s);
  const tToast = (m) => { if (window.triggerToast) window.triggerToast(m); };

  let GH = null, JIRA = null, LLM = null;

  function byKind(conns, kind, id) {
    return conns.find((c) => c.id === id) || conns.find((c) => c.kind === kind && c.is_default) || conns.find((c) => c.kind === kind);
  }

  async function load() {
    let conns = [];
    try { conns = await api.get("/api/connections"); }
    catch (e) { tToast("Bağlantılar yüklenemedi: " + e.message); return; }
    GH = byKind(conns, "github"); JIRA = byKind(conns, "jira"); LLM = byKind(conns, "llm");

    setVal("[data-bind='gh-org']", GH ? GH.owner : "");
    setVal("#github-token", "");
    const gt = $("#github-token"); if (gt) gt.placeholder = GH && GH.token === "***masked***" ? "kayıtlı (değiştirmek için yaz)" : "";
    const wh = $("#webhook-token");
    if (wh) {
      wh.value = "";
      wh.disabled = false;
      wh.placeholder = GH && GH.webhook_secret === "***masked***" ? "kayıtlı (değiştirmek için yaz)" : "whsec_...";
      wh.title = "GitHub webhook secret (repo ayarlarındaki ile aynı olmalı)";
      let note = $("#wh-note");
      if (!note) {
        note = document.createElement("div");
        note.id = "wh-note";
        note.className = "text-xs mt-1";
        note.style.color = "#64748b";
        wh.parentElement.after(note);
      }
      note.textContent = "Endpoint: " + location.origin + "/api/webhooks/github";
    }
    try {
      const pols = await api.get("/api/policies");
      const repos = pols.map((p) => p.repo).join(", ");
      const ri = document.querySelector("[data-bind='gh-repos']");
      if (ri) { ri.value = repos; ri.readOnly = true; ri.title = "İzlenen repolar Politikalar sayfasından yönetilir"; }
    } catch (e) {}

    if (JIRA) {
      setVal("[data-bind='jira-domain']", JIRA.base_url);
      setVal("[data-bind='jira-email']", JIRA.email);
      setVal("#jira-token", "");
    }
    if (LLM) {
      setVal("[data-bind='llm-endpoint']", LLM.base_url);
      setVal("[data-bind='llm-max']", LLM.max_tokens || 2048);
      const sl = document.querySelector("#temp-slider");
      if (sl) { sl.value = LLM.temperature != null ? LLM.temperature : 0.3; const tv = $("#temp-val"); if (tv) tv.innerText = sl.value; }
      await fillModels(LLM);
    }
    try {
      const s = await api.get("/api/settings");
      const rt = $("#redaction-toggle");
      if (rt) { rt.checked = !!s.redact_secrets; paintBadge(rt.checked); }
    } catch (e) {}
    renderExtra(conns);
  }

  function setVal(sel, v) { const el = document.querySelector(sel); if (el) el.value = v == null ? "" : v; }
  function getVal(sel) { const el = document.querySelector(sel); return el ? el.value : ""; }

  async function fillModels() {
    const sel = document.querySelector("[data-bind='llm-model']");
    if (!sel || !LLM) return;
    try {
      const models = await api.get("/api/llm/models?conn_id=" + encodeURIComponent(LLM.id));
      sel.innerHTML = models.map((x) => '<option value="' + esc(x.name) + '">' + esc(x.name) + "</option>").join("");
      if (LLM.model) sel.value = LLM.model;
    } catch (e) { sel.innerHTML = '<option value="' + esc(LLM.model || "") + '">' + esc(LLM.model || "") + "</option>"; }
  }

  function paintBadge(on) {
    const b = $("#redaction-status-badge");
    if (b) { b.innerText = on ? "Aktif" : "Kapalı"; }
  }

  function showResult(bindName, msg, ok) {
    const btn = document.querySelector('[data-bind="' + bindName + '"]');
    if (!btn || !btn.parentElement) { tToast(msg); return; }
    let el = btn.parentElement.querySelector("[data-test-result]");
    if (!el) {
      el = document.createElement("div");
      el.setAttribute("data-test-result", "1");
      el.className = "text-xs mt-2";
      btn.parentElement.appendChild(el);
    }
    el.style.color = ok ? "#10b981" : "#ef4444";
    el.textContent = msg;
    tToast(msg);
  }

  async function doTest(kind, bindName, label, saver) {
    // Once ekrandaki degerleri kaydet, sonra test et (yoksa eski token denenir)
    if (saver) {
      const saved = await saver(true);
      if (!saved) return;
    }
    const conn = kind === "github" ? GH : kind === "jira" ? JIRA : LLM;
    if (!conn) { showResult(bindName, "Bağlantı yok.", false); return; }
    showResult(bindName, label + " test ediliyor…", true);
    try {
      const r = await api.post("/api/connections/" + encodeURIComponent(conn.id) + "/test", {});
      showResult(bindName, (r.ok ? "✓ " : "✗ ") + label + ": " + (r.detail || r.status), !!r.ok);
    } catch (e) { showResult(bindName, "✗ " + label + ": " + e.message, false); }
  }

  async function saveGH(silent) {
    if (!GH) return false;
    const token = ($("#github-token") || {}).value || "";
    const secret = ($("#webhook-token") || {}).value || "";
    const body = { name: GH.name, kind: "github", base_url: GH.base_url, owner: getVal("[data-bind='gh-org']"), email: "", project_key: "", provider: "", model: "", temperature: 0.3, max_tokens: 2048, is_default: GH.is_default };
    if (token) body.token = token;
    if (secret) body.webhook_secret = secret;
    try {
      await api.put("/api/connections/" + encodeURIComponent(GH.id), body);
      const fresh = await api.get("/api/connections");
      GH = byKind(fresh, "github");
      if (!silent) { tToast("GitHub ayarları kaydedildi."); load(); }
      return true;
    } catch (e) { tToast("Kaydedilemedi: " + e.message); return false; }
  }
  async function saveJira(silent) {
    if (!JIRA) return false;
    const token = ($("#jira-token") || {}).value || "";
    const body = { name: JIRA.name, kind: "jira", base_url: getVal("[data-bind='jira-domain']"), owner: "", email: getVal("[data-bind='jira-email']"), project_key: JIRA.project_key, provider: "", model: "", temperature: 0.3, max_tokens: 2048, is_default: JIRA.is_default };
    if (token) body.token = token;
    try {
      await api.put("/api/connections/" + encodeURIComponent(JIRA.id), body);
      const fresh = await api.get("/api/connections");
      JIRA = byKind(fresh, "jira");
      if (!silent) { tToast("Jira ayarları kaydedildi."); load(); }
      return true;
    } catch (e) { tToast("Kaydedilemedi: " + e.message); return false; }
  }
  async function saveLLM(silent) {
    if (!LLM) return false;
    const sl = document.querySelector("#temp-slider");
    const body = { name: LLM.name, kind: "llm", base_url: getVal("[data-bind='llm-endpoint']"), owner: "", email: "", project_key: "", provider: LLM.provider || "ollama", model: getVal("[data-bind='llm-model']"), temperature: sl ? parseFloat(sl.value) : 0.3, max_tokens: parseInt(getVal("[data-bind='llm-max']"), 10) || 2048, is_default: LLM.is_default, token: "" };
    try {
      await api.put("/api/connections/" + encodeURIComponent(LLM.id), body);
      const fresh = await api.get("/api/connections");
      LLM = byKind(fresh, "llm");
      if (!silent) { tToast("LLM ayarları kaydedildi."); load(); }
      return true;
    } catch (e) { tToast("Kaydedilemedi: " + e.message); return false; }
  }

  function wire() {
    const map = { "gh-test": () => doTest("github", "gh-test", "GitHub", saveGH), "gh-save": () => saveGH(false), "jira-test": () => doTest("jira", "jira-test", "Jira", saveJira), "jira-save": () => saveJira(false), "llm-test": () => doTest("llm", "llm-test", "LLM", saveLLM), "llm-save": () => saveLLM(false), "sync-all": async () => { await saveGH(true); await saveJira(true); await saveLLM(true); tToast("Tümü kaydedildi."); load(); } };
    document.querySelectorAll("[data-bind]").forEach((b) => {
      const k = b.dataset.bind;
      if (!map[k]) return;
      b.removeAttribute("onclick");
      b.addEventListener("click", (e) => { e.preventDefault(); map[k](); });
    });
    const rt = $("#redaction-toggle");
    if (rt) {
      rt.removeAttribute("onchange");
      rt.addEventListener("change", async () => {
        try { await api.put("/api/settings", { redact_secrets: rt.checked }); paintBadge(rt.checked); tToast("Redaksiyon " + (rt.checked ? "açıldı" : "kapatıldı") + "."); }
        catch (e) { tToast("Kaydedilemedi: " + e.message); }
      });
    }
  }

  function renderExtra(conns) {
    let box = $("#extra-conns");
    if (!box) {
      const main = document.querySelector("body > main > div");
      if (!main) return;
      box = document.createElement("div");
      box.id = "extra-conns";
      main.appendChild(box);
    }
    const ids = [GH && GH.id, JIRA && JIRA.id, LLM && LLM.id].filter(Boolean);
    const rest = conns.filter((c) => ids.indexOf(c.id) === -1);
    box.innerHTML = '<div class="rounded-xl p-4" style="background:#1e293b;border:1px solid #334155">'
      + '<div class="flex items-center justify-between mb-2"><h3 class="text-sm font-semibold" style="color:#f8fafc">Diğer Bağlantılar (' + rest.length + ")</h3>"
      + '<button id="xc-add" class="text-xs px-3 py-1.5 rounded-md" style="background:#6366f1;color:#fff">+ Ekle</button></div>'
      + (rest.map((c) => '<div class="flex items-center justify-between py-1.5 text-xs" style="border-top:1px solid #334155;color:#94a3b8">'
        + "<span><b style='color:#f8fafc'>" + esc(c.name) + "</b> · " + esc(c.kind) + (c.provider ? " · " + esc(c.provider) : "") + "</span>"
        + '<span><button data-xc-test="' + esc(c.id) + '" class="mr-3" style="color:#818cf8">Test</button>'
        + '<button data-xc-del="' + esc(c.id) + '" style="color:#ef4444">Sil</button></span></div>').join("")
        || '<div class="text-xs" style="color:#64748b">Ek bağlantı yok. Birden fazla GitHub/Jira buradan eklenir.</div>')
      + "</div>";
    const add = box.querySelector("#xc-add");
    if (add) add.onclick = () => connModal();
    box.querySelectorAll("[data-xc-test]").forEach((b) => (b.onclick = async () => {
      try { const r = await api.post("/api/connections/" + encodeURIComponent(b.dataset.xcTest) + "/test", {}); tToast((r.ok ? "✓ " : "✗ ") + (r.detail || r.status)); }
      catch (e) { tToast("✗ " + e.message); }
    }));
    box.querySelectorAll("[data-xc-del]").forEach((b) => (b.onclick = async () => {
      if (!confirm("Silinsin mi?")) return;
      try { await api.del("/api/connections/" + encodeURIComponent(b.dataset.xcDel)); load(); }
      catch (e) { tToast("Silinemedi: " + e.message); }
    }));
  }

  function connModal() {
    const { openModal, closeModal, field, input, formValues, primaryBtn } = window.DAN;
    const m = openModal("<h3 class='text-base font-semibold mb-3' style='color:#f8fafc'>Yeni Bağlantı</h3>"
      + field("Ad", input("name", ""))
      + field("Tür", '<select name="kind" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc"><option value="github">GitHub</option><option value="jira">Jira</option><option value="llm">LLM</option></select><div class="mb-3"></div>')
      + field("Base URL", input("base_url", ""))
      + field("Owner / E-posta", input("owner", ""))
      + field("Token", '<input type="password" name="token" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc" /><div class="mb-3"></div>')
      + field("Proje anahtarı (jira)", input("project_key", ""))
      + '<div class="flex justify-end">' + primaryBtn("Kaydet") + "</div>");
    m.querySelector('[data-act="save"]').onclick = async () => {
      try { await api.post("/api/connections", formValues(m)); closeModal(); load(); }
      catch (e) { tToast("Kaydedilemedi: " + e.message); }
    };
  }

  wire();
  load();
})();
