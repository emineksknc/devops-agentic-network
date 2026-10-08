/* DAN ortak API katmani: tum sayfalar bunu kullanir. */
(function () {
  async function req(method, path, body) {
    const r = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((data && data.detail) || ("HTTP " + r.status));
    return data;
  }
  const api = {
    get: (p) => req("GET", p),
    post: (p, b) => req("POST", p, b),
    put: (p, b) => req("PUT", p, b),
    del: (p) => req("DELETE", p),
  };

  function toast(msg) {
    let t = document.getElementById("toast-notify");
    let txt = document.getElementById("toast-text");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast-notify";
      t.className = "fixed top-20 right-4 z-50 px-4 py-2 rounded-lg shadow-xl text-sm";
      t.style.background = "#00a572"; t.style.color = "#00311f";
      txt = document.createElement("span"); txt.id = "toast-text";
      t.appendChild(txt); document.body.appendChild(t);
    }
    txt.innerText = msg;
    t.style.opacity = "1";
    clearTimeout(t._h);
    t._h = setTimeout(() => { t.style.opacity = "0"; }, 2800);
  }

  const STATUS_TR = {
    success: ["Başarılı", "#10b981"], partially_blocked: ["Kısmen Engellendi", "#f59e0b"],
    failed: ["Başarısız", "#ef4444"], queued: ["Kuyrukta", "#818cf8"],
    running: ["Çalışıyor", "#818cf8"], pending_approval: ["Onay Bekliyor", "#f59e0b"],
    rejected: ["Reddedildi", "#ef4444"],
  };
  function statusBadge(status) {
    const [label, color] = STATUS_TR[status] || [status, "#94a3b8"];
    return '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold" '
      + 'style="background:color-mix(in srgb,' + color + ' 18%, transparent);color:' + color + '">'
      + label + "</span>";
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function timeAgo(iso) {
    try {
      const d = new Date(iso), diff = (Date.now() - d.getTime()) / 1000;
      if (diff < 3600) return Math.max(1, Math.floor(diff / 60)) + " dk önce";
      if (diff < 86400) return Math.floor(diff / 3600) + " saat önce";
      return d.toLocaleString("tr-TR");
    } catch (e) { return iso || ""; }
  }

  /* Basit modal: openModal(html) -> element doner, closeModal() kapatir */
  function openModal(html) {
    closeModal();
    const back = document.createElement("div");
    back.id = "dan-modal";
    back.style.cssText = "position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:1rem";
    back.innerHTML = '<div class="w-full max-w-lg rounded-xl p-5" style="background:#1e293b;border:1px solid #334155">'
      + html + "</div>";
    back.addEventListener("click", (e) => { if (e.target === back) closeModal(); });
    document.body.appendChild(back);
    return back;
  }
  function closeModal() { const m = document.getElementById("dan-modal"); if (m) m.remove(); }
  function field(label, inner) {
    return '<label class="block text-xs mb-1" style="color:#94a3b8">' + label + "</label>" + inner
      + '<div class="mb-3"></div>';
  }
  function input(name, value, placeholder) {
    return '<input name="' + name + '" value="' + esc(value || "") + '" placeholder="' + esc(placeholder || "")
      + '" class="w-full px-3 py-2 rounded-md text-sm" style="background:#0f172a;border:1px solid #334155;color:#f8fafc" />';
  }
  function formValues(modal) {
    const o = {};
    modal.querySelectorAll("input[name],select[name],textarea[name]").forEach((el) => {
      o[el.name] = el.type === "checkbox" ? el.checked : el.value;
    });
    return o;
  }
  function primaryBtn(label) {
    return '<button data-act="save" class="px-4 py-2 rounded-md text-sm font-semibold" '
      + 'style="background:#6366f1;color:#fff">' + label + "</button>";
  }

  window.DAN = { api, toast, statusBadge, esc, timeAgo, openModal, closeModal, field, input, formValues, primaryBtn };
})();
