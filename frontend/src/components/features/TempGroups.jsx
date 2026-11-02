import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { Timer, Paperclip, PaperPlaneTilt, DownloadSimple, UserCirclePlus } from "@phosphor-icons/react";
import { Btn, inputCls, errMsg } from "./shared";
import { motion } from "framer-motion";
import { TimeRing } from "../motion";

const MAX_FILE = 2 * 1024 * 1024;

const fmtLeft = (iso) => {
  const ms = new Date(iso) - new Date();
  if (ms <= 0) return "expired";
  const h = Math.floor(ms / 3600000), m = Math.floor((ms % 3600000) / 60000);
  return h >= 48 ? `${Math.floor(h / 24)}d ${h % 24}h left` : `${h}h ${m}m left`;
};
const minutesLeft = (iso) => (new Date(iso) - new Date()) / 60000;

const saveBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
};
const toBase64 = (file) => new Promise((res, rej) => {
  const r = new FileReader();
  r.onload = () => res(String(r.result).split(",")[1]);
  r.onerror = rej;
  r.readAsDataURL(file);
});

export function TempGroups({ user }) {
  const [groups, setGroups] = useState([]);
  const [waiting, setWaiting] = useState([]);
  const [sel, setSel] = useState(null);
  const [name, setName] = useState("");
  const [hours, setHours] = useState(24);
  const [keyword, setKeyword] = useState("");

  const load = useCallback(() =>
    axios.get(`${API}/temp-groups`).then((r) => {
      setGroups(r.data.groups); setWaiting(r.data.my_requests);
      setSel((cur) => (cur && r.data.groups.some((g) => g.id === cur) ? cur : cur === null ? null : null));
    }).catch(() => {}), []);
  useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, [load]);

  const create = async (e) => {
    e.preventDefault();
    try {
      const r = await axios.post(`${API}/temp-groups`, { name, hours: Number(hours) });
      toast.success(`"${r.data.name}" created — share the name only with people you want to let in`);
      setName(""); await load(); setSel(r.data.id);
    } catch (err) { toast.error(errMsg(err, "Could not create the group")); }
  };
  const ask = async (e) => {
    e.preventDefault();
    try { const r = await axios.post(`${API}/temp-groups/request`, { name: keyword }); toast.success(r.data.message); setKeyword(""); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };

  const current = groups.find((g) => g.id === sel);

  return (
    <div className="space-y-6 animate-fade-up" data-testid="temp-groups-view">
      <SectionHeading
        eyebrow="Short-lived & private"
        title="Temporary groups"
        description="Private chat rooms for hackathons, study sprints and fest teams. Groups are invisible to outsiders — you join by typing the exact group name and the creator approves. Everything, including shared files, is deleted when the timer ends."
      />
      <div className="grid lg:grid-cols-[320px_1fr] gap-6">
        <div className="space-y-4">
          <TactileCard className="!p-4">
            <div className="text-[11px] uppercase tracking-widest font-semibold text-ink-2 mb-2">Create a group</div>
            <form onSubmit={create} className="space-y-2">
              <input data-testid="temp-name-input" required minLength={3} maxLength={60} value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Group name = the keyword" className={inputCls} />
              <div className="flex gap-2">
                <select data-testid="temp-hours-select" value={hours} onChange={(e) => setHours(e.target.value)} className={inputCls}>
                  {[6, 12, 24, 48, 72, 168].map((h) => <option key={h} value={h}>{h < 168 ? `${h} hours` : "1 week"}</option>)}
                </select>
                <Btn data-testid="temp-create-btn" type="submit"><UserCirclePlus size={14} weight="fill" /></Btn>
              </div>
            </form>
          </TactileCard>

          <TactileCard className="!p-4">
            <div className="text-[11px] uppercase tracking-widest font-semibold text-ink-2 mb-2">Join with a group name</div>
            <form onSubmit={ask} className="flex gap-2">
              <input data-testid="temp-keyword-input" required value={keyword} onChange={(e) => setKeyword(e.target.value)}
                placeholder="Type the exact name" className={inputCls} />
              <Btn data-testid="temp-request-btn" type="submit" variant="ghost">Ask</Btn>
            </form>
            {waiting.length > 0 && <div className="text-[11px] text-ink-3 mt-2">Waiting for approval: {waiting.join(", ")}</div>}
          </TactileCard>

          <div className="space-y-2" data-testid="temp-group-list">
            {groups.map((g) => (
              <button key={g.id} data-testid={`temp-group-${g.id}`} onClick={() => setSel(g.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${sel === g.id ? "bg-paper-card border-brand shadow-clay" : "bg-paper-card/60 border-edge-light hover:border-brand/50"}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <TimeRing createdAt={g.created_at} expiresAt={g.expires_at} size={26} />
                    <div className="font-serif text-lg font-semibold text-ink truncate">{g.name}</div>
                  </div>
                  {g.pending_requests > 0 && <span className="text-[10px] font-semibold bg-brand text-paper rounded-full px-2 py-0.5">{g.pending_requests} request{g.pending_requests > 1 ? "s" : ""}</span>}
                </div>
                <div className={`text-[11px] mt-0.5 flex items-center gap-1 ${minutesLeft(g.expires_at) < 60 ? "text-brand font-semibold" : "text-ink-3"}`}>
                  <Timer size={11} weight="fill" /> {fmtLeft(g.expires_at)} · {g.member_count} member{g.member_count > 1 ? "s" : ""}
                </div>
              </button>
            ))}
            {groups.length === 0 && <div className="text-ink-3 italic text-sm">You are not in any group yet. Create one, or ask to join with its name.</div>}
          </div>
        </div>

        {current ? <Chat key={current.id} group={current} user={user} reload={load} onGone={() => { setSel(null); load(); }} />
          : <TactileCard className="!p-10 text-center text-ink-3 text-sm">Pick a group to open its chat.</TactileCard>}
      </div>
    </div>
  );
}

function Chat({ group, user, reload, onGone }) {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [members, setMembers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [showMembers, setShowMembers] = useState(false);
  const [thumbs, setThumbs] = useState({});
  const [, tick] = useState(0);
  const lastId = useRef(0);
  const goneRef = useRef(onGone);
  goneRef.current = onGone;                 // keep the polling effect stable across parent re-renders
  const bottom = useRef(null);
  const fileInput = useRef(null);

  const poll = useCallback(async (initial = false) => {
    try {
      const r = await axios.get(`${API}/temp-groups/${group.id}/messages`, { params: { after: initial ? 0 : lastId.current } });
      if (r.data.length) {
        lastId.current = r.data[r.data.length - 1].id;
        setMsgs((prev) => (initial ? r.data : [...prev, ...r.data.filter((m) => !prev.some((p) => p.id === m.id))]));
      }
    } catch (e) { if (e.response?.status === 404) goneRef.current(); }
  }, [group.id]);

  useEffect(() => { poll(true); const t = setInterval(() => poll(false), 4000); return () => clearInterval(t); }, [poll]);
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 30000); return () => clearInterval(t); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs.length]);
  useEffect(() => {
    axios.get(`${API}/temp-groups/${group.id}/members`).then((r) => setMembers(r.data.members)).catch(() => {});
  }, [group.id, group.member_count]);
  const loadRequests = useCallback(() => {
    if (group.is_creator) axios.get(`${API}/temp-groups/${group.id}/requests`).then((r) => setRequests(r.data)).catch(() => {});
  }, [group.id, group.is_creator]);
  useEffect(() => { loadRequests(); }, [loadRequests, group.pending_requests]);

  useEffect(() => {          // lazily load image thumbnails (they need the auth header, so no plain <img src>)
    msgs.forEach((m) => {
      if (m.file && m.file.mime?.startsWith("image/") && !thumbs[m.id]) {
        setThumbs((t) => ({ ...t, [m.id]: "loading" }));
        axios.get(`${API}/temp-groups/${group.id}/messages/${m.id}/file`, { responseType: "blob" })
          .then((r) => setThumbs((t) => ({ ...t, [m.id]: URL.createObjectURL(r.data) }))).catch(() => {});
      }
    });
  }, [msgs]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (minutesLeft(group.expires_at) < 60) toast.warning(`"${group.name}" and its chat are deleted ${fmtLeft(group.expires_at).replace(" left", "")} from now — download a copy if you want to keep it.`, { duration: 8000 });
  }, [group.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() && !file) return;
    try {
      const body = { body: text };
      if (file) body.file = { name: file.name, mime: file.type || "application/octet-stream", data: await toBase64(file) };
      const r = await axios.post(`${API}/temp-groups/${group.id}/messages`, body);
      setText(""); setFile(null); if (fileInput.current) fileInput.current.value = "";
      lastId.current = r.data.id; setMsgs((p) => [...p, r.data]);
    } catch (err) { toast.error(errMsg(err, "Could not send")); }
  };
  const pick = (e) => {
    const f = e.target.files?.[0];
    if (f && f.size > MAX_FILE) { toast.error("Files are limited to 2 MB"); e.target.value = ""; return; }
    setFile(f || null);
  };
  const download = async (m) => {
    try { const r = await axios.get(`${API}/temp-groups/${group.id}/messages/${m.id}/file`, { responseType: "blob" }); saveBlob(r.data, m.file.name); }
    catch (err) { toast.error("Download failed"); }
  };
  const exportAll = async () => {
    try { const r = await axios.get(`${API}/temp-groups/${group.id}/export`, { responseType: "blob" }); saveBlob(r.data, `${group.name}-chat.zip`); toast.success("Saved — chat and files are in the ZIP"); }
    catch (err) { toast.error("Export failed"); }
  };
  const decide = async (uid, what) => {
    try { await axios.post(`${API}/temp-groups/${group.id}/requests/${uid}/${what}`); loadRequests(); reload(); }
    catch (err) { toast.error(errMsg(err)); }
  };
  const extend = async (h) => {
    try { await axios.post(`${API}/temp-groups/${group.id}/extend`, { hours: h }); toast.success(`Extended by ${h}h`); reload(); }
    catch (err) { toast.error(errMsg(err)); }
  };
  const leave = async () => {
    if (!window.confirm("Leave this group? You will lose access to its chat.")) return;
    try { await axios.delete(`${API}/temp-groups/${group.id}/members/${user.user_id}`); onGone(); } catch (err) { toast.error(errMsg(err)); }
  };
  const remove = async (uid) => { try { await axios.delete(`${API}/temp-groups/${group.id}/members/${uid}`); reload(); } catch (err) { toast.error(errMsg(err)); } };
  const destroy = async () => {
    if (!window.confirm("Delete this group and everything in it now? This cannot be undone.")) return;
    try { await axios.delete(`${API}/temp-groups/${group.id}`); onGone(); } catch (err) { toast.error(errMsg(err)); }
  };

  const soon = minutesLeft(group.expires_at) < 60;
  return (
    <TactileCard className="!p-0 overflow-hidden flex flex-col h-[640px]" data-testid="temp-chat">
      <div className="px-5 py-3 border-b border-edge-light flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <TimeRing createdAt={group.created_at} expiresAt={group.expires_at} />
          <div>
          <div className="font-serif text-xl font-semibold text-ink">{group.name}</div>
          <div className={`text-[11px] flex items-center gap-1 ${soon ? "text-brand font-semibold" : "text-ink-3"}`}>
            <Timer size={11} weight="fill" /> {fmtLeft(group.expires_at)} · deleted automatically
          </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Btn variant="ghost" data-testid="temp-members-toggle" onClick={() => setShowMembers((v) => !v)}>Members ({members.length})</Btn>
          <Btn variant="ghost" data-testid="temp-export-btn" onClick={exportAll}><span className="flex items-center gap-1"><DownloadSimple size={14} /> Save chat</span></Btn>
          {group.is_creator ? (<>
            <Btn variant="ghost" onClick={() => extend(24)}>+24h</Btn>
            <Btn variant="ghost" onClick={destroy}>Delete</Btn>
          </>) : <Btn variant="ghost" onClick={leave}>Leave</Btn>}
        </div>
      </div>

      {soon && (
        <div className="px-5 py-2 text-xs bg-brand/10 text-brand-deep flex items-center justify-between gap-3" data-testid="temp-expiry-banner">
          <span>This group, its messages and files will be permanently deleted {fmtLeft(group.expires_at).replace(" left", "")} from now.</span>
          <button onClick={exportAll} className="font-semibold underline">Download a copy</button>
        </div>
      )}

      {group.is_creator && requests.length > 0 && (
        <div className="px-5 py-3 bg-paper-sidebar border-b border-edge-light space-y-2" data-testid="temp-requests">
          <div className="text-[11px] uppercase tracking-widest font-semibold text-ink-2">Waiting to join</div>
          {requests.map((r) => (
            <div key={r.user_id} className="flex items-center justify-between gap-2 text-sm">
              <span><b>{r.name}</b> <span className="text-ink-3 text-xs">{[r.roll_no, r.department].filter(Boolean).join(" · ")}</span></span>
              <span className="flex gap-2">
                <Btn data-testid={`temp-approve-${r.user_id}`} onClick={() => decide(r.user_id, "approve")}>Accept</Btn>
                <Btn variant="ghost" onClick={() => decide(r.user_id, "decline")}>Decline</Btn>
              </span>
            </div>
          ))}
        </div>
      )}

      {showMembers && (
        <div className="px-5 py-3 border-b border-edge-light max-h-40 overflow-y-auto text-sm space-y-1">
          {members.map((m) => (
            <div key={m.user_id} className="flex items-center justify-between">
              <span>{m.name} {m.is_creator && <span className="text-[10px] text-brand font-semibold">CREATOR</span>} <span className="text-xs text-ink-3">{[m.roll_no, m.department].filter(Boolean).join(" · ")}</span></span>
              {group.is_creator && !m.is_creator && <button onClick={() => remove(m.user_id)} className="text-xs text-ink-3 hover:text-brand">Remove</button>}
            </div>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3" data-testid="temp-messages">
        {msgs.length === 0 && <div className="text-center text-ink-3 text-sm italic mt-10">No messages yet — say hello.</div>}
        {msgs.map((m) => {
          const mine = m.user_id === user.user_id;
          return (
            <motion.div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}
              initial={{ opacity: 0, y: 8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.25 }}>
              <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ${mine ? "bg-brand text-paper" : "bg-paper-sidebar text-ink"}`}>
                <div className={`text-[10px] font-semibold mb-0.5 ${mine ? "text-paper/80" : "text-brand-deep"}`}>
                  {mine ? "You" : m.user_name} · {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
                {m.body && <div className="whitespace-pre-wrap break-words">{m.body}</div>}
                {m.file && m.file.mime?.startsWith("image/") && thumbs[m.id] && thumbs[m.id] !== "loading" && (
                  <img src={thumbs[m.id]} alt={m.file.name} onClick={() => download(m)} className="mt-1.5 max-h-56 rounded-lg cursor-pointer" />
                )}
                {m.file && (
                  <button onClick={() => download(m)} className={`mt-1.5 flex items-center gap-1 text-xs underline ${mine ? "text-paper" : "text-brand-deep"}`}>
                    <Paperclip size={12} /> {m.file.name} ({Math.max(1, Math.round(m.file.size / 1024))} KB)
                  </button>
                )}
              </div>
            </motion.div>
          );
        })}
        <div ref={bottom} />
      </div>

      <form onSubmit={send} className="px-4 py-3 border-t border-edge-light flex items-center gap-2">
        <input ref={fileInput} type="file" className="hidden" onChange={pick} data-testid="temp-file-input" />
        <button type="button" onClick={() => fileInput.current?.click()} title="Attach a file (max 2 MB)" className="p-2.5 rounded-xl border border-edge-light text-ink-2 hover:text-brand"><Paperclip size={16} /></button>
        <input data-testid="temp-message-input" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000}
          placeholder={file ? `Attached: ${file.name} — add a note…` : "Write a message…"} className={inputCls} />
        <Btn data-testid="temp-send-btn" type="submit"><PaperPlaneTilt size={16} weight="fill" /></Btn>
      </form>
    </TactileCard>
  );
}
