/* Calistirmalar sayfasi: /api/runs baglantisi. Sablonun kart yapisini korur. */
(function () {
  const list = document.getElementById("runs-list-container");
  if (!list || !window.DAN) return;
  const { api, toast, statusBadge, esc, timeAgo, openModal, closeModal, field, input, formValues, primaryBtn } = window.DAN;

  let runs = [];

  function card(r) {
    const blocked = r.blocked_count || 0;
    const dry = r.dry_run
      ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold" style="background:rgba(245,158,11,.15);color:#f59e0b">Dry-Run</span>'
      : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold" style="background:rgba(16,185,129,.15);color:#10b981">Canlı</span>';
    return '<div class="run-card flex flex-col p-4 rounded-xl cursor-pointer" data-repo="' + esc(r.repo) + '" data-status="' + esc(r.status)
      + '" onclick="navigateToDetail(\'' + esc(r.run_id) + '\')" '
      + 'style="background:#1e293b;border:1px solid #334155">'
      + '<div class="flex items-start justify-between gap-2 mb-1"><div class="flex flex-wrap items-center gap-2">'
      + '<span class="px-2 py-0.5 rounded text-sm font-bold" style="background:#0f172a;color:#818cf8">#run-' + esc(r.run_id) + "</span>"
      + dry + '<span class="text-xs" style="color:#94a3b8">' + timeAgo(r.created_at) + "</span>"
      + "</div>" + statusBadge(r.status) + "</div>"
      + '<div class="text-sm font-semibold truncate" style="color:#f8fafc">' + esc(r.repo) + "</div>"
      + '<div class="flex items-center justify-between pt-2 text-xs" style="color:#94a3b8"><div class="flex items-center gap-3">'
      + "<span>" + (r.commit_count || 0) + " commit</span>"
      + (blocked ? '<span style="color:#f59e0b">' + blocked + " engellenen</span>" : '<span style="color:#10b981">0 engellenen</span>')
      + '</div><span style="color:#818cf8">İncele ›</span></div></div>';
  }

  function paintStats() {
    const total = runs.length;
    const ok = runs.filter((r) => r.status === "success").length;
    const blocked = runs.filter((r) => r.status === "partially_blocked" || r.status === "pending_approval").length;
    const failed = runs.filter((r) => ["failed", "rejected"].includes(r.status)).length;
    const live = runs.filter((r) => ["queued", "running"].includes(r.status)).length;
    // istatistik seridi: 4 karttaki buyuk sayilar
    const ribbon = document.querySelector(".grid.grid-cols-2");
    if (ribbon) {
      const cards = ribbon.querySelectorAll(":scope > div");
      const vals = [total, ok, blocked, live];
      cards.forEach((c, i) => {
        if (vals[i] === undefined) return;
        const spans = c.querySelectorAll("span");
        for (const s of spans) {
          if (/^\d+$/.test(s.textContent.trim())) { s.textContent = vals[i]; break; }
        }
      });
    }
    // durum haplari: "Tümü (142)" -> gercek sayilar
    const pills = document.querySelectorAll(".status-filter-btn");
    const counts = { all: total, success: ok, blocked, failed, queued: live };
    pills.forEach((p) => {
      const t = p.textContent;
      const set = (label, n) => { p.innerHTML = p.innerHTML.replace(/\(\d+\)/, "(" + n + ")"); void label; };
      if (/Tümü/.test(t)) set(0, counts.all);
      else if (/Başarılı/.test(t)) set(0, counts.success);
      else if (/Engellendi/.test(t)) set(0, counts.blocked);
      else if (/Hata/.test(t)) set(0, counts.failed);
      else if (/Kuyrukta/.test(t)) set(0, counts.queued);
    });
  }

  function paintRepos() {
    const sel = document.getElementById("repo-filter-select");
    if (!sel) return;
    const repos = [...new Set(runs.map((r) => r.repo))];
    sel.innerHTML = '<option value="all">Tüm Depolar</option>'
      + repos.map((r) => '<option value="' + esc(r) + '">' + esc(r) + "</option>").join("");
  }

  async function load() {
    if (window.switchView) window.switchView("skeleton");
    try {
      runs = await api.get("/api/runs");
      if (!runs.length) { if (window.switchView) window.switchView("empty"); }
      else {
        list.innerHTML = runs.map(card).join("");
        if (window.switchView) window.switchView("data");
      }
      paintStats(); paintRepos();
    } catch (e) {
      runs = [];
      list.innerHTML = '<div class="rounded-xl p-6 text-center text-sm" style="background:#1e293b;border:1px solid #334155;color:#ef4444">'
        + "API'ye ulaşılamadı: " + esc(e.message) + "</div>";
      paintStats(); paintRepos();
      if (window.switchView) window.switchView("data");
      toast("Run listesi alınamadı: " + e.message);
    }
  }

  window.navigateToDetail = function (id) { location.href = "run-detail.html?id=" + encodeURIComponent(id); };

  window.triggerNewRun = function () {
    const m = openModal("<h3 class='text-base font-semibold mb-3' style='color:#f8fafc'>Yeni Run Başlat</h3>"
      + field("Repo (org/repo)", input("repo", "", "org/backend-api"))
      + field("Hedef", input("user_goal", "GitHub reposundaki son değişiklikleri incele, ilgili Jira kartlarını güncelle ve teknik bülteni hazırla."))
      + field("Commit sayısı", input("count", "3"))
      + '<label class="text-xs flex items-center gap-2 mb-4" style="color:#94a3b8">'
      + '<input type="checkbox" name="dry_run" checked /> Dry-run (Jira\'ya yazma, önce planı göster)</label>'
      + '<div class="flex justify-end gap-2">' + primaryBtn("Başlat") + "</div>");
    m.querySelector('[data-act="save"]').onclick = async () => {
      const v = formValues(m);
      try {
        const r = await api.post("/api/runs", {
          repo: v.repo, user_goal: v.user_goal || undefined,
          count: parseInt(v.count, 10) || 3, dry_run: !!v.dry_run,
        });
        closeModal(); toast("Run başlatıldı: #run-" + r.run_id); load();
      } catch (e) { toast("Başlatılamadı: " + e.message); }
    };
  };

  load();
  setInterval(load, 15000);
})();
