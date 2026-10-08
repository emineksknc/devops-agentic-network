/* Denetim izi: /api/audit salt-okunur. */
(function () {
  const main = document.querySelector("body > main > div");
  if (!main || !window.DAN) return;
  const { api, toast, esc, input } = window.DAN;
  const cs = 'style="background:#1e293b;border:1px solid #334155"';

  async function load() {
    const t = (document.getElementById("a-ticket") || {}).value || "";
    const r = (document.getElementById("a-repo") || {}).value || "";
    let rows = [];
    try {
      rows = await api.get("/api/audit?ticket=" + encodeURIComponent(t) + "&repo=" + encodeURIComponent(r));
    } catch (e) { toast("Yüklenemedi: " + e.message); return; }
    const tb = document.getElementById("a-rows");
    if (!tb) return;
    tb.innerHTML = rows.map((a) =>
      "<tr style='border-top:1px solid #334155'>"
      + "<td class='py-2 pr-3 font-mono text-xs' style='color:#818cf8'>" + esc(a.ticket_id) + "</td>"
      + "<td class='py-2 pr-3 text-xs' style='color:#94a3b8'>" + esc(a.repo) + "</td>"
      + "<td class='py-2 pr-3 text-xs' style='color:#94a3b8'><a href='run-detail.html?id=" + esc(a.run_id) + "' style='color:#818cf8'>#run-" + esc(a.run_id) + "</a></td>"
      + "<td class='py-2 pr-3 text-xs' style='color:#c7c4d7'>" + esc(a.state) + (a.transition_to ? " → " + esc(a.transition_to) : "") + "</td>"
      + "<td class='py-2 text-xs' style='color:#94a3b8'>" + esc(a.created_at || "").slice(0, 16).replace("T", " ") + "</td></tr>"
    ).join("") || "<tr><td class='py-4 text-xs' style='color:#94a3b8'>Kayıt yok.</td></tr>";
  }
  main.innerHTML = '<h1 class="text-xl font-bold" style="color:#f8fafc">Denetim İzi</h1>'
    + '<div class="flex flex-col sm:flex-row gap-2">'
    + '<input id="a-ticket" placeholder="Bilet filtrele (örn. SCRUM-6)" class="flex-1 px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc" />'
    + '<input id="a-repo" placeholder="Repo filtrele" class="flex-1 px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc" />'
    + '<button id="a-go" class="px-4 py-2 rounded-md text-sm font-semibold" style="background:#6366f1;color:#fff">Filtrele</button></div>'
    + '<div class="rounded-xl p-4 overflow-x-auto" ' + cs + '><table class="w-full text-left">'
    + "<thead><tr class='text-xs' style='color:#94a3b8'><th class='pr-3 pb-1'>Bilet</th><th class='pr-3 pb-1'>Repo</th><th class='pr-3 pb-1'>Run</th><th class='pr-3 pb-1'>Durum</th><th class='pb-1'>Zaman</th></tr></thead>"
    + '<tbody id="a-rows"></tbody></table></div>';
  document.getElementById("a-go").onclick = load;
  load();
})();
