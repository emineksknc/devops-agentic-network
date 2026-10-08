/* Run detay sayfasi: ?id= -> GET /api/runs/{id}, onay akisi. */
(function () {
  const main = document.querySelector("body > main > div");
  if (!main || !window.DAN) return;
  const { api, toast, statusBadge, esc, timeAgo } = window.DAN;
  const id = new URLSearchParams(location.search).get("id");
  if (!id) { main.innerHTML = "<p class='text-sm' style='color:#94a3b8'>Run seçilmedi. <a href='runs.html' style='color:#818cf8'>Listeye dön</a></p>"; return; }

  function chip(t) {
    return '<span class="px-2 py-0.5 rounded text-xs font-mono" style="background:#0f172a;border:1px solid #334155;color:#94a3b8">' + esc(t) + "</span>";
  }
  function cardStyle() { return 'style="background:#1e293b;border:1px solid #334155"'; }

  async function act(approved) {
    try {
      await api.post("/api/runs/" + encodeURIComponent(id) + "/approve", { approved, note: "" });
      toast(approved ? "Onaylandı, Jira yazıldı." : "Reddedildi.");
      load();
    } catch (e) { toast("İşlem başarısız: " + e.message); }
  }
  window.DAN_APPROVE = () => act(true);
  window.DAN_REJECT = () => act(false);

  async function load() {
    let d;
    try { d = await api.get("/api/runs/" + encodeURIComponent(id)); }
    catch (e) { main.innerHTML = "<p class='text-sm' style='color:#ef4444'>Run bulunamadı.</p>"; return; }

    const dry = d.dry_run
      ? '<span class="px-2 py-0.5 rounded text-xs font-semibold" style="background:rgba(245,158,11,.15);color:#f59e0b">Dry-Run</span>'
      : '<span class="px-2 py-0.5 rounded text-xs font-semibold" style="background:rgba(16,185,129,.15);color:#10b981">Canlı</span>';

    let approveBar = "";
    if (d.status === "pending_approval") {
      approveBar = '<div class="rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3" ' + cardStyle() + '>'
        + '<div class="text-sm" style="color:#f8fafc"><b>Onay bekliyor:</b> <span style="color:#94a3b8">Jira\'ya henüz yazılmadı. Planı inceleyip onayla.</span></div>'
        + '<div class="flex gap-2"><button onclick="DAN_REJECT()" class="px-4 py-2 rounded-md text-sm" style="border:1px solid #334155;color:#94a3b8">Reddet</button>'
        + '<button onclick="DAN_APPROVE()" class="px-4 py-2 rounded-md text-sm font-semibold" style="background:#6366f1;color:#fff">Onayla ve Yaz</button></div></div>';
    }

    const units = (d.commit_units || []).map((u) => {
      const ok = u.review_status !== "FAILED";
      const badge = '<span class="px-2 py-0.5 rounded text-xs font-semibold" style="background:' + (ok ? "rgba(16,185,129,.15);color:#10b981" : "rgba(239,68,68,.15);color:#ef4444") + '">' + esc(u.review_status || "?") + "</span>";
      return '<div class="rounded-xl p-4 space-y-2" ' + cardStyle() + '>'
        + '<div class="flex flex-wrap items-center gap-2"><span class="text-xs font-mono" style="color:#818cf8">' + esc(u.short_sha || "") + "</span>"
        + badge + (u.jira_ids || []).map(chip).join("") + "</div>"
        + '<div class="text-sm font-semibold" style="color:#f8fafc">' + esc(u.message || "") + "</div>"
        + '<div class="text-xs" style="color:#94a3b8">Yazar: ' + esc(u.author || "?") + "</div>"
        + (u.review_comment ? '<div class="text-xs rounded-md p-2" style="background:#0f172a;color:#c7c4d7">' + esc(u.review_comment) + "</div>" : "")
        + "</div>";
    }).join("") || '<div class="text-xs" style="color:#94a3b8">Commit yok.</div>';

    const actions = (d.jira_actions || []).map((a) =>
      '<div class="flex flex-wrap items-center gap-2 text-xs rounded-lg px-3 py-2" ' + cardStyle() + '>'
      + chip(a.ticket_id)
      + '<span style="color:#94a3b8">' + esc(a.state) + "</span>"
      + (a.transition_to ? '<span style="color:#c7c4d7">→ ' + esc(a.transition_to) + "</span>" : "")
      + (a.skipped_reason ? '<span style="color:#f59e0b">' + esc(a.skipped_reason) + "</span>" : "")
      + "</div>").join("");

    main.innerHTML =
      '<a href="runs.html" class="hidden lg:inline-flex items-center gap-2 text-xs mb-1" style="color:#94a3b8">‹ Tüm Çalıştırmalar</a>'
      + '<div class="rounded-xl p-4 flex flex-wrap items-center gap-2" ' + cardStyle() + '>'
      + '<span class="font-mono font-bold" style="color:#818cf8">#run-' + esc(d.run_id) + "</span>"
      + dry + statusBadge(d.status)
      + '<span class="text-xs" style="color:#94a3b8">' + esc(d.repo) + " · " + timeAgo(d.created_at) + "</span></div>"
      + approveBar
      + '<div class="rounded-xl p-4" ' + cardStyle() + '><h3 class="text-sm font-semibold mb-2" style="color:#f8fafc">Sürüm Bülteni</h3>'
      + '<div class="text-xs whitespace-pre-wrap" style="color:#c7c4d7">' + esc(d.final_report || d.error || "—") + "</div></div>"
      + '<div class="space-y-2"><h3 class="text-sm font-semibold" style="color:#f8fafc">Commitler (' + (d.commit_units || []).length + ")</h3>" + units + "</div>"
      + (actions ? '<div class="space-y-2"><h3 class="text-sm font-semibold" style="color:#f8fafc">Jira Aksiyonları</h3>' + actions + "</div>" : "");
  }
  load();
})();
