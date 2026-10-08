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
}

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

WEB_JS = """// Web kabugu: aktif sayfa isaretleme + mobil cekmece davranisi korunur.
(function () {
  var page = document.body.dataset.page || "";
  var map = {
    runs: ["calistirmalar"],
    "run-detail": ["calistirma-detayi"],
    policies: ["politikalar"],
    audit: ["denetim-izi"],
    settings: ["ayarlar"],
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
"""


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
    # 4) body'ye sayfa kimligi + asset referanslari (</head> oncesi CSS, </body> oncesi JS)
    html = html.replace("<body", '<body data-page="%s"' % page, 1)
    html = html.replace(
        "</head>" if "</head>" in html else "</HEAD>",
        '<link rel="stylesheet" href="assets/web.css" />\n</head>',
        1,
    )
    if "</body>" in html:
        html = html.replace("</body>", '<script src="assets/web.js"></script>\n</body>', 1)
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
