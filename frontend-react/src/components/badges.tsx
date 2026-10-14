const MAP: Record<string, [string, string]> = {
  success: ["Başarılı", "#10b981"],
  partially_blocked: ["Kısmen Engellendi", "#f59e0b"],
  failed: ["Başarısız", "#ef4444"],
  queued: ["Kuyrukta", "#818cf8"],
  running: ["Çalışıyor", "#818cf8"],
  pending_approval: ["Onay Bekliyor", "#f59e0b"],
  rejected: ["Reddedildi", "#ef4444"],
  planned: ["Planlandı", "#818cf8"],
  applied: ["Uygulandı", "#10b981"],
  skipped: ["Atlandı", "#f59e0b"],
  mismatch: ["Eşleşmiyor", "#f59e0b"],
};

export function StatusBadge({ status }: { status?: string | null }) {
  const [label, color] = MAP[status || ""] || [status || "—", "#94a3b8"];
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ background: `color-mix(in srgb, ${color} 18%, transparent)`, color }}
    >
      {label}
    </span>
  );
}

export function Chip({ children, href, tone }: { children: React.ReactNode; href?: string; tone?: "jira" }) {
  const style =
    tone === "jira"
      ? {
          background: "rgba(0,82,204,.14)",
          border: "1px solid rgba(0,82,204,.55)",
          color: "#4c9aff",
        }
      : {
          background: "#0f172a",
          border: "1px solid #334155",
          color: "#94a3b8",
        };
  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="px-2 py-0.5 rounded text-xs font-mono hover:text-ink"
        style={style}
      >
        {children}
      </a>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded text-xs font-mono" style={style}>
      {children}
    </span>
  );
}

export function GithubMark() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

export function JiraMark() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M11.571 11.513H0a5.218 5.218 0 0 0 5.232 5.215h2.13v2.057A5.215 5.215 0 0 0 12.575 24V12.518a1.005 1.005 0 0 0-1.005-1.005zm5.723-5.756H5.736a5.215 5.215 0 0 0 5.215 5.214h2.129v2.058a5.218 5.218 0 0 0 5.215 5.214V6.758a1.001 1.001 0 0 0-1.001-1.001zM23.013 0H11.455a5.215 5.215 0 0 0 5.215 5.215h2.129v2.057A5.215 5.215 0 0 0 24 12.483V1.005A1.001 1.001 0 0 0 23.013 0Z" />
    </svg>
  );
}
