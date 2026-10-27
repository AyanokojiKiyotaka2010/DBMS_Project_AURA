import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, useStructure } from "../../lib/campus";
import {
  TactileCard,
  SectionHeading,
  EncryptedIDChip,
  EscalationTimeline,
  RoleBadge,
} from "../CampusUI";
import { AttachmentPicker, AttachmentGallery } from "../Attachments";
import { Lock, Sparkle, CheckCircle } from "@phosphor-icons/react";

export function Queries({ user }) {
  const structure = useStructure();
  const [items, setItems] = useState([]);
  const [department, setDepartment] = useState(user.department);
  const [topic, setTopic] = useState("");
  const [query, setQuery] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [showArchived, setShowArchived] = useState(false);

  const load = () =>
    axios
      .get(`${API}/queries`, { params: { archived: showArchived } })
      .then((r) => setItems(r.data))
      .catch(() => {});
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [showArchived]);

  const post = async (e) => {
    e.preventDefault();
    if (!query.trim()) return toast.error("Please describe your doubt");
    try {
      await axios.post(`${API}/queries`, { department, topic: topic || "General", query, attachments });
      setQuery(""); setTopic(""); setAttachments([]);
      toast.success("Anonymous query posted with encrypted ID");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to post");
    }
  };

  const answer = async (qid, text) => {
    if (!text.trim()) return;
    try {
      await axios.post(`${API}/queries/${qid}/answer`, { text });
      toast.success("Answer added");
      load();
    } catch { toast.error("Failed"); }
  };

  const resolve = async (qid) => {
    try {
      await axios.post(`${API}/queries/${qid}/resolve`);
      toast.success("Marked resolved — archives in 7 days");
      load();
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-8 animate-fade-up" data-testid="queries-view">
      <SectionHeading
        eyebrow="Anonymous"
        title="Ask anything, safely."
        description="Your identity is masked with a rotating encrypted ID. If nobody answers in 48h it escalates to seniors, then to alumni after 7 days."
        right={
          <div className="flex items-center gap-2 bg-paper-card border border-edge-light rounded-full p-1">
            <button
              data-testid="queries-tab-active"
              onClick={() => setShowArchived(false)}
              className={`px-3 py-1 text-xs font-semibold rounded-full ${!showArchived ? "bg-brand text-paper" : "text-ink-2"}`}
            >Active</button>
            <button
              data-testid="queries-tab-archived"
              onClick={() => setShowArchived(true)}
              className={`px-3 py-1 text-xs font-semibold rounded-full ${showArchived ? "bg-brand text-paper" : "text-ink-2"}`}
            >Archived</button>
          </div>
        }
      />

      <TactileCard className="!p-6" data-testid="query-composer">
        <form onSubmit={post} className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <select
              data-testid="query-dept-select"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
            >
              {structure.departments.map((d) => <option key={d.id}>{d.name}</option>)}
            </select>
            <input
              data-testid="query-topic-input"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Topic (e.g. B+ trees)"
              className="flex-1 min-w-[180px] bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <textarea
            data-testid="query-text-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            placeholder="Ask freely, no name attached…"
            className="w-full bg-paper-sidebar border border-edge-light rounded-xl p-3 text-sm outline-none resize-none focus:border-brand"
          />
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 text-xs text-ink-3 flex-wrap">
              <div className="flex items-center gap-2">
                <Lock size={13} /> Posted as <span className="font-mono text-ink-2">enc_usr_•••</span>
              </div>
              <AttachmentPicker attachments={attachments} setAttachments={setAttachments} testidPrefix="query" />
            </div>
            <button
              data-testid="query-submit-btn"
              type="submit"
              className="px-4 py-2 rounded-lg bg-brand text-paper text-sm font-semibold hover:bg-brand-hover flex items-center gap-2 active:scale-[0.98]"
            >
              <Sparkle size={14} weight="fill" /> Submit anonymously
            </button>
          </div>
        </form>
      </TactileCard>

      <div className="space-y-5">
        {items.map((q) => (
          <QueryCard key={q.id} q={q} onAnswer={answer} onResolve={resolve} user={user} />
        ))}
        {items.length === 0 && (
          <div className="text-ink-3 italic text-sm">
            {showArchived ? "No archived queries yet." : "No open queries — silence is golden."}
          </div>
        )}
      </div>
    </div>
  );
}

function QueryCard({ q, onAnswer, onResolve, user }) {
  const [text, setText] = useState("");
  return (
    <TactileCard className="!p-6" data-testid={`query-card-${q.id}`}>
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <EncryptedIDChip id={q.author_encrypted_id} />
          <span className="text-[10px] uppercase tracking-widest text-brand-deep font-semibold px-2 py-0.5 rounded-full bg-brand-deep/10">{q.department}</span>
          {q.topic && <span className="text-[10px] font-mono text-ink-3">#{q.topic}</span>}
        </div>
        <EscalationTimeline stage={q.stage} />
      </div>

      <p className="font-serif text-xl md:text-2xl text-ink mt-4 leading-snug">{q.query}</p>

      <AttachmentGallery attachments={q.attachments} testidPrefix={`query-att-${q.id}`} />

      <div className="mt-5 space-y-3">
        {(q.answers || []).map((a, idx) => (
          <div key={idx} className="pl-4 border-l-2 border-brand/40">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-ink">{a.author}</span>
              <RoleBadge role={a.role} />
              <span className="text-[10px] font-mono text-ink-3">{new Date(a.time).toLocaleString()}</span>
            </div>
            <p className="text-sm text-ink-2 leading-relaxed whitespace-pre-wrap">{a.text}</p>
          </div>
        ))}
      </div>

      {q.status !== "Resolved" && q.status !== "Archived" && (
        <div className="mt-5 pt-4 border-t border-edge-light flex gap-2 flex-wrap">
          <input
            data-testid={`answer-input-${q.id}`}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Write a helpful answer…"
            className="flex-1 min-w-[220px] bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
          />
          <button
            data-testid={`answer-submit-${q.id}`}
            onClick={() => { onAnswer(q.id, text); setText(""); }}
            className="px-3 py-2 rounded-lg bg-brand-deep text-paper text-sm font-semibold hover:bg-ink"
          >
            Answer
          </button>
          {q.real_author_id === user.user_id && (
            <button
              data-testid={`resolve-btn-${q.id}`}
              onClick={() => onResolve(q.id)}
              className="px-3 py-2 rounded-lg bg-brand-gold/20 text-brand-deep text-sm font-semibold hover:bg-brand-gold/30 flex items-center gap-1"
            >
              <CheckCircle size={14} weight="fill" /> Mark resolved
            </button>
          )}
        </div>
      )}
    </TactileCard>
  );
}
