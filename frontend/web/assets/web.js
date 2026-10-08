// Web kabugu: aktif sayfa isaretleme + mobil cekmece davranisi korunur.
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
})();
