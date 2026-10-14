/* Ajanlar: ac/kapa + system prompt override (/api/agents). */
(function () {
  const main = document.querySelector("body > main > div");
  if (!main || !window.DAN) return;
  const { api, toast, esc, openModal, closeModal, field, formValues, primaryBtn } = window.DAN;
  const cs = 'style="background:#1e293b;border:1px solid #334155"';

  async function load() {
    let agents = [];
    try { agents = await api.get("/api/agents"); } catch (e) { toast("Yüklenemedi: " + e.message); return; }
    main.innerHTML = '<h1 class="text-xl font-bold" style="color:#f8fafc">Ajanlar</h1>'
      + '<div class="grid gap-3 xl:grid-cols-2">' + agents.map(agentCard).join("") + "</div>";
    main.querySelectorAll("[data-toggle]").forEach((b) => (b.onclick = async () => {
      try { await api.put("/api/agents/" + b.dataset.toggle, { enabled: b.dataset.on === "1" }); load(); }
      catch (e) { toast("Güncellenemedi: " + e.message); }
    }));
    main.querySelectorAll("[data-prompt]").forEach((b) => (b.onclick = () => promptModal(JSON.parse(b.dataset.prompt))));
  }
  function agentCard(a) {
    const dot = a.enabled ? "#10b981" : "#64748b";
    return '<div class="rounded-xl p-4 space-y-2" ' + cs + '>'
      + '<div class="flex items-center justify-between"><b class="text-sm" style="color:#f8fafc"><span style="color:' + dot + '">●</span> ' + esc(a.name) + "</b>"
      + '<button data-toggle="' + esc(a.name) + '" data-on="' + (a.enabled ? "0" : "1") + '" class="text-xs" style="color:#818cf8">'
      + (a.enabled ? "Kapat" : "Aç") + "</button></div>"
      + '<div class="text-xs" style="color:#94a3b8">' + (a.enabled ? "Aktif" : "Devre dışı (akışta atlanır)")
      + (a.customized ? " · <span style='color:#f59e0b'>özel prompt</span>" : "") + "</div>"
      + '<button data-prompt=\'' + esc(JSON.stringify(a)) + '\' class="text-xs" style="color:#818cf8">System promptu düzenle</button></div>';
  }
  function promptModal(a) {
    const m = openModal("<h3 class='text-base font-semibold mb-3' style='color:#f8fafc'>" + esc(a.name) + "</h3>"
      + field("Varsayılan", '<div class="text-xs rounded-md p-2 max-h-32 overflow-auto" style="background:#0f172a;color:#94a3b8">' + esc(a.default_prompt || "—") + "</div><div class='mb-3'></div>")
      + field("Özel prompt (boş = varsayılan)", '<textarea name="system_prompt" rows="5" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc">' + esc(a.system_prompt || "") + "</textarea><div class='mb-3'></div>")
      + '<div class="flex justify-end">' + primaryBtn("Kaydet") + "</div>");
    m.querySelector('[data-act="save"]').onclick = async () => {
      try { await api.put("/api/agents/" + encodeURIComponent(a.name), { system_prompt: formValues(m).system_prompt }); closeModal(); load(); }
      catch (e) { toast("Kaydedilemedi: " + e.message); }
    };
  }
  load();
})();
