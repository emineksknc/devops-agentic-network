import { useEffect, useState } from "react";

let push: ((msg: string, ok?: boolean) => void) | null = null;

export function toast(msg: string, ok = true) {
  push?.(msg, ok);
}

export function Toaster() {
  const [items, setItems] = useState<{ id: number; msg: string; ok: boolean }[]>([]);
  useEffect(() => {
    push = (msg, ok = true) => {
      const id = Date.now() + Math.random();
      setItems((prev) => [...prev, { id, msg, ok }]);
      setTimeout(() => setItems((prev) => prev.filter((x) => x.id !== id)), 4000);
    };
    return () => {
      push = null;
    };
  }, []);
  return (
    <div className="fixed top-4 right-4 z-[70] space-y-2 max-w-sm">
      {items.map((t) => (
        <div
          key={t.id}
          className="px-4 py-2 rounded-lg text-sm shadow-xl"
          style={{ background: t.ok ? "#00a572" : "#93000a", color: "#fff" }}
        >
          {t.msg}
        </div>
      ))}
    </div>
  );
}
