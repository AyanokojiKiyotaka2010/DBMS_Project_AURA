import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading, EncryptedIDChip } from "../CampusUI";
import { StatTile } from "./Dashboard";
import {
  Printer,
  Megaphone,
  Question,
  WarningCircle,
  CalendarBlank,
  ChartLineDown,
  Copy,
  Sparkle,
} from "@phosphor-icons/react";

export function WeeklyDigest({ user }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${API}/digest/weekly`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load digest"));
  }, []);

  const buildTextDigest = () => {
    if (!data) return "";
    const l = [];
    l.push(`AURA — Weekly Digest for ${data.department}`);
    l.push(`Generated: ${new Date(data.generated_at).toLocaleString()}`);
    l.push(`CR on record: ${data.cr_name}`);
    l.push("");
    l.push("== This Week at a Glance ==");
    l.push(`• Announcements posted (last 7 days): ${data.summary.announcements_7d}`);
    l.push(`• Open doubts: ${data.summary.open_doubts}`);
    l.push(`• Escalated (to seniors/alumni): ${data.summary.escalated}`);
    l.push(`• Attendance defaulters (<75%): ${data.summary.defaulters}`);
    l.push(`• Upcoming deadlines: ${data.summary.upcoming_deadlines}`);
    l.push("");
    if (data.announcements.length) {
      l.push("== Pinned Announcements ==");
      data.announcements.forEach((a, i) => {
        l.push(`${i + 1}. [${a.kind}] ${a.title} — by ${a.author}`);
        if (a.deadline) l.push(`   Deadline: ${new Date(a.deadline).toLocaleString()}`);
      });
      l.push("");
    }
    if (data.doubts.length) {
      l.push("== Open Doubts ==");
      data.doubts.forEach((q, i) => {
        l.push(`${i + 1}. [${q.stage}] #${q.topic || "General"} — ${q.query}`);
      });
      l.push("");
    }
    if (data.defaulters.length) {
      l.push("== Attendance Defaulters ==");
      data.defaulters.forEach((d) => {
        l.push(`• ${d.name} (${d.year}) — ${d.percent}% (${d.attended}/${d.total})`);
      });
    }
    return l.join("\n");
  };

  const copyDigest = async () => {
    try {
      await navigator.clipboard.writeText(buildTextDigest());
      toast.success("Digest copied to clipboard — ready to paste into WhatsApp / email");
    } catch {
      toast.error("Copy failed");
    }
  };

  if (error) {
    return (
      <div className="tactile-card !p-6 flex items-center gap-3 text-sm text-ink-2" data-testid="digest-forbidden">
        <WarningCircle size={18} className="text-brand" />
        {error}
      </div>
    );
  }

  if (!data) {
    return <div className="text-ink-3 italic text-sm animate-pulse" data-testid="digest-loading">Assembling your Monday digest…</div>;
  }

  const weekEnd = new Date(data.week_ending);

  return (
    <div className="space-y-8 animate-fade-up print:space-y-4" data-testid="digest-view">
      <div className="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-brand font-semibold">
            Monday Digest · Week ending {weekEnd.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </div>
          <h2 className="font-serif text-4xl md:text-5xl font-semibold text-ink tracking-tight leading-[1.02] mt-2">
            {data.department}
            <span className="italic text-brand-gold"> in seven days.</span>
          </h2>
          <p className="text-sm text-ink-2 mt-2 max-w-xl">
            Prepared for <b className="text-ink">{data.cr_name}</b>. Skim it, or hit copy and paste into your class WhatsApp.
          </p>
        </div>
        <div className="flex items-center gap-2 print:hidden">
          <button
            data-testid="digest-copy-btn"
            onClick={copyDigest}
            className="px-3.5 py-2 rounded-lg bg-paper-card border border-edge-light text-ink-2 hover:text-ink hover:border-brand text-xs font-semibold flex items-center gap-1.5"
          >
            <Copy size={13} weight="fill" /> Copy digest
          </button>
          <button
            data-testid="digest-print-btn"
            onClick={() => window.print()}
            className="px-3.5 py-2 rounded-lg bg-brand text-paper hover:bg-brand-hover text-xs font-semibold flex items-center gap-1.5 shadow-clay"
          >
            <Printer size={13} weight="fill" /> Print / PDF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatTile label="Announcements" value={data.summary.announcements_7d} tone="brand" />
        <StatTile label="Open doubts" value={data.summary.open_doubts} tone="deep" />
        <StatTile label="Escalated" value={data.summary.escalated} tone="gold" />
        <StatTile label="Defaulters" value={data.summary.defaulters} tone="brand" />
        <StatTile label="Deadlines" value={data.summary.upcoming_deadlines} tone="deep" />
      </div>

      <TactileCard data-testid="digest-announcements">
        <SectionHeading
          eyebrow="Pinned"
          title="Announcements this week"
          right={<Megaphone size={22} className="text-brand" weight="fill" />}
        />
        <div className="mt-5 space-y-4">
          {data.announcements.length === 0 && (
            <div className="text-ink-3 italic text-sm">Nothing pinned this week.</div>
          )}
          {data.announcements.map((a) => (
            <div key={a.id} className="border-b border-edge-light pb-4 last:border-none last:pb-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] uppercase tracking-widest text-brand font-semibold">{a.kind}</span>
                <span className="text-[10px] font-mono text-ink-3">{new Date(a.created_at).toLocaleString()}</span>
              </div>
              <div className="font-serif text-xl text-ink">{a.title}</div>
              <p className="text-sm text-ink-2 mt-1 whitespace-pre-wrap">{a.body}</p>
              <div className="text-xs text-ink-3 mt-1">by <b className="text-ink-2">{a.author}</b></div>
            </div>
          ))}
        </div>
      </TactileCard>

      <TactileCard data-testid="digest-doubts">
        <SectionHeading
          eyebrow="Unresolved"
          title="Open doubts that still need eyes"
          right={<Question size={22} className="text-brand-deep" weight="fill" />}
        />
        <div className="mt-5 space-y-3">
          {data.doubts.length === 0 && (
            <div className="text-ink-3 italic text-sm">Everything answered — nice week.</div>
          )}
          {data.doubts.map((q) => (
            <div key={q.id} className="flex items-start gap-3 py-2 border-b border-edge-light last:border-none">
              <EncryptedIDChip id={q.enc_id} />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-ink font-medium">{q.query}</div>
                <div className="text-[11px] text-ink-3 mt-0.5 font-mono">
                  #{q.topic} · {q.answers} answers · stage: <b className="text-brand-deep">{q.stage}</b>
                </div>
              </div>
            </div>
          ))}
        </div>
      </TactileCard>

      {data.escalated.length > 0 && (
        <TactileCard data-testid="digest-escalated" className="!bg-brand/5">
          <SectionHeading
            eyebrow="Escalated"
            title="These crossed the 48-hour line"
            right={<Sparkle size={22} className="text-brand" weight="fill" />}
          />
          <div className="mt-5 space-y-2">
            {data.escalated.map((q) => (
              <div key={q.id} className="flex items-center gap-3 text-sm py-1.5">
                <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full bg-brand text-paper font-semibold">
                  {q.stage}
                </span>
                <span className="flex-1 text-ink truncate">{q.query}</span>
                <span className="text-[10px] font-mono text-ink-3">#{q.topic}</span>
              </div>
            ))}
          </div>
        </TactileCard>
      )}

      {data.deadlines.length > 0 && (
        <TactileCard data-testid="digest-deadlines">
          <SectionHeading
            eyebrow="Upcoming"
            title="Deadlines on the horizon"
            right={<CalendarBlank size={22} className="text-brand-deep" weight="fill" />}
          />
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
            {data.deadlines.map((d, i) => {
              const dt = new Date(d.when);
              return (
                <div key={i} className="p-3 rounded-xl border border-edge-light bg-paper-sidebar">
                  <div className="font-serif text-2xl text-brand-deep">
                    {dt.toLocaleDateString(undefined, { day: "2-digit" })}
                  </div>
                  <div className="text-[11px] uppercase tracking-widest text-ink-3">
                    {dt.toLocaleDateString(undefined, { month: "short", weekday: "short" })}
                  </div>
                  <div className="text-xs text-ink mt-1 line-clamp-2 font-medium">{d.title}</div>
                </div>
              );
            })}
          </div>
        </TactileCard>
      )}

      <TactileCard data-testid="digest-defaulters">
        <SectionHeading
          eyebrow="Roster health"
          title="Attendance defaulters (below 75%)"
          right={<ChartLineDown size={22} className="text-brand" weight="fill" />}
        />
        <div className="mt-5">
          {data.defaulters.length === 0 && (
            <div className="text-ink-3 italic text-sm">Everyone is safely above 75%. Rare and beautiful.</div>
          )}
          {data.defaulters.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-[10px] uppercase tracking-widest text-ink-3 font-semibold">
                <tr>
                  <th className="text-left py-2">Name</th>
                  <th className="text-left py-2">Year</th>
                  <th className="text-right py-2">%</th>
                  <th className="text-right py-2">Classes</th>
                </tr>
              </thead>
              <tbody>
                {data.defaulters.map((d) => (
                  <tr key={d.email} className="border-t border-edge-light">
                    <td className="py-2 text-ink font-medium">{d.name}</td>
                    <td className="py-2 text-ink-2">{d.year || "—"}</td>
                    <td className="py-2 text-right font-mono text-brand font-semibold">{d.percent}%</td>
                    <td className="py-2 text-right text-ink-3 font-mono">{d.attended}/{d.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </TactileCard>
    </div>
  );
}
