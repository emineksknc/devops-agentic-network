/* Gelistiriciler: /api/developers — kim ne yapti. */
(function () {
  const main = document.querySelector("body > main > div");
  if (!main || !window.DAN) return;
  const { api, toast, esc } = window.DAN;
  const cs = 'style="background:#1e293b;border:1px solid #334155"';

  async function load() {
    let devs = [];
    try { devs = await api.get("/api/developers"); } catch (e) { toast("Yüklenemedi: " + e.message); return; }
    main.innerHTML = '<h1 class="text-xl font-bold" style="color:#f8fafc">Geliştiriciler</h1>'
      + '<div class="grid gap-3 xl:grid-cols-2">' + (devs.map(devCard).join("")
        || '<div class="rounded-xl p-6 text-center text-sm" ' + cs + ' style="color:#94a3b8">Henüz run verisi yok.</div>') + "</div>";
  }
  function devCard(d) {
    return '<div class="rounded-xl p-4 space-y-2" ' + cs + '>'
      + '<div class="flex items-center justify-between"><b class="text-sm" style="color:#f8fafc">' + esc(d.author) + "</b>"
      + '<span class="text-xs" style="color:#94a3b8">' + d.commits + " commit</span></div>"
      + '<div class="text-xs" style="color:#94a3b8">Engellenen: <span style="color:' + (d.blocked ? "#f59e0b" : "#10b981") + '">' + d.blocked + "</span>"
      + " · Repo: " + d.repos + "</div>"
      + (d.tickets && d.tickets.length ? '<div class="flex flex-wrap gap-1">' + d.tickets.map((t) =>
        '<span class="px-2 py-0.5 rounded text-xs font-mono" style="background:#0f172a;border:1px solid #334155;color:#94a3b8">' + esc(t) + "</span>").join("") + "</div>" : "")
      + "</div>";
  }
  load();
})();
