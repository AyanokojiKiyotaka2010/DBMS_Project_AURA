import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, IS_ADMIN } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { AttachmentPicker, AttachmentGallery } from "../Attachments";

export function Complaints({ user }) {
  const [items, setItems] = useState([]);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [attachments, setAttachments] = useState([]);
  const isAdmin = IS_ADMIN(user.role) || user.role === "Convener";

  const load = () => axios.get(`${API}/complaints`).then((r) => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const post = async (e) => {
    e.preventDefault();
    if (!subject || !body) return;
    try {
      await axios.post(`${API}/complaints`, { subject, body, attachments });
      setSubject(""); setBody(""); setAttachments([]);
      toast.success("Sent to conveners");
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const respond = async (id, resp) => {
    try {
      await axios.post(`${API}/complaints/${id}/respond`, { response: resp });
      toast.success("Response recorded");
      load();
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-8 animate-fade-up" data-testid="complaints-view">
      <SectionHeading
        eyebrow="Direct line"
        title="General complaints"
        description="Escalate issues to admins and conveners with an audited trail."
      />
      <TactileCard className="!p-5">
        <form onSubmit={post} className="space-y-3">
          <input
            data-testid="complaint-subject-input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Subject"
            className="w-full font-serif text-xl bg-transparent border-b border-edge-light py-2 outline-none focus:border-brand"
          />
          <textarea
            data-testid="complaint-body-input"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            placeholder="What's going on?"
            className="w-full bg-paper-sidebar border border-edge-light rounded-xl p-3 text-sm outline-none resize-none focus:border-brand"
          />
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <AttachmentPicker attachments={attachments} setAttachments={setAttachments} testidPrefix="complaint" />
            <button
              data-testid="complaint-submit-btn"
              className="px-4 py-2 rounded-lg bg-brand text-paper text-sm font-semibold hover:bg-brand-hover"
            >
              Send to admins
            </button>
          </div>
        </form>
      </TactileCard>

      <div className="space-y-4">
        {items.map((c) => (
          <TactileCard key={c.id} className="!p-5" data-testid={`complaint-${c.id}`}>
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-brand font-semibold">{c.status}</div>
                <div className="font-serif text-xl font-semibold text-ink mt-1">{c.subject}</div>
                <div className="text-xs text-ink-3 mt-1">By {c.author} · {new Date(c.created_at).toLocaleString()}</div>
                <p className="text-sm text-ink-2 mt-3 whitespace-pre-wrap">{c.body}</p>
                <AttachmentGallery attachments={c.attachments} testidPrefix={`complaint-att-${c.id}`} />
              </div>
            </div>
            {c.response && (
              <div className="mt-3 pt-3 border-t border-edge-light bg-brand-deep/5 -mx-5 -mb-5 p-4 rounded-b-2xl">
                <div className="text-[10px] uppercase tracking-widest text-brand-deep font-semibold">Admin response</div>
                <p className="text-sm text-ink mt-1">{c.response}</p>
              </div>
            )}
            {isAdmin && !c.response && <RespondForm onSubmit={(r) => respond(c.id, r)} />}
          </TactileCard>
        ))}
        {items.length === 0 && <div className="text-ink-3 italic text-sm">No complaints filed. Enjoy the peace.</div>}
      </div>
    </div>
  );
}

function RespondForm({ onSubmit }) {
  const [r, setR] = useState("");
  return (
    <div className="mt-3 pt-3 border-t border-edge-light flex gap-2 flex-wrap">
      <input
        value={r}
        onChange={(e) => setR(e.target.value)}
        placeholder="Write official response…"
        className="flex-1 min-w-[220px] bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
      />
      <button
        onClick={() => { if (r) { onSubmit(r); setR(""); } }}
        className="px-3 py-2 rounded-lg bg-brand-deep text-paper text-sm font-semibold hover:bg-ink"
      >
        Respond
      </button>
    </div>
  );
}
