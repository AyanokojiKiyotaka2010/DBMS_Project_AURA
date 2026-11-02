import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, animate, motion, useInView, useReducedMotion } from "framer-motion";

/* Small, calm motion kit. Everything degrades to "no animation" when the visitor prefers reduced motion. */
const EASE = [0.22, 1, 0.36, 1];

/** Fades/slides a screen in when `k` changes (the active section). */
export function PageTransition({ k, children }) {
  const reduce = useReducedMotion();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={k}
        initial={reduce ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reduce ? { opacity: 0 } : { opacity: 0, y: -6 }}
        transition={{ duration: 0.28, ease: EASE }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/** Children appear one after another. Wrap items in <Item>. */
export function Stagger({ children, className = "", gap = 0.07, delay = 0 }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap, delayChildren: delay } } }}
    >
      {children}
    </motion.div>
  );
}
export function Item({ children, className = "", ...rest }) {
  return (
    <motion.div className={className} variants={{ hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } } }} {...rest}>
      {children}
    </motion.div>
  );
}

/** Reveals when scrolled into view (long lists, cards below the fold). */
export function Reveal({ children, className = "", delay = 0 }) {
  const ref = useRef(null);
  const seen = useInView(ref, { once: true, margin: "0px 0px -40px 0px" });
  const reduce = useReducedMotion();
  return (
    <motion.div ref={ref} className={className} initial={reduce ? false : { opacity: 0, y: 16 }}
      animate={seen ? { opacity: 1, y: 0 } : undefined} transition={{ duration: 0.5, ease: EASE, delay }}>
      {children}
    </motion.div>
  );
}

/** A gentle lift on hover for clickable cards. */
export function Lift({ children, className = "", y = -3, ...rest }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} whileHover={reduce ? undefined : { y, transition: { duration: 0.2 } }} whileTap={reduce ? undefined : { scale: 0.995 }} {...rest}>
      {children}
    </motion.div>
  );
}

/** Number that counts up to its value (non-numbers are shown as-is). */
export function CountUp({ value, duration = 0.9, className = "" }) {
  const reduce = useReducedMotion();
  const numeric = typeof value === "number" && Number.isFinite(value);
  const [shown, setShown] = useState(numeric && !reduce ? 0 : value);
  useEffect(() => {
    if (!numeric || reduce) { setShown(value); return undefined; }
    const c = animate(0, value, { duration, ease: EASE, onUpdate: (v) => setShown(Math.round(v)) });
    return () => c.stop();
  }, [value, numeric, reduce, duration]);
  return <span className={className}>{shown}</span>;
}

/** Placeholder block while data loads. */
export function Skeleton({ className = "" }) {
  return <div className={`rounded-lg bg-gradient-to-r from-edge-light/40 via-edge-light/80 to-edge-light/40 bg-[length:200%_100%] animate-[shimmer_1.6s_ease-in-out_infinite] ${className}`} />;
}

/** Thin horizontal meter whose fill animates in. tone: auto | brand | deep | gold */
export function BarMeter({ value, max = 100, tone = "auto", className = "", label }) {
  const reduce = useReducedMotion();
  const pct = Math.max(0, Math.min(100, (Number(value) / max) * 100));
  const color = tone === "auto" ? (pct >= 75 ? "#2A4747" : pct >= 50 ? "#E8B255" : "#D95D39")
    : tone === "gold" ? "#E8B255" : tone === "brand" ? "#D95D39" : "#2A4747";
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="h-1.5 w-20 rounded-full bg-edge-light overflow-hidden">
        <motion.div className="h-full rounded-full" style={{ background: color }} initial={reduce ? false : { width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: EASE }} />
      </div>
      {label !== undefined && <span className="tabular-nums text-xs text-ink-2">{label}</span>}
    </div>
  );
}

/** Circular countdown (time left of a total span). */
export function TimeRing({ createdAt, expiresAt, size = 34 }) {
  const total = new Date(expiresAt) - new Date(createdAt);
  const left = Math.max(0, new Date(expiresAt) - new Date());
  const frac = total > 0 ? Math.max(0, Math.min(1, left / total)) : 0;
  const r = (size - 6) / 2, c = 2 * Math.PI * r;
  const color = left < 3600000 ? "#D95D39" : "#2A4747";
  return (
    <svg width={size} height={size} className="-rotate-90 shrink-0" aria-hidden>
      <circle cx={size / 2} cy={size / 2} r={r} stroke="#EAE5D9" strokeWidth="4" fill="none" />
      <motion.circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="4" strokeLinecap="round" fill="none"
        strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - frac) }} transition={{ duration: 0.9, ease: EASE }} />
    </svg>
  );
}
