import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, CAN_POST_ANNOUNCEMENT } from "../../lib/campus";
import { useCampusSocket } from "../../lib/socket";
import { TactileCard, SectionHeading, RoleBadge } from "../CampusUI";
import { Lock, PaperPlaneTilt, Broadcast } from "@phosphor-icons/react";

export function Announcements({ user }) {
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [kind, setKind] = useState("general");
  const [deadline, setDeadline] = useState("");
  const [liveOnline, setLiveOnline] = useState(false);
  const canPost = CAN_POST_ANNOUNCEMENT(user.role);

  const load = () =>
    axios
      .get(`${API}/announcements`, { params: { department: user.department, year: user.year } })
      .then((r) => setItems(r.data))
      .catch(() => {});

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [user.department, user.year]);

  useCampusSocket((event) => {
    if (event.type === "welcome") setLiveOnline(true);
    if (event.type === "announcement.created") {
      const a = event.payload;
      if (a.department && a.department !== user.department) return;
      setItems((prev) => {
        if (prev.some((x) => x.id === a.id)) return prev;
        return [a, ...prev];
      });
      if (a.author_id !== user.user_id) {
        toast.success(`New announcement: ${a.title}`, { duration: 4000 });
      }
    }
  });

  const post = async (e) => {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return toast.error("Add a title and body");
    try {
      await axios.post(`${API}/announcements`, {
        title, body, kind,
        deadline: deadline || null,
        department: user.department,
        year: user.year,
      });
      toast.success("Announcement pinned");
      setTitle(""); setBody(""); setDeadline(""); setKind("general");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Only CR / DCR can post");
    }
  };

  return (
    <div data-testid="announcements-view" className="space-y-8 animate-fade-up">
      <SectionHeading
        eyebrow={`${user.department}${user.year ? " · " + user.year : ""}`}
        title="Department announcements"
        description="A CR/DCR-locked feed for class reschedules, deadlines and pinned campus notices."
        right={
          <div
            data-testid="live-indicator-announcements"
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-semibold uppercase tracking-widest ${
              liveOnline
                ? "text-brand-deep border-brand-deep/30 bg-brand-deep/5"
                : "text-ink-3 border-edge-light bg-paper-sidebar"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${liveOnline ? "bg-brand-deep animate-pulse" : "bg-ink-3"}`} />
            <Broadcast size={12} weight="fill" />
            {liveOnline ? "Live" : "Offline"}
          </div>
        }
      />

      {canPost ? (
        <TactileCard className="!p-6">
          <form onSubmit={post} className="space-y-3" data-testid="announcement-composer">
            <div className="flex items-center gap-2">
              <RoleBadge role={user.role} />
              <span className="text-xs text-ink-3">Posting as {user.name}</span>
            </div>
            <input
              data-testid="ann-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Announcement title (e.g. Reschedule: DBMS Wed→Fri 4pm)"
              className="w-full font-serif text-2xl bg-transparent border-b border-edge-light py-2 outline-none focus:border-brand"
            />
            <textarea
              data-testid="ann-body-input"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={3}
              placeholder="Details, room number, links…"
              className="w-full bg-paper-sidebar border border-edge-light rounded-xl p-3 text-sm outline-none focus:border-brand resize-none"
            />
            <div className="flex flex-wrap items-center gap-3">
              <select
                data-testid="ann-kind-select"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                className="bg-paper-card border border-edge-light rounded-lg px-3 py-2 text-xs"
              >
                <option value="general">General</option>
                <option value="reschedule">Class reschedule</option>
                <option value="deadline">Deadline</option>
                <option value="exam">Exam / test</option>
              </select>
              <input
                data-testid="ann-deadline-input"
                type="datetime-local"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="bg-paper-card border border-edge-light rounded-lg px-3 py-2 text-xs text-ink-2"
              />
              <button
                data-testid="ann-submit-btn"
                type="submit"
                className="ml-auto px-4 py-2 rounded-lg bg-brand text-paper text-sm font-semibold hover:bg-brand-hover flex items-center gap-2 active:scale-[0.98]"
              >
                <PaperPlaneTilt size={14} weight="fill" /> Publish
              </button>
            </div>
          </form>
        </TactileCard>
      ) : (
        <div className="tactile-card !p-4 flex items-center gap-3 text-sm text-ink-2">
          <Lock size={16} className="text-ink-3" />
          Only <b>CR</b> or <b>DCR</b> in this department can pin announcements. Ask your rep to publish.
        </div>
      )}

      <TactileCard>
        <SectionHeading eyebrow="This week" title="Deadline calendar" />
        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
          {items.filter((i) => i.deadline).slice(0, 4).map((a) => {
            const d = new Date(a.deadline);
            return (
              <div key={a.id} className="p-3 rounded-xl border border-edge-light bg-paper-sidebar">
                <div className="font-serif text-2xl text-brand-deep">
                  {d.toLocaleDateString(undefined, { day: "2-digit" })}
                </div>
                <div className="text-[11px] uppercase tracking-widest text-ink-3">
                  {d.toLocaleDateString(undefined, { month: "short", weekday: "short" })}
                </div>
                <div className="text-xs text-ink mt-1 line-clamp-2 font-medium">{a.title}</div>
              </div>
            );
          })}
          {items.filter((i) => i.deadline).length === 0 && (
            <div className="col-span-full text-ink-3 text-sm italic">No upcoming deadlines. Enjoy the calm.</div>
          )}
        </div>
      </TactileCard>

      <div className="space-y-4">
        {items.map((a) => (
          <TactileCard key={a.id} className="!p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] uppercase tracking-widest text-brand font-semibold">{a.kind}</span>
                  <span className="text-[10px] text-ink-3 font-mono">{new Date(a.created_at).toLocaleString()}</span>
                </div>
                <h3 className="font-serif text-2xl font-semibold tracking-tight text-ink">{a.title}</h3>
                <p className="text-sm text-ink-2 mt-2 leading-relaxed whitespace-pre-wrap">{a.body}</p>
              </div>
              <RoleBadge role={a.author_role} />
            </div>
            <div className="mt-4 pt-3 border-t border-edge-light flex items-center justify-between text-xs text-ink-3">
              <span>Posted by <b className="text-ink-2">{a.author}</b></span>
              {a.deadline && <span className="font-mono">Due {new Date(a.deadline).toLocaleString()}</span>}
            </div>
          </TactileCard>
        ))}
        {items.length === 0 && (
          <div className="text-ink-3 text-sm italic">No announcements yet for your department & year.</div>
        )}
      </div>
    </div>
  );
}
