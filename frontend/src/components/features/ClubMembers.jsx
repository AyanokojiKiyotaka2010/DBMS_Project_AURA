import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { FileArrowDown, Trash } from "@phosphor-icons/react";
import { Btn, inputCls, errMsg } from "./shared";

const ROLES = ["Member", "Core", "Co-Head", "Head"];
const GLOBAL = ["Administrator", "Convener", "Professor"];
const toBase64 = (file) => new Promise((res, rej) => {
  const r = new FileReader();
  r.onload = () => res(String(r.result).split(",")[1]);
  r.onerror = rej;
  r.readAsDataURL(file);
});
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

/** Join button (always) + members area (when `open` and you are a member or manager). */
export function ClubMembership({ club, user, open, onChanged }) {
  const status = club.my_status || "none";
  const canManage = !!club.can_manage;
  const isGlobal = GLOBAL.includes(user.role);
  const [docs, setDocs] = useState([]);
  const [members, setMembers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [doc, setDoc] = useState({ title: "", description: "", file: null });
  const [rolls, setRolls] = useState("");
  const base = `${API}/clubs/${club.id}`;
  const allowed = status === "member" || canManage;

  const load = useCallback(async () => {
    if (!open || !allowed) return;
    axios.get(`${base}/documents`).then((r) => setDocs(r.data)).catch(() => {});
    axios.get(`${base}/members`).then((r) => setMembers(r.data)).catch(() => {});
    if (canManage) axios.get(`${base}/requests`).then((r) => setRequests(r.data)).catch(() => {});
  }, [open, allowed, canManage, base]);
  useEffect(() => { load(); }, [load]);

  const act = async (fn, ok) => {
    try { await fn(); ok && toast.success(ok); await load(); onChanged && onChanged(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const join = () => act(() => axios.post(`${base}/join`, { message: "" }), "Request sent — a club manager will review it");
  const leave = () => window.confirm(status === "pending" ? "Withdraw your request?" : "Leave this club?") && act(() => axios.delete(`${base}/join`));

  const upload = async (e) => {
    e.preventDefault();
    if (!doc.file) return toast.error("Choose a file");
    if (doc.file.size > 4 * 1024 * 1024) return toast.error("Documents are limited to 4 MB");
    await act(async () => {
      await axios.post(`${base}/documents`, { title: doc.title, description: doc.description,
        file: { name: doc.file.name, mime: doc.file.type || "application/octet-stream", data: await toBase64(doc.file) } });
      setDoc({ title: "", description: "", file: null });
    }, "Document added");
  };
  const download = async (d) => {
    try {
      const r = await axios.get(`${base}/documents/${d.id}/file`, { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = url; a.download = d.file_name; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) { toast.error("Download failed"); }
  };
  const addRolls = () => act(async () => {
    const r = await axios.post(`${base}/members/add-by-roll`, { roll_nos: rolls.split(/[\s,;]+/).filter(Boolean), role: "Member" });
    toast.success(`${r.data.added.length} added` + (r.data.not_found.length ? ` · not found: ${r.data.not_found.join(", ")}` : ""));
    setRolls("");
  });

  return (
    <div data-testid={`club-membership-${club.id}`}>
      <div className="mt-3 flex items-center gap-2">
        {status === "none" && <Btn data-testid={`club-join-${club.id}`} onClick={join}>Request to join</Btn>}
        {status === "pending" && (<>
          <span className="text-xs font-semibold text-brand-deep bg-brand/10 rounded-full px-3 py-1.5" data-testid={`club-pending-${club.id}`}>Request pending</span>
          <button onClick={leave} className="text-xs text-ink-3 hover:text-brand underline">Withdraw</button>
        </>)}
        {status === "member" && (<>
          <span className="text-xs font-semibold text-brand-deep bg-brand-deep/10 rounded-full px-3 py-1.5" data-testid={`club-member-${club.id}`}>Member · {club.my_role}</span>
          <button onClick={leave} className="text-xs text-ink-3 hover:text-brand underline">Leave</button>
        </>)}
        <span className="text-[11px] text-ink-3">{club.member_count || 0} member{club.member_count === 1 ? "" : "s"}{canManage && club.pending_count ? ` · ${club.pending_count} request${club.pending_count > 1 ? "s" : ""} waiting` : ""}</span>
      </div>

      {open && !allowed && <div className="mt-3 text-xs text-ink-3 italic">Members can see the club’s archive documents and member list. Request to join to get access.</div>}

      {open && allowed && (
        <div className="mt-4 space-y-5" data-testid={`club-members-area-${club.id}`}>
          {canManage && requests.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] font-semibold text-ink-3 mb-1.5">Requests to join</div>
              {requests.map((r) => (
                <div key={r.user_id} className="flex items-center justify-between gap-2 text-sm py-1">
                  <span><b>{r.name}</b> <span className="text-xs text-ink-3">{[r.roll_no, r.department, r.year].filter(Boolean).join(" · ")}</span></span>
                  <span className="flex gap-2">
                    <Btn data-testid={`club-approve-${club.id}-${r.user_id}`} onClick={() => act(() => axios.post(`${base}/requests/${r.user_id}/approve`))}>Accept</Btn>
                    <Btn variant="ghost" onClick={() => act(() => axios.post(`${base}/requests/${r.user_id}/decline`))}>Decline</Btn>
                  </span>
                </div>
              ))}
            </div>
          )}

          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-semibold text-ink-3 mb-1.5">Archive documents (members only)</div>
            {docs.length === 0 && <div className="text-xs text-ink-3">No documents yet.</div>}
            <ul className="space-y-1.5">
              {docs.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-2 text-sm">
                  <button onClick={() => download(d)} className="text-left flex items-center gap-2 hover:text-brand">
                    <FileArrowDown size={16} className="text-brand-deep" />
                    <span><b>{d.title}</b><span className="text-xs text-ink-3"> · {d.file_name} · {kb(d.size)} · {d.uploaded_by}</span>
                      {d.description && <span className="block text-xs text-ink-2">{d.description}</span>}</span>
                  </button>
                  {canManage && <button onClick={() => window.confirm("Delete this document?") && act(() => axios.delete(`${base}/documents/${d.id}`))} className="text-ink-3 hover:text-brand"><Trash size={13} /></button>}
                </li>
              ))}
            </ul>
            {canManage && (
              <form onSubmit={upload} className="mt-2 grid grid-cols-2 gap-2">
                <input required className={inputCls} placeholder="Title" value={doc.title} onChange={(e) => setDoc({ ...doc, title: e.target.value })} />
                <input className={inputCls} placeholder="Short description (optional)" value={doc.description} onChange={(e) => setDoc({ ...doc, description: e.target.value })} />
                <input type="file" data-testid={`club-doc-file-${club.id}`} className={inputCls} onChange={(e) => setDoc({ ...doc, file: e.target.files?.[0] || null })} />
                <Btn type="submit" data-testid={`club-doc-upload-${club.id}`}>Upload (max 4 MB)</Btn>
              </form>
            )}
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-semibold text-ink-3 mb-1.5">Members</div>
            <ul className="space-y-1">
              {members.map((m) => (
                <li key={m.user_id} className="flex items-center justify-between gap-2 text-sm">
                  <span>{m.name} <span className="text-xs text-ink-3">{[m.roll_no, m.department, m.year].filter(Boolean).join(" · ")}</span></span>
                  <span className="flex items-center gap-2">
                    {isGlobal ? (
                      <select value={m.role} className="bg-transparent text-xs outline-none" onChange={(e) => act(() => axios.post(`${base}/members/${m.user_id}/role`, { role: e.target.value }))}>
                        {ROLES.map((r) => <option key={r}>{r}</option>)}
                      </select>
                    ) : <span className="text-xs font-semibold text-brand-deep">{m.role}</span>}
                    {canManage && <button onClick={() => window.confirm(`Remove ${m.name}?`) && act(() => axios.delete(`${base}/members/${m.user_id}`))} className="text-ink-3 hover:text-brand"><Trash size={12} /></button>}
                  </span>
                </li>
              ))}
            </ul>
            {canManage && (
              <div className="mt-2 flex gap-2">
                <input data-testid={`club-rolls-${club.id}`} className={inputCls} placeholder="Add students by roll no. (paste several, separated by spaces or commas)" value={rolls} onChange={(e) => setRolls(e.target.value)} />
                <Btn variant="ghost" type="button" onClick={addRolls} disabled={!rolls.trim()}>Add</Btn>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
