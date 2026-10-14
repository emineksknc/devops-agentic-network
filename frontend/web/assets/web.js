// Web kabugu: aktif sayfa isaretleme + mock kalintilarini canli/nor hale getirme.
(function () {
  var page = document.body.dataset.page || "";
  var map = {
    runs: ["calistirmalar"],
    "run-detail": ["calistirma-detayi"],
    policies: ["politikalar"],
    audit: ["denetim-izi"],
    settings: ["ayarlar"],
    agents: ["ajanlar"],
    developers: ["gelistiriciler"],
  };
  var active = map[page] || [];
  document.querySelectorAll("aside nav a, body > nav a").forEach(function (a) {
    var p = a.getAttribute("data-path") || "";
    if (active.indexOf(p) !== -1) {
      a.setAttribute("aria-current", "page");
    } else {
      a.removeAttribute("aria-current");
    }
  });

  // Mock kimlik/ortam yazilarini notrle (sablon kalintisi, backend'de auth yok)
  var swaps = {
    "Ba\u015f Sistem Mimar\u0131": "Y\u00f6netici",
    "Tech Lead \u00b7 Online": "Admin \u00b7 Local",
    "PROD-EU-1": "LOCAL",
  };
  try {
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (n) {
      Object.keys(swaps).forEach(function (k) {
        if (n.nodeValue && n.nodeValue.indexOf(k) !== -1) n.nodeValue = n.nodeValue.split(k).join(swaps[k]);
      });
    });
  } catch (e) {}

  // Canli durum: ajan sayisi + API gecikmesi (olmazsa banner gizlenir)
  fetch("/api/agents").then(function (r) { return r.json(); }).then(function (agents) {
    var on = agents.filter(function (a) { return a.enabled; }).length;
    document.body.querySelectorAll("span, div").forEach(function (el) {
      if (el.children.length === 0 && el.textContent.indexOf("Ajan modeli aktif") !== -1) {
        el.textContent = on + " ajan aktif (" + agents.map(function (a) { return a.name.replace("_agent", ""); }).join(", ") + ")";
      }
    });
    return fetch("/api/health");
  }).then(function (r) { return r.json(); }).then(function (h) {
    document.body.querySelectorAll("span").forEach(function (el) {
      if (el.children.length === 0 && el.textContent.indexOf("Orkestrasyon Motoru") !== -1) {
        el.textContent = "Orkestrasyon Motoru: v" + (h.version || "?");
      }
    });
  }).catch(function () {});
})();
