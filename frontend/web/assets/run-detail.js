/* Run detay: sablon rapor + commit kartlari + onay modal'i korunur, ici canli.
   ?id= ile acilir. Onay modal'i gercek approve/reject yapar. */
(function () {
  if (!window.DAN) return;
  const { api, esc } = window.DAN;
  const feedback = (m) => { if (window.showFeedback) window.showFeedback(m); };
  const id = new URLSearchParams(location.search).get("id");
  let RUN = null;

  async function load() {
    if (!id) return;
    try { RUN = await api.get("/api/runs/" + encodeURIComponent(id)); }
    catch (e) { feedback("Run bulunamadı."); return; }
    paintHeader();
    paintReport();
    paintCommits();
    paintModal();
  }

  function swapTexts(root, pairs) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((n) => {
      pairs.forEach(([from, to]) => {
        if (n.nodeValue && n.nodeValue.includes(from)) n.nodeValue = n.nodeValue.split(from).join(to);
      });
    });
  }

  function paintHeader() {
    swapTexts(document.body, [
      ["run-84f9a2", "run-" + RUN.run_id],
      ["org/payment-gateway", RUN.repo],
    ]);
    document.title = "#run-" + RUN.run_id + " - DevOps Agentic Network";
  }

  function paintReport() {
    const box = document.getElementById("report-content");
    if (!box) return;
    const txt = RUN.final_report || RUN.error || "Rapor yok.";
    const first = box.querySelector("p");
    if (first) {
      first.textContent = txt;
      // mock alt bloklari kaldir, tek gercek paragraf birak
      [...box.querySelectorAll("div")].forEach((d) => { if (!d.contains(first)) d.remove(); });
    } else {
      box.innerHTML = '<div class="rounded-lg p-3 text-xs whitespace-pre-wrap" style="color:#c7c4d7">' + esc(txt) + "</div>";
    }
    const st = document.querySelector("[data-run-status]");
    if (st) st.textContent = RUN.status;
  }

  function paintCommits() {
    const units = RUN.commit_units || [];
    // sablon kart kokleri: commit-N detay bloklarinin karti
    const details = ["commit-1", "commit-2", "commit-3"].map((x) => document.getElementById(x)).filter(Boolean);
    if (!details.length) return;
    const firstDetail = details[0];
    // kart kokunu bul (detay blogunu iceren kart)
    let tplCard = firstDetail.parentElement;
    const parent = tplCard.parentElement;
    const Drop = (window.toggleCommit ? "toggleCommit" : "");
    void Drop;
    // mevcut kartlari temizle (sablon ornekleri)
    [...parent.children].forEach((ch) => {
      if (ch.querySelector && ch.querySelector("[id^='commit-']")) ch.remove();
    });
    if (!units.length) {
      const d = document.createElement("div");
      d.className = "text-xs p-3"; d.style.color = "#94a3b8"; d.textContent = "Commit bulunamadı.";
      parent.appendChild(d);
      return;
    }
    units.forEach((u, i) => {
      const card = tplCard.cloneNode(true);
      const detId = "commit-live-" + i;
      card.innerHTML = card.innerHTML
        .replace(/commit-1/g, detId)
        .replace(/PAY-1042/g, esc((u.jira_ids || []).join(", ") || "—"))
        .replace(/services\/payment_webhook\.go:78/g, esc((u.short_sha || "") + " · " + (u.author || "")));
      // baslik + durum rozeti
      const title = card.querySelector(".font-semibold, b, h4");
      const badge = document.createElement("span");
      const ok = u.review_status !== "FAILED";
      badge.className = "px-2 py-0.5 rounded text-xs font-semibold";
      badge.style.cssText = ok ? "background:rgba(16,185,129,.15);color:#10b981" : "background:rgba(239,68,68,.15);color:#ef4444";
      badge.textContent = u.review_status || "?";
      if (title && title.parentElement) title.parentElement.appendChild(badge);
      // mesaj + yorum
      const msg = document.createElement("div");
      msg.className = "text-xs px-1";
      msg.style.color = "#f8fafc";
      msg.textContent = u.message || "";
      card.prepend(msg);
      if (u.review_comment) {
        const c = document.createElement("div");
        c.className = "text-xs rounded-md p-2";
        c.style.cssText = "background:#0f172a;color:#c7c4d7";
        c.textContent = u.review_comment;
        card.appendChild(c);
      }
      // toggle bagla
      card.querySelectorAll("[onclick*='toggleCommit']").forEach((b) => {
        b.removeAttribute("onclick");
        b.addEventListener("click", () => window.toggleCommit && window.toggleCommit(detId));
      });
      parent.appendChild(card);
    });
  }

  function paintModal() {
    const modal = document.getElementById("confirm-modal");
    if (modal) swapTexts(modal, [["run-84f9a2", "run-" + RUN.run_id], ["org/payment-gateway", RUN.repo]]);
  }

  window.executeDeployment = async function () {
    if (window.closeConfirmModal) window.closeConfirmModal();
    if (!RUN) return;
    if (RUN.status !== "pending_approval") { feedback("Bu run onay beklemiyor (" + RUN.status + ")."); return; }
    try {
      RUN = await api.post("/api/runs/" + encodeURIComponent(RUN.run_id) + "/approve", { approved: true, note: "" });
      feedback("Onaylandı, Jira yazıldı.");
      paintHeader(); paintReport(); paintCommits();
    } catch (e) { feedback("Onay başarısız: " + e.message); }
  };
  // iptal butonu -> gercek ret
  document.addEventListener("click", async (e) => {
    const b = e.target.closest && e.target.closest("[data-act='reject-run']");
    if (!b || !RUN) return;
    try {
      RUN = await api.post("/api/runs/" + encodeURIComponent(RUN.run_id) + "/approve", { approved: false, note: "" });
      if (window.closeConfirmModal) window.closeConfirmModal();
      feedback("Run reddedildi.");
      paintHeader(); paintReport(); paintCommits();
    } catch (err) { feedback("Ret başarısız: " + err.message); }
  });

  window.downloadExecutionReport = function () {
    if (!RUN) return;
    const blob = new Blob([JSON.stringify(RUN, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "run-" + RUN.run_id + ".json"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  };

  load();
})();
