import React, { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading, EncryptedIDChip } from "../CampusUI";
import { Megaphone, ArrowUpRight } from "@phosphor-icons/react";

export function Dashboard({ user, setActive }) {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    axios.get(`${API}/stats/overview`).then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const HERO =
    "https://images.unsplash.com/photo-1760594386931-12fa82b68e59?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDR8MHwxfHNlYXJjaHw0fHx1bml2ZXJzaXR5JTIwY2x1YiUyMG1lZXRpbmclMjBldmVudCUyMHBvc3RlciUyMHN0eWxlfGVufDB8fHx8MTc4NjA1MjM1Nnww&ixlib=rb-4.1.0&q=85";

  return (
    <div data-testid="dashboard-view" className="space-y-10 animate-fade-up">
      <div className="relative overflow-hidden rounded-3xl tactile-card !p-0">
        <div className="grid md:grid-cols-2">
          <div className="p-8 md:p-10 relative">
            <div className="text-[11px] uppercase tracking-[0.22em] text-brand font-semibold mb-3">
              {user.department} · {user.year || "Campus"}
            </div>
            <h1 className="font-serif text-4xl md:text-5xl font-semibold text-ink tracking-tight leading-[1.02]">
              Good to see you, <span className="italic">{user.name?.split(" ")[0]}</span>.
            </h1>
            <p className="text-sm text-ink-2 mt-4 leading-relaxed max-w-md">
              Your announcements, doubts, clubs and admin threads — folded into a single warm paper feed.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <button
                data-testid="hero-cta-ask"
                onClick={() => setActive("queries")}
                className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-paper text-sm font-semibold shadow-clay transition-all active:scale-[0.98] flex items-center gap-2"
              >
                Ask anonymously <ArrowUpRight size={14} />
              </button>
              <button
                data-testid="hero-cta-clubs"
                onClick={() => setActive("clubs")}
                className="px-5 py-2.5 rounded-xl bg-paper-card border border-edge-light text-ink text-sm font-semibold hover:border-brand/50 transition-all"
              >
                Browse clubs
              </button>
            </div>
          </div>
          <div className="relative min-h-[220px] md:min-h-full">
            <img src={HERO} alt="Campus club poster" className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-r from-paper-card/70 to-transparent md:from-paper-card/40" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Announcements" value={stats?.announcements ?? "—"} tone="brand" />
        <StatTile label="Open queries" value={stats?.open_queries ?? "—"} tone="deep" />
        <StatTile label="Escalated to alumni" value={stats?.escalated_alumni ?? "—"} tone="gold" />
        <StatTile label="Active clubs" value={stats?.clubs ?? "—"} tone="deep" />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <TactileCard>
          <SectionHeading eyebrow="Today" title="What CRs pinned" />
          <div className="mt-5 space-y-3 text-sm">
            {(stats?.recent_announcements || []).slice(0, 3).map((a) => (
              <div key={a.id} className="flex items-start gap-3 py-2 border-b border-edge-light last:border-none">
                <Megaphone size={16} className="text-brand mt-1" weight="fill" />
                <div>
                  <div className="font-semibold text-ink">{a.title}</div>
                  <div className="text-xs text-ink-3">{a.author} · {a.time}</div>
                </div>
              </div>
            ))}
            {(!stats || (stats.recent_announcements || []).length === 0) && (
              <div className="text-ink-3 text-sm italic">No pinned announcements yet.</div>
            )}
          </div>
        </TactileCard>

        <TactileCard>
          <SectionHeading eyebrow="Doubts" title="Latest anonymous questions" />
          <div className="mt-5 space-y-3 text-sm">
            {(stats?.recent_queries || []).slice(0, 3).map((q) => (
              <div key={q.id} className="py-2 border-b border-edge-light last:border-none">
                <div className="flex items-center gap-2 mb-1">
                  <EncryptedIDChip id={q.enc_id} />
                  <span className="text-[10px] text-ink-3 font-mono">{q.time}</span>
                </div>
                <div className="text-ink">{q.query}</div>
              </div>
            ))}
            {(!stats || (stats.recent_queries || []).length === 0) && (
              <div className="text-ink-3 text-sm italic">No queries yet — you can be first.</div>
            )}
          </div>
        </TactileCard>
      </div>
    </div>
  );
}

export function StatTile({ label, value, tone }) {
  const toneClass = { brand: "text-brand", deep: "text-brand-deep", gold: "text-brand-gold" }[tone];
  return (
    <div className="tactile-card !p-5">
      <div className="text-[10px] uppercase tracking-[0.22em] text-ink-3 font-semibold">{label}</div>
      <div className={`font-serif text-4xl font-semibold mt-1 ${toneClass}`}>{value}</div>
    </div>
  );
}
