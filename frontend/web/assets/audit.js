/* Denetim izi: sablon akis/filtre/export tasarimi korunur, satirlar canli.
   article[data-ticket|data-action|data-actor] yapisi sablon filtresiyle uyumlu. */
(function () {
  if (!window.DAN) return;
  const { api, esc } = window.DAN;
  const stream = document.getElementById("audit-log-stream");
  if (!stream) return;
  let ROWS = [];

  function stateColor(s) {
    return { applied: "#10b981", planned: "#818cf8", skipped: "#f59e0b", failed: "#ef4444" }[s] || "#94a3b8";
  }

  function articleFor(tpl, a) {
    const el = tpl.cloneNode(true);
    el.dataset.ticket = a.ticket_id || "";
    el.dataset.action = a.state || "";
    el.dataset.actor = a.trigger || "api";
    let html = el.innerHTML;
    // zaman + run + bilet metinleri: bilinen sablon orneklerini degistir
    html = html.replace(/Bugün 14:32:10|Dün[^<]{0,20}|#run-84f9a2/g, (m) => {
      if (m.startsWith("#run")) return "#run-" + a.run_id;
      return (a.created_at || "").slice(0, 16).replace("T", " ");
    });
    html = html.replace(/PAY-1042/g, a.ticket_id || "");
    html = html.replace(/Llama 3\.1 70B|AI Agent \([^)]*\)/g, "DAN Orkestratör");
    html = html.replace(/JIRA_TRANSITION_STATUS|STATUS_TRANSITION/g, "JIRA_" + (a.state || "").toUpperCase());
    el.innerHTML = html;
    // durum noktasi rengi
    const dot = el.querySelector("span.w-2");
    if (dot) dot.style.background = stateColor(a.state);
    // detay satiri: gecis bilgisi
    const detail = el.querySelector(".bg-surface-container-lowest");
    if (detail) {
      detail.innerHTML = '<div class="flex items-center justify-between"><span class="text-xs" style="color:#94a3b8">Durum:</span>'
        + '<span class="text-xs font-semibold" style="color:' + stateColor(a.state) + '">' + esc(a.state || "")
        + (a.transition_to ? " → " + esc(a.transition_to) : "") + "</span></div>"
        + '<div class="flex items-center justify-between"><span class="text-xs" style="color:#94a3b8">Repo:</span>'
        + '<span class="text-xs" style="color:#c7c4d7">' + esc(a.repo || "") + "</span></div>"
        + (a.skipped_reason ? '<div class="text-xs" style="color:#f59e0b">' + esc(a.skipped_reason) + "</div>" : "");
    }
    el.style.display = "";
    return el;
  }

  async function load() {
    const q = ((document.getElementById("ticket-search") || {}).value || "").trim();
    try { ROWS = await api.get("/api/audit?ticket=" + encodeURIComponent(q)); }
    catch (e) { ROWS = []; }
    const items = [...stream.querySelectorAll("article")];
    if (!items.length) return;
    const tpl = items[0];
    items.forEach((x) => x.remove());
    const frag = document.createDocumentFragment();
    ROWS.forEach((a) => frag.appendChild(articleFor(tpl, a)));
    stream.appendChild(frag);
    const empty = document.getElementById("audit-empty-state");
    if (empty) empty.style.display = ROWS.length ? "none" : "";
    rebuildFilters();
    if (window.applyFilter) window.applyFilter();
  }

  function rebuildFilters() {
    const actSel = document.getElementById("action-filter");
    if (actSel) {
      const states = [...new Set(ROWS.map((r) => r.state).filter(Boolean))];
      const cur = actSel.value;
      actSel.innerHTML = '<option value="ALL">Tümü</option>' + states.map((s) => '<option value="' + esc(s) + '">' + esc(s) + "</option>").join("");
      if ([...actSel.options].some((o) => o.value === cur)) actSel.value = cur;
    }
    const actorSel = document.getElementById("actor-filter");
    if (actorSel) {
      const actors = [...new Set(ROWS.map((r) => r.trigger || "api"))];
      const cur = actorSel.value;
      actorSel.innerHTML = '<option value="ALL">Tümü</option>' + actors.map((s) => '<option value="' + esc(s) + '">' + esc(s) + "</option>").join("");
      if ([...actorSel.options].some((o) => o.value === cur)) actorSel.value = cur;
    }
  }

  function download(name, text, type) {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  // filtre + export'u canliya bagla (sablon fonksiyonlarini sar)
  const search = document.getElementById("ticket-search");
  if (search) search.addEventListener("input", () => { clearTimeout(search._t); search._t = setTimeout(load, 400); });
  const reset = document.getElementById("reset-filter-btn");
  if (reset) reset.addEventListener("click", () => { setTimeout(load, 50); });
  const csvBtn = document.getElementById("export-csv-btn"), jsonBtn = document.getElementById("export-json-btn");
  if (csvBtn) csvBtn.addEventListener("click", () => {
    const head = "ticket,repo,run,state,transition,created_at\n";
    const body = ROWS.map((a) => [a.ticket_id, a.repo, a.run_id, a.state, a.transition_to || "", a.created_at || ""].map((x) => '"' + String(x == null ? "" : x).replace(/"/g, '""') + '"').join(",")).join("\n");
    download("denetim-izi.csv", head + body, "text/csv");
  });
  if (jsonBtn) jsonBtn.addEventListener("click", () => {
    download("denetim-izi.json", JSON.stringify(ROWS, null, 2), "application/json");
  });

  load();
})();
