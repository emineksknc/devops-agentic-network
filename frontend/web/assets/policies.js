/* Politikalar: /api/policies + baglanti secimi. */
(function () {
  const main = document.querySelector("body > main > div");
  if (!main || !window.DAN) return;
  const { api, toast, esc, openModal, closeModal, field, input, formValues, primaryBtn } = window.DAN;
  let conns = [];

  function connName(id) { const c = conns.find((x) => x.id === id); return c ? c.name : "—"; }
  const cs = 'style="background:#1e293b;border:1px solid #334155"';

  async function load() {
    try {
      const [pols, c] = await Promise.all([api.get("/api/policies"), api.get("/api/connections")]);
      conns = c;
      main.innerHTML = '<div class="flex items-center justify-between"><h1 class="text-xl font-bold" style="color:#f8fafc">Politikalar</h1>'
        + '<button id="p-new" class="px-4 py-2 rounded-md text-sm font-semibold" style="background:#6366f1;color:#fff">+ Yeni Politika</button></div>'
        + '<div class="grid gap-3 xl:grid-cols-2">' + (pols.map(policyCard).join("") || emptyState()) + "</div>";
      document.getElementById("p-new").onclick = () => editModal({});
      main.querySelectorAll("[data-edit]").forEach((b) => (b.onclick = () => editModal(JSON.parse(b.dataset.edit))));
      main.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
        if (!confirm("Silinsin mi?")) return;
        await api.del("/api/policies/" + encodeURIComponent(b.dataset.del)); load();
      }));
    } catch (e) { toast("Yüklenemedi: " + e.message); }
  }
  function emptyState() {
    return '<div class="rounded-xl p-6 text-center text-sm" ' + cs + ' style="color:#94a3b8">Henüz politika yok. İlkini oluştur.</div>';
  }
  function policyCard(p) {
    return '<div class="rounded-xl p-4 space-y-2" ' + cs + '>'
      + '<div class="flex items-center justify-between"><b class="text-sm" style="color:#f8fafc">' + esc(p.repo) + "</b>"
      + '<div class="flex gap-2"><button data-edit=\'' + esc(JSON.stringify(p)) + '\' class="text-xs" style="color:#818cf8">Düzenle</button>'
      + '<button data-del="' + esc(p.repo) + '" class="text-xs" style="color:#ef4444">Sil</button></div></div>'
      + '<div class="text-xs space-y-1" style="color:#94a3b8">'
      + "<div>Proje: " + esc(p.jira_project || "—") + "</div>"
      + "<div>Geçerse → " + esc(p.on_pass_transition) + (p.auto_write_pass ? " (otomatik)" : " (onaylı)") + "</div>"
      + "<div>Kalırsa → " + esc(p.on_fail_transition) + (p.auto_write_fail ? " (otomatik)" : " (onaylı)") + "</div>"
      + "<div>GitHub: " + esc(connName(p.github_conn_id)) + " · Jira: " + esc(connName(p.jira_conn_id)) + "</div>"
      + (p.dry_run_default ? "<div>Dry-run varsayılan</div>" : "") + "</div></div>";
  }
  function connOpts(kind, sel) {
    return conns.filter((c) => c.kind === kind)
      .map((c) => '<option value="' + esc(c.id) + '"' + (c.id === sel ? " selected" : "") + ">" + esc(c.name) + "</option>").join("");
  }
  function editModal(p) {
    const m = openModal("<h3 class='text-base font-semibold mb-3' style='color:#f8fafc'>Politika</h3>"
      + field("Repo (org/repo)", input("repo", p.repo || "", "org/backend-api"))
      + field("Jira projesi", input("jira_project", p.jira_project || "", "SCRUM"))
      + field("Geçerse geçiş", input("on_pass_transition", p.on_pass_transition || "In Review"))
      + field("Kalırsa geçiş", input("on_fail_transition", p.on_fail_transition || "Blocked"))
      + field("GitHub bağlantısı", '<select name="github_conn_id" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc"><option value="">Varsayılan</option>' + connOpts("github", p.github_conn_id) + "</select><div class='mb-3'></div>")
      + field("Jira bağlantısı", '<select name="jira_conn_id" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc"><option value="">Varsayılan</option>' + connOpts("jira", p.jira_conn_id) + "</select><div class='mb-3'></div>")
      + '<div class="text-xs space-y-2 mb-4" style="color:#94a3b8">'
      + tgl("auto_write_pass", "Geçerse otomatik yaz", p.auto_write_pass !== false)
      + tgl("auto_write_fail", "Kalırsa otomatik yaz", !!p.auto_write_fail)
      + tgl("require_approval", "Onay zorunlu", p.require_approval !== false)
      + tgl("dry_run_default", "Dry-run varsayılan", p.dry_run_default !== false) + "</div>"
      + '<div class="flex justify-end">' + primaryBtn("Kaydet") + "</div>");
    m.querySelector('[data-act="save"]').onclick = async () => {
      try { await api.post("/api/policies", formValues(m)); closeModal(); load(); }
      catch (e) { toast("Kaydedilemedi: " + e.message); }
    };
  }
  function tgl(name, label, on) {
    return '<label class="flex items-center gap-2"><input type="checkbox" name="' + name + '"' + (on ? " checked" : "") + " /> " + label + "</label>";
  }
  load();
})();
