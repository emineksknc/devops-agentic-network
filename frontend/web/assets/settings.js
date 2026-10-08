/* Ayarlar: /api/connections CRUD (github/jira/llm). Token maskeli gelir. */
(function () {
  const main = document.querySelector("body > main > div");
  if (!main || !window.DAN) return;
  const { api, toast, esc, openModal, closeModal, field, input, formValues, primaryBtn } = window.DAN;
  const cs = 'style="background:#1e293b;border:1px solid #334155"';
  const KINDS = [["github", "GitHub"], ["jira", "Jira"], ["llm", "LLM"]];

  async function load() {
    let conns = [];
    try { conns = await api.get("/api/connections"); } catch (e) { toast("Yüklenemedi: " + e.message); return; }
    main.innerHTML = '<div class="flex items-center justify-between"><h1 class="text-xl font-bold" style="color:#f8fafc">Bağlantılar</h1>'
      + '<button id="c-new" class="px-4 py-2 rounded-md text-sm font-semibold" style="background:#6366f1;color:#fff">+ Yeni Bağlantı</button></div>'
      + KINDS.map(([k, label]) => {
        const items = conns.filter((c) => c.kind === k);
        return '<div><h2 class="text-sm font-semibold mb-2" style="color:#c7c4d7">' + label + "</h2>"
          + '<div class="grid gap-3 xl:grid-cols-2">' + (items.map(connCard).join("") || emptyCard()) + "</div></div>";
      }).join("");
    document.getElementById("c-new").onclick = () => editModal({ kind: "github" });
    main.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => {
      const c = conns.find((x) => x.id === b.dataset.edit); if (c) editModal(c);
    }));
    main.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
      if (!confirm("Bağlantı silinsin mi?")) return;
      try { await api.del("/api/connections/" + encodeURIComponent(b.dataset.del)); load(); }
      catch (e) { toast("Silinemedi: " + e.message); }
    }));
  }
  function emptyCard() { return '<div class="rounded-xl p-4 text-xs" ' + cs + ' style="color:#94a3b8">Kayıt yok.</div>'; }
  function connCard(c) {
    const detail = c.kind === "github" ? esc(c.base_url) + " · " + esc(c.owner)
      : c.kind === "jira" ? esc(c.base_url) + " · " + esc(c.project_key)
      : esc(c.provider || "ollama") + " · " + esc(c.model);
    return '<div class="rounded-xl p-4 space-y-1" ' + cs + '>'
      + '<div class="flex items-center justify-between"><b class="text-sm" style="color:#f8fafc">' + esc(c.name) + "</b>"
      + (c.is_default ? '<span class="text-xs" style="color:#10b981">varsayılan</span>' : "") + "</div>"
      + '<div class="text-xs font-mono" style="color:#94a3b8">' + esc(c.id) + "</div>"
      + '<div class="text-xs" style="color:#94a3b8">' + detail + "</div>"
      + '<div class="flex gap-3 pt-1"><button data-edit="' + esc(c.id) + '" class="text-xs" style="color:#818cf8">Düzenle</button>'
      + '<button data-del="' + esc(c.id) + '" class="text-xs" style="color:#ef4444">Sil</button></div></div>';
  }
  function editModal(c) {
    const kindSel = '<select name="kind" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc">'
      + KINDS.map(([k, l]) => '<option value="' + k + '"' + (c.kind === k ? " selected" : "") + ">" + l + "</option>").join("") + "</select><div class='mb-3'></div>";
    const m = openModal("<h3 class='text-base font-semibold mb-3' style='color:#f8fafc'>Bağlantı</h3>"
      + field("Ad", input("name", c.name || ""))
      + field("Tür", kindSel)
      + field("Base URL", input("base_url", c.base_url || "", "https://..."))
      + field("Owner (github)", input("owner", c.owner || ""))
      + field("E-posta (jira)", input("email", c.email || ""))
      + field("Token (boş = değişmez)", '<input type="password" name="token" value="" placeholder="***" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc" /><div class="mb-3"></div>')
      + field("Proje anahtarı (jira)", input("project_key", c.project_key || "", "SCRUM"))
      + field("Provider (llm)", '<select name="provider" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc">'
        + ["ollama", "openai", "anthropic"].map((p) => '<option value="' + p + '"' + (c.provider === p ? " selected" : "") + ">" + p + "</option>").join("") + "</select><div class='mb-3'></div>")
      + field("Model (llm)", input("model", c.model || "", "llama3.1 / gpt-4o-mini").replace('class="w-full', 'list="m-models" class="w-full')
        + '<datalist id="m-models"></datalist><div id="m-hint" class="text-xs mt-1" style="color:#64748b">Kurulu modeller yükleniyor…</div><div class=\'mb-3\'></div>')
      + '<label class="text-xs flex items-center gap-2 mb-4" style="color:#94a3b8"><input type="checkbox" name="is_default" ' + (c.is_default ? "checked" : "") + " /> Varsayılan yap</label>"
      + '<div class="flex justify-end">' + primaryBtn("Kaydet") + "</div>");
    const dl = m.querySelector("#m-models");
    const hint = m.querySelector("#m-hint");
    const provSel = m.querySelector('select[name="provider"]');
    async function fillModels() {
      const kindSel = m.querySelector('select[name="kind"]');
      if (hint) hint.style.display = (kindSel && kindSel.value === "llm") ? "" : "none";
      if (!kindSel || kindSel.value !== "llm") return;
      const prov = provSel ? provSel.value : "ollama";
      const q = c.id ? "?conn_id=" + encodeURIComponent(c.id) : "?provider=" + encodeURIComponent(prov);
      try {
        const models = await api.get("/api/llm/models" + q);
        dl.innerHTML = models.map((x) => '<option value="' + esc(x.name) + '">').join("");
        if (hint) hint.textContent = models.length ? models.length + " model bulundu (" + (models[0].source || "") + ")" : "Model bulunamadı";
      } catch (e) { if (hint) hint.textContent = "Liste alınamadı: " + e.message; }
    }
    const kindSel2 = m.querySelector('select[name="kind"]');
    if (provSel) provSel.onchange = fillModels;
    if (kindSel2) kindSel2.onchange = fillModels;
    fillModels();
    m.querySelector('[data-act="save"]').onclick = async () => {
      const v = formValues(m);
      try {
        if (c.id) await api.put("/api/connections/" + encodeURIComponent(c.id), v);
        else await api.post("/api/connections", v);
        closeModal(); load();
      } catch (e) { toast("Kaydedilemedi: " + e.message); }
    };
  }
  load();
})();
