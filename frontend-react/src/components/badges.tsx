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

export function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-mono"
      style={{ background: "#0f172a", border: "1px solid #334155", color: "#94a3b8" }}
    >
      {children}
    </span>
  );
}
