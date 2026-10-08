"""Stitch mobil sablonlarini web duzenine uyarlar.
Girdi : stitch_devops_agentic_network_dashboard/*/[code.html]
Cikti : frontend/web/*.html + frontend/web/assets/*
Calistirma: .\\venv\\Scripts\\python.exe frontend/tools/build_web.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "stitch_devops_agentic_network_dashboard"
DST = ROOT / "frontend" / "web"

PAGES = {
    "al_t_rmalar_devops_agentic_network": "runs.html",
    "al_t_rma_detay_devops_agentic_network": "run-detail.html",
    "politikalar_devops_agentic_network": "policies.html",
    "denetim_i_zi_devops_agentic_network": "audit.html",
    "ayarlar_devops_agentic_network": "settings.html",
}

HREFS = {
    "calistirmalar": "runs.html",
    "calistirma-detayi": "run-detail.html",
    "politikalar": "policies.html",
    "denetim-izi": "audit.html",
    "ayarlar": "settings.html",
    "ajanlar": "agents.html",
    "gelistiriciler": "developers.html",
}

PAGE_SCRIPTS = {
    "runs": ["api.js", "runs.js"],
    "run-detail": ["api.js", "run-detail.js"],
    "policies": ["api.js", "policies.js"],
    "audit": ["api.js", "audit.js"],
    "settings": ["api.js", "settings.js"],
    "agents": ["api.js", "agents.js"],
    "developers": ["api.js", "developers.js"],
}

NAV_EXTRA = [
    ("ajanlar", "agents.html", "smart_toy", "Ajanlar"),
    ("gelistiriciler", "developers.html", "group", "Geliştiriciler"),
]

SIDEBAR_WIDTH = "240px"

WEB_CSS = """/* Web uyarlamasi: desktop duzen (Stitch mobil sablon uzerine katman) */
@media (min-width: 1024px) {
  /* cekmece her zaman acik sabit sidebar olur */
  #mobile-nav-drawer {
    transform: none !important;
    width: %SIDEBAR%;
    border-right: 1px solid #334155;
  }
  #mobile-nav-drawer #drawer-close-btn, #drawer-backdrop { display: none !important; }
  /* header + main sidebar kadar sagdan baslar */
  body > header.fixed { left: %SIDEBAR%; width: auto; right: 0; }
  body > main {
    padding-left: calc(%SIDEBAR% + 0px) !important;
  }
  body > main > div:first-child {
    max-width: 1400px; margin-left: auto; margin-right: auto;
    padding-left: 2rem; padding-right: 2rem;
  }
  /* koskoca kart listeleri genis ekranda iki sutun */
  #runs-list-container {
    display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }
  #runs-list-container > * { margin-top: 0 !important; }
}
  /* detay sayfasi: genis ekranda icerik + sag ozet sutunu */
  body[data-page="run-detail"] > main > div:first-child > section:first-of-type {
    max-width: 1100px;
  }
}
/* mobil cekmece acma tusu desktop'ta gizlenir */
@media (min-width: 1024px) {
  #drawer-toggle-btn { display: none !important; }
}
/* mobil alt bar desktop'ta gizlenir (class ile de kapatilir) */
""".replace("%SIDEBAR%", SIDEBAR_WIDTH)

WEB_JS = """// Web kabugu: aktif sayfa isaretleme + mock kalintilarini canli/nor hale getirme.
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
    "Ba\\u015f Sistem Mimar\\u0131": "Y\\u00f6netici",
    "Tech Lead \\u00b7 Online": "Admin \\u00b7 Local",
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
"""


def _inject_nav_links(html: str) -> str:
    """Cekmeceye Ajanlar + Gelistiriciler linkleri (ayarlar oncesi)."""
    import re

    m = re.search(r'<a[^>]*data-path="ayarlar"[^>]*>.*?</a>', html, re.DOTALL)
    if not m:
        return html
    anchor = m.group(0)
    extras = ""
    for path, href, icon, label in NAV_EXTRA:
        item = re.sub(r'data-path="ayarlar"', f'data-path="{path}"', anchor)
        item = re.sub(r'href="[^"]*"', f'href="{href}"', item, count=1)
        item = re.sub(r"<span[^>]*material-symbols[^>]*>.*?</span>", f'<span class="material-symbols-outlined">{icon}</span>', item, count=1)
        item = item.replace(">Ayarlar</span>", f">{label}</span>")
        # aktiflik class'larini temizle (web.js seciyor)
        item = item.replace("bg-surface-container-highest text-primary font-semibold", "text-on-surface-variant hover:text-on-surface hover:bg-surface-container")
        item = item.replace(' aria-current="page"', "")
        extras += item
    return html.replace(anchor, extras + anchor, 1)


def adapt(html: str, page: str) -> str:
    # 1) mobil alt navigasyon: sadece mobilde goster
    html = html.replace(
        '<nav class="fixed bottom-0 w-full',
        '<nav class="fixed bottom-0 w-full lg:hidden',
        1,
    )
    # 2) cekmece: desktop'ta her zaman gorunur (CSS zorlar), kapat tusunu isaretle
    html = html.replace(
        'id="mobile-nav-drawer"',
        'id="mobile-nav-drawer" data-web-sidebar',
        1,
    )
    html = html.replace(
        "aria-label=\"Men",
        "aria-label=\"Men",
        1,
    )
    # 3) sayfalar arasi gercek linkler
    for key, target in HREFS.items():
        html = html.replace('data-path="%s" href="#"' % key,
                            'data-path="%s" href="%s"' % (key, target))
    # 3b) cekmeceye yeni ekran linkleri
    html = _inject_nav_links(html)
    # 3c) sablonun sahte ortam etiketini notrle (canli karsiligi web.js'te)
    html = html.replace("PROD-EU-1", "LOCAL")
    # 4) body'ye sayfa kimligi + asset referanslari (</head> oncesi CSS, </body> oncesi JS)
    html = html.replace("<body", '<body data-page="%s"' % page, 1)
    html = html.replace(
        "</head>" if "</head>" in html else "</HEAD>",
        '<link rel="stylesheet" href="assets/web.css" />\n</head>',
        1,
    )
    if "</body>" in html:
        scripts = '<script src="assets/web.js"></script>\n'
        for js in PAGE_SCRIPTS.get(page, []):
            scripts += f'<script src="assets/{js}"></script>\n'
        html = html.replace("</body>", scripts + "</body>", 1)
    else:
        html += '\n<script src="assets/web.js"></script>\n'
    # 5) run-detail: web'de ustte kirinti (breadcrumb) + masaustu iki sutun
    if page == "run-detail":
        html = html.replace(
            '<div class="flex flex-col w-full px-gutter py-space-md space-y-space-md">',
            '<div class="flex flex-col w-full px-gutter py-space-md space-y-space-md">\n'
            '<a href="runs.html" data-web-crumb class="hidden lg:inline-flex items-center gap-2 '
            'font-code-sm text-code-sm text-on-surface-variant hover:text-on-surface w-fit">\n'
            '<span class="material-symbols-outlined text-[16px]">arrow_back</span>'
            "T\u00fcm \u00c7al\u0131\u015ft\u0131rmalar</a>",
            1,
        )
    return html


def main() -> None:
    assets = DST / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "web.css").write_text(WEB_CSS, encoding="utf-8")
    (assets / "web.js").write_text(WEB_JS, encoding="utf-8")

    built: dict[str, str] = {}
    for src_dir, out_name in PAGES.items():
        src_file = SRC / src_dir / "code.html"
        html = src_file.read_text(encoding="utf-8")
        page = out_name.replace(".html", "")
        built[out_name] = adapt(html, page)

    # run-detail kaynaginda cekmece yok: runs sayfasindaki
    # backdrop+sidebar blogunu aynen tasiyoruz (linkler uyarlanmis haliyle)
    m = re.search(
        r'<div class="fixed inset-0 z-50.*?</aside>',
        built["runs.html"],
        re.DOTALL,
    )
    if m:
        drawer = m.group(0)
        detail = built["run-detail.html"]
        menu_btn = (
            "<button aria-label=\"Men\u00fc\" "
            "class=\"lg:hidden w-11 h-11 flex items-center justify-center rounded-lg "
            "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors\" "
            "onclick=\"document.getElementById('mobile-nav-drawer').classList.toggle('-translate-x-full');"
            "document.getElementById('drawer-backdrop').classList.toggle('hidden');\">"
            '<span class="material-symbols-outlined">menu</span></button>'
        )
        detail = detail.replace(
            '<button aria-label="Geri D',
            menu_btn + '<button aria-label="Geri D',
            1,
        )
        detail = detail.replace("</header>", "</header>" + drawer, 1)
        built["run-detail.html"] = detail
        print("sidebar run-detail'e tasindi")

    for out_name, html in built.items():
        (DST / out_name).write_text(html, encoding="utf-8")
        print("yazildi:", DST / out_name)

    # Bizim ekranlar: runs iskeletinden uretilen kabuk + kendi baglama scripti
    _build_custom_page(built["runs.html"], "agents.html", "agents", "Ajanlar")
    _build_custom_page(built["runs.html"], "developers.html", "developers", "Geliştiriciler")


def _build_custom_page(shell: str, out_name: str, page: str, title: str) -> None:
    import re

    html = shell.replace('data-page="runs"', f'data-page="{page}"', 1)
    html = html.replace("<title>DevOps Agentic Network</title>",
                        f"<title>{title} - DevOps Agentic Network</title>", 1)
    new_main = (
        '<main class="flex flex-col relative w-full pt-[100px] pb-24 bg-surface min-h-screen">'
        '<div class="flex flex-col w-full px-gutter space-y-space-md" id="page-root">'
        '<p class="text-xs" style="color:#94a3b8">Yükleniyor…</p>'
        "</div></main>"
    )
    html = re.sub(r"<main.*?</main>", new_main, html, count=1, flags=re.DOTALL)
    scripts = '<script src="assets/web.js"></script>\n'
    for js in PAGE_SCRIPTS.get(page, []):
        scripts += f'<script src="assets/{js}"></script>\n'
    # eski sayfa scriptlerini sok, yenilerini tak
    html = re.sub(r'<script src="assets/(web|api|runs)\.js"></script>\n?', "", html)
    html = html.replace("</body>", scripts + "</body>", 1)
    (DST / out_name).write_text(html, encoding="utf-8")
    print("yazildi:", DST / out_name)

    index = DST / "index.html"
    index.write_text(
        '<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8" />'
        '<meta http-equiv="refresh" content="0; url=runs.html" />'
        "<title>DevOps Agentic Network</title></head>"
        '<body><a href="runs.html">Calistirmalar</a></body></html>',
        encoding="utf-8",
    )
    print("yazildi:", index)


if __name__ == "__main__":
    main()
