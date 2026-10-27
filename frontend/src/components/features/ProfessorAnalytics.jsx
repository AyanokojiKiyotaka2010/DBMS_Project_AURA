import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { StatTile } from "./Dashboard";

export function ProfessorAnalytics() {
  const [data, setData] = useState(null);
  useEffect(() => {
    axios.get(`${API}/analytics/professors`).then((r) => setData(r.data)).catch(() => toast.error("Failed to load"));
  }, []);

  if (!data) {
    return <div className="text-ink-3 italic text-sm animate-pulse" data-testid="analytics-loading">Loading analytics…</div>;
  }

  const maxAnswers = Math.max(1, ...data.professors.map((p) => p.answers));

  return (
    <div className="space-y-8 animate-fade-up" data-testid="analytics-view">
      <SectionHeading
        eyebrow="Insights"
        title="Professor response leaderboard"
        description="Who's answering fastest, and which topics remain chronically unanswered — updated every time you visit."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatTile label="Professor answers" value={data.totals.professor_answers} tone="brand" />
        <StatTile label="Open queries" value={data.totals.open_queries} tone="deep" />
        <StatTile label="Unanswered > 48h" value={data.totals.unanswered_48h} tone="gold" />
      </div>

      <TactileCard>
        <SectionHeading eyebrow="Leaderboard" title="By total answers" />
        <div className="mt-6 space-y-4">
          {data.professors.length === 0 && (
            <div className="text-ink-3 italic text-sm">No professor answers yet — a fresh dataset awaits.</div>
          )}
          {data.professors.map((p, i) => (
            <div key={p.name} className="flex items-center gap-4" data-testid={`prof-row-${i}`}>
              <div className="w-8 h-8 shrink-0 rounded-full bg-brand/10 text-brand grid place-items-center font-serif font-bold">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0 ml-1">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-serif text-lg text-ink truncate">{p.name}</div>
                  <div className="text-xs text-ink-3 font-mono shrink-0">
                    {p.answers} answers · avg {p.avg_response_hours}h
                  </div>
                </div>
                <div className="mt-1.5 h-2 rounded-full bg-paper-sidebar overflow-hidden">
                  <div
                    className="h-full bg-brand transition-all"
                    style={{ width: `${(p.answers / maxAnswers) * 100}%` }}
                  />
                </div>
                {p.topics.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {p.topics.slice(0, 5).map((t) => (
                      <span key={t} className="text-[10px] font-mono text-ink-3 border border-edge-light rounded-full px-2 py-0.5">
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </TactileCard>

      <TactileCard>
        <SectionHeading
          eyebrow="Attention needed"
          title="Chronically unanswered topics"
          description="Open queries older than 48h with no answers yet, grouped by department & topic."
        />
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.unanswered_topics.length === 0 && (
            <div className="text-ink-3 italic text-sm col-span-full">All topics have received attention — excellent.</div>
          )}
          {data.unanswered_topics.map((t) => (
            <div
              key={t.topic}
              data-testid={`unanswered-${t.topic}`}
              className="flex items-center justify-between gap-3 p-3 rounded-xl border border-edge-light bg-paper-sidebar"
            >
              <div className="font-medium text-ink text-sm truncate">{t.topic}</div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-brand/10 text-brand font-semibold">
                {t.count} pending
              </span>
            </div>
          ))}
        </div>
      </TactileCard>
    </div>
  );
}
