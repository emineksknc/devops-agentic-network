import type { ReactNode } from "react";

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,.6)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="card w-full max-w-lg p-5 max-h-[90vh] overflow-auto">
        <h3 className="text-base font-semibold mb-3">{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block mb-3">
      <span className="block text-xs mb-1 text-muted">{label}</span>
      {children}
    </label>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="card p-6 text-center text-sm text-muted">{text}</div>;
}
