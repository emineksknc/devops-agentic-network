import { NavLink, Outlet } from "react-router-dom";
import { Toaster } from "./Toaster";

const NAV = [
  { to: "/runs", label: "Çalıştırmalar" },
  { to: "/policies", label: "Politikalar" },
  { to: "/audit", label: "Denetim" },
  { to: "/agents", label: "Ajanlar" },
  { to: "/developers", label: "Geliştiriciler" },
  { to: "/settings", label: "Ayarlar" },
];

export function Layout() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Toaster />
      {/* desktop sidebar */}
      <aside
        className="hidden lg:flex fixed top-0 bottom-0 left-0 w-60 flex-col z-40"
        style={{ background: "#131b2e", borderRight: "1px solid #334155" }}
      >
        <div className="h-16 flex items-center px-5 font-bold">DevOps Agentic</div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `block px-4 py-2.5 rounded-lg text-sm ${isActive ? "font-semibold" : "text-muted hover:text-ink"}`
              }
              style={({ isActive }) => (isActive ? { background: "#2d3449", color: "#818cf8" } : undefined)}
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 text-xs font-mono text-faint">LOCAL</div>
      </aside>
      {/* topbar */}
      <header
        className="fixed top-0 right-0 left-0 lg:left-60 h-16 z-30 flex items-center justify-between px-4 lg:px-8"
        style={{ background: "rgba(15,23,42,.9)", backdropFilter: "blur(12px)" }}
      >
        <span className="lg:hidden font-bold">DevOps Agentic</span>
        <span className="hidden lg:inline text-sm text-muted">Otonom DevOps Orkestrasyonu</span>
        <span className="text-xs font-mono text-faint">v0.2.0</span>
      </header>
      <main className="pt-16 lg:pl-60 pb-24 lg:pb-10">
        <div className="max-w-[1400px] mx-auto px-4 lg:px-8 py-4 space-y-4">
          <Outlet />
        </div>
      </main>
      {/* mobile bottom nav */}
      <nav
        className="lg:hidden fixed bottom-0 w-full z-40 flex justify-around h-16"
        style={{ background: "rgba(15,23,42,.95)", borderTop: "1px solid #334155" }}
      >
        {NAV.slice(0, 4).map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) => `flex-1 text-center text-[11px] py-3 ${isActive ? "font-semibold" : "text-muted"}`}
            style={({ isActive }) => (isActive ? { color: "#818cf8" } : undefined)}
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
