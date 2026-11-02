import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MagnifyingGlass, ArrowElbowDownLeft } from "@phosphor-icons/react";

/** Ctrl/⌘ + K: jump to any screen without hunting through the sidebar. */
export default function CommandPalette({ open, onClose, items, onPick }) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const input = useRef(null);
  const list = useRef(null);

  const shown = useMemo(() => {
    const t = q.trim().toLowerCase();
    return items.filter((i) => !t || `${i.label} ${i.group || ""}`.toLowerCase().includes(t));
  }, [items, q]);

  useEffect(() => { if (open) { setQ(""); setIdx(0); setTimeout(() => input.current?.focus(), 30); } }, [open]);
  useEffect(() => { setIdx(0); }, [q]);
  useEffect(() => { list.current?.querySelector(`[data-idx="${idx}"]`)?.scrollIntoView({ block: "nearest" }); }, [idx]);

  const onKey = (e) => {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, shown.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter" && shown[idx]) { onPick(shown[idx].id); onClose(); }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50 flex items-start justify-center pt-[14vh] px-4 bg-ink/30 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={onClose} data-testid="command-palette">
          <motion.div onMouseDown={(e) => e.stopPropagation()} onKeyDown={onKey}
            className="w-full max-w-lg rounded-2xl bg-paper-card border border-edge-light shadow-2xl overflow-hidden"
            initial={{ opacity: 0, y: -12, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
            <div className="flex items-center gap-3 px-4 py-3 border-b border-edge-light">
              <MagnifyingGlass size={18} className="text-ink-3" />
              <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Go to…  (clubs, reports, queries)"
                className="flex-1 bg-transparent outline-none text-sm text-ink placeholder:text-ink-3" data-testid="palette-input" />
              <kbd className="text-[10px] text-ink-3 border border-edge-light rounded px-1.5 py-0.5">esc</kbd>
            </div>
            <div ref={list} className="max-h-[50vh] overflow-y-auto p-2">
              {shown.length === 0 && <div className="text-center text-sm text-ink-3 py-8">Nothing matches “{q}”.</div>}
              {shown.map((it, i) => {
                const Icon = it.icon;
                return (
                  <button key={it.id} data-idx={i} data-testid={`palette-item-${it.id}`} onMouseMove={() => setIdx(i)}
                    onClick={() => { onPick(it.id); onClose(); }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition-colors ${i === idx ? "bg-brand/10 text-ink" : "text-ink-2"}`}>
                    <Icon size={17} weight={i === idx ? "duotone" : "regular"} className={i === idx ? "text-brand" : ""} />
                    <span className="flex-1">{it.label}</span>
                    {it.group && <span className="text-[10px] uppercase tracking-widest text-ink-3">{it.group}</span>}
                    {i === idx && <ArrowElbowDownLeft size={14} className="text-brand" />}
                  </button>
                );
              })}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
