/* Politikalar: sablon kart/modal tasarimi korunur, ici canli API.
   Kartlar sablon karttan klonlanir; modal select'leri canli dolar. */
(function () {
  if (!window.DAN) return;
  const { api, esc } = window.DAN;
  const showToast = (m) => { if (window.showToast) window.showToast(m); };
  const setSwitch = window.setSwitchState || ((btn, s) => btn && btn.setAttribute("aria-checked", s ? "true" : "false"));

  let CONNS = [];
  const STATUSES = ["To Do", "In Progress", "In Review", "Done", "Blocked"];

  function editButtons() {
    let found = [...document.querySelectorAll("button[onclick*='openPolicyModal']")];
    if (!found.length) {
      found = [...document.querySelectorAll("button")].filter((b) =>
        (b.getAttribute("onclick") || "").includes("openPolicyModal"));
    }
    return found;
  }
  function cardRoot(btn) {
    let el = btn.parentElement, depth = 0;
    while (el && depth < 10) {
      try {
        if (el.querySelector && el.querySelector("button[onclick*='testPolicyRule']")) return el;
      } catch (e) {}
      el = el.parentElement; depth++;
    }
    el = btn.parentElement; depth = 0;
    while (el && depth < 10) {
      if (el.className && typeof el.className === "string" && el.className.includes("rounded-xl")) return el;
      el = el.parentElement; depth++;
    }
    return btn.parentElement;
  }
  function parseArgs(onclick) {
    const m = onclick.match(/openPolicyModal\((.*)\)\s*;?\s*$/);
    if (!m) return null;
    try { return JSON.parse("[" + m[1].replace(/'/g, '"') + "]"); } catch (e) { return null; }
  }

  async function load() {
    let pols = [];
    try {
      const [p, c] = await Promise.all([api.get("/api/policies"), api.get("/api/connections")]);
      pols = p; CONNS = c;
    } catch (e) { showToast("Politikalar yüklenemedi: " + e.message); return; }

    const btns = editButtons();
    if (!btns.length) return;
    const templateCard = cardRoot(btns[0]);
    const parent = templateCard.parentElement;
    const mocks = btns.map((b) => ({ btn: b, card: cardRoot(b), args: parseArgs(b.getAttribute("onclick")) }));
    // sablon kartlari kaldir, canlilari klonla
    mocks.forEach((x) => x.card.remove());
    if (!pols.length) {
      const empty = templateCard.cloneNode(true);
      empty.innerHTML = '<div class="p-6 text-center text-sm" style="color:#94a3b8">Henüz politika yok. Düzenle ile ilkini oluştur.</div>';
      parent.appendChild(empty);
    }
    pols.forEach((p) => parent.appendChild(buildCard(templateCard, p)));
    fillModalSelects();
  }

  function buildCard(tpl, p) {
    const card = tpl.cloneNode(true);
    let html = card.innerHTML;
    // repo adi: karttaki ilk repo gorunumu degistir
    const repoSpots = [...card.querySelectorAll("*")].filter((el) =>
      el.children.length === 0 && /org\//.test(el.textContent || ""));
    repoSpots.forEach((el) => { el.textContent = p.repo; });
    // durum gecisleri
    const passSpots = [...card.querySelectorAll("*")].filter((el) =>
      el.children.length === 0 && /Ready for Staging|In Review|In Progress/.test(el.textContent || ""));
    passSpots.forEach((el) => { el.textContent = p.on_pass_transition; });
    const failSpots = [...card.querySelectorAll("*")].filter((el) =>
      el.children.length === 0 && /Blocked/.test(el.textContent || ""));
    failSpots.forEach((el) => { el.textContent = p.on_fail_transition; });
    // toggle'lar: sirayla autowrite/approval/dryrun (sablon duzeni)
    const toggles = [...card.querySelectorAll("button[onclick*='toggleSwitch']")];
    const vals = [p.auto_write_pass || p.auto_write_fail, p.require_approval, p.dry_run_default];
    toggles.slice(0, 3).forEach((t, i) => { setSwitch(t, !!vals[i]); t.removeAttribute("onclick"); t.onclick = () => { if (window.toggleSwitch) window.toggleSwitch(t); }; });
    // butonlari gercekle
    card.querySelectorAll("button").forEach((b) => {
      const oc = b.getAttribute("onclick") || "";
      if (oc.includes("testPolicyRule")) {
        b.removeAttribute("onclick");
        b.onclick = async () => {
          try {
            const r = await api.post("/api/runs", { repo: p.repo, dry_run: true, count: 3 });
            showToast("Test runu başlatıldı: #run-" + r.run_id);
          } catch (e) { showToast("Test başlatılamadı: " + e.message); }
        };
      } else if (oc.includes("openPolicyModal")) {
        b.removeAttribute("onclick");
        b.onclick = () => window.openPolicyModal(p.repo, p.jira_project, p.on_pass_transition, p.on_fail_transition, !!(p.auto_write_pass || p.auto_write_fail), !!p.require_approval, !!p.dry_run_default);
      }
    });
    card.dataset.policy = p.repo;
    return card;
  }

  function fillModalSelects() {
    const sj = document.getElementById("select-jira");
    if (sj) {
      const projects = [...new Set(CONNS.filter((c) => c.kind === "jira").flatMap((c) => [c.project_key]).filter(Boolean))];
      sj.innerHTML = projects.map((x) => '<option value="' + esc(x) + '">' + esc(x) + "</option>").join("")
        || '<option value="">—</option>';
    }
    ["select-pass", "select-fail"].forEach((id) => {
      const s = document.getElementById(id);
      if (s) s.innerHTML = STATUSES.map((x) => '<option value="' + esc(x) + '">' + esc(x) + "</option>").join("");
    });
    // baglanti secimleri (tasarim dilinde ek satirlar)
    const form = document.getElementById("policy-form");
    if (form && !document.getElementById("select-gh-conn")) {
      const wrap = document.createElement("div");
      wrap.innerHTML = '<label class="text-xs" style="color:#94a3b8">GitHub bağlantısı</label>'
        + '<select id="select-gh-conn" class="w-full mt-1 mb-2 px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc"></select>'
        + '<label class="text-xs" style="color:#94a3b8">Jira bağlantısı</label>'
        + '<select id="select-jira-conn" class="w-full mt-1 px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc"></select>';
      const anchor = document.getElementById("select-fail");
      if (anchor && anchor.parentElement) anchor.parentElement.after(wrap);
      else form.prepend(wrap);
    }
    const gh = document.getElementById("select-gh-conn"), ji = document.getElementById("select-jira-conn");
    if (gh) gh.innerHTML = '<option value="">Varsayılan</option>' + CONNS.filter((c) => c.kind === "github").map((c) => '<option value="' + esc(c.id) + '">' + esc(c.name) + "</option>").join("");
    if (ji) ji.innerHTML = '<option value="">Varsayılan</option>' + CONNS.filter((c) => c.kind === "jira").map((c) => '<option value="' + esc(c.id) + '">' + esc(c.name) + "</option>").join("");
  }

  function switchVal(id) {
    const b = document.getElementById(id);
    return b ? b.getAttribute("aria-checked") === "true" : false;
  }

  // global'leri gercekle bagla (sablon bunlari cagirir)
  window.openPolicyModal = function (repo, jira, pass, fail, autoWrite, reqApproval, dryRun) {
    const orig = document.getElementById("policy-modal");
    if (!orig) return;
    document.getElementById("modal-title").textContent = "Politika Düzenle (" + repo + ")";
    document.getElementById("input-repo").value = repo || "";
    const sj = document.getElementById("select-jira"); if (sj && jira) sj.value = jira;
    const sp = document.getElementById("select-pass"); if (sp && pass) sp.value = pass;
    const sf = document.getElementById("select-fail"); if (sf && fail) sf.value = fail;
    setSwitch(document.getElementById("modal-toggle-autowrite"), !!autoWrite);
    setSwitch(document.getElementById("modal-toggle-approval"), !!reqApproval);
    setSwitch(document.getElementById("modal-toggle-dryrun"), !!dryRun);
    // mevcut politika varsa baglantilari sec
    api.get("/api/policies/" + encodeURIComponent(repo)).then((p) => {
      const gh = document.getElementById("select-gh-conn"); if (gh) gh.value = p.github_conn_id || "";
      const ji = document.getElementById("select-jira-conn"); if (ji) ji.value = p.jira_conn_id || "";
    }).catch(() => {});
    orig.classList.remove("hidden");
  };
  window.savePolicyChanges = async function (e) {
    if (e) e.preventDefault();
    const auto = switchVal("modal-toggle-autowrite");
    const body = {
      repo: document.getElementById("input-repo").value,
      jira_project: document.getElementById("select-jira").value,
      on_pass_transition: document.getElementById("select-pass").value,
      on_fail_transition: document.getElementById("select-fail").value,
      auto_write_pass: auto, auto_write_fail: auto,
      require_approval: switchVal("modal-toggle-approval"),
      dry_run_default: switchVal("modal-toggle-dryrun"),
      github_conn_id: (document.getElementById("select-gh-conn") || {}).value || "",
      jira_conn_id: (document.getElementById("select-jira-conn") || {}).value || "",
    };
    try {
      await api.post("/api/policies", body);
      if (window.closePolicyModal) window.closePolicyModal();
      showToast(body.repo + " politikası kaydedildi.");
      load();
    } catch (err) { showToast("Kaydedilemedi: " + err.message); }
  };
  window.testPolicyRule = async function (repo) {
    try {
      const r = await api.post("/api/runs", { repo, dry_run: true, count: 3 });
      showToast("Test runu başlatıldı: #run-" + r.run_id);
    } catch (e) { showToast("Test başlatılamadı: " + e.message); }
  };

  load();
})();
