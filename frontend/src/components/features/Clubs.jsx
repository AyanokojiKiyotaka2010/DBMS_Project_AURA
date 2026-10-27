import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, CAN_MANAGE_CLUBS } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { Books, ArrowUpRight, Plus, Trash } from "@phosphor-icons/react";
import { Field, Btn, inputCls, errMsg } from "./shared";

const EMPTY = { name: "", category: "", description: "", cover: "", cells: "" };

export function Clubs({ user }) {
  const canManage = CAN_MANAGE_CLUBS(user?.role);
  const [clubs, setClubs] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [cellDraft, setCellDraft] = useState({});
  const [archDraft, setArchDraft] = useState({});

  const load = () => axios.get(`${API}/clubs`).then((r) => setClubs(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const replace = (club) => setClubs((p) => p.map((c) => (c.id === club.id ? club : c)));

  const create = async (e) => {
    e.preventDefault();
    try {
      const cells = form.cells.split(",").map((c) => c.trim()).filter(Boolean);
      const r = await axios.post(`${API}/clubs`, { ...form, cells });
      setClubs((p) => [...p, r.data].sort((a, b) => a.name.localeCompare(b.name)));
      setForm(EMPTY);
      setShowForm(false);
      toast.success(`Club "${r.data.name}" created`);
    } catch (err) { toast.error(errMsg(err, "Could not create club")); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete "${c.name}" with its cells and archive?`)) return;
    try {
      await axios.delete(`${API}/clubs/${c.id}`);
      setClubs((p) => p.filter((x) => x.id !== c.id));
    } catch (err) { toast.error(errMsg(err)); }
  };

  const addCell = async (c) => {
    const name = (cellDraft[c.id] || "").trim();
    if (!name) return;
    try {
      replace((await axios.post(`${API}/clubs/${c.id}/cells`, { name })).data);
      setCellDraft((p) => ({ ...p, [c.id]: "" }));
    } catch (err) { toast.error(errMsg(err)); }
  };

  const addYear = async (c) => {
    const d = archDraft[c.id] || {};
    if (!d.year) return;
    try {
      replace((await axios.post(`${API}/clubs/${c.id}/archives`, { year: Number(d.year), events: Number(d.events || 0) })).data);
      setArchDraft((p) => ({ ...p, [c.id]: {} }));
    } catch (err) { toast.error(errMsg(err)); }
  };

  return (
    <div className="space-y-8 animate-fade-up" data-testid="clubs-view">
      <SectionHeading
        eyebrow="Community"
        title="Clubs, cells & five-year archives"
        description="Every club groups its media, writing, events and past festivals in one place."
        right={canManage && (
          <Btn data-testid="club-new-btn" onClick={() => setShowForm((v) => !v)}>
            <span className="flex items-center gap-1.5"><Plus size={14} weight="bold" />{showForm ? "Close" : "New club"}</span>
          </Btn>
        )}
      />

      {canManage && showForm && (
        <TactileCard>
          <form onSubmit={create} className="grid md:grid-cols-2 gap-4" data-testid="club-form">
            <Field label="Club name"><input required data-testid="club-name-input" className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Category"><input data-testid="club-category-input" className={inputCls} placeholder="Cultural, Technical…" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></Field>
            <Field label="Description" className="md:col-span-2"><textarea data-testid="club-desc-input" rows={2} className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            <Field label="Cover image URL (optional)"><input className={inputCls} value={form.cover} onChange={(e) => setForm({ ...form, cover: e.target.value })} /></Field>
            <Field label="Cells (comma separated)"><input data-testid="club-cells-input" className={inputCls} placeholder="Media, Design, Events" value={form.cells} onChange={(e) => setForm({ ...form, cells: e.target.value })} /></Field>
            <div className="md:col-span-2"><Btn type="submit" data-testid="club-create-submit">Create club</Btn></div>
          </form>
        </TactileCard>
      )}

      {clubs.length === 0 && (
        <TactileCard>
          <div className="text-sm text-ink-3 text-center py-6" data-testid="clubs-empty">
            {canManage ? "No clubs yet — create the first one with “New club”." : "No clubs have been added yet."}
          </div>
        </TactileCard>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {clubs.map((c) => (
          <TactileCard key={c.id} className="!p-0 overflow-hidden" data-testid={`club-card-${c.id}`}>
            <div className="relative h-40 bg-brand-deep">
              {c.cover && <img src={c.cover} alt={c.name} className="absolute inset-0 w-full h-full object-cover" />}
              <div className="absolute inset-0 bg-gradient-to-t from-brand-deep/80 via-brand-deep/20 to-transparent" />
              <div className="absolute bottom-3 left-4 right-4 text-paper">
                <div className="text-[10px] uppercase tracking-[0.22em] text-brand-gold font-semibold">{c.category}</div>
                <div className="font-serif text-2xl font-semibold">{c.name}</div>
              </div>
              {canManage && (
                <button data-testid={`club-delete-${c.id}`} onClick={() => remove(c)} title="Delete club"
                  className="absolute top-3 right-3 p-2 rounded-lg bg-paper/90 text-ink-2 hover:text-brand">
                  <Trash size={14} />
                </button>
              )}
            </div>
            <div className="p-5">
              <p className="text-sm text-ink-2 leading-relaxed">{c.description}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(c.cells || []).map((cell) => (
                  <span key={cell} className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-edge-light bg-paper-sidebar text-ink-2">#{cell}</span>
                ))}
              </div>
              {canManage && (
                <div className="mt-3 flex gap-2">
                  <input data-testid={`club-cell-input-${c.id}`} className={inputCls} placeholder="Add a cell" value={cellDraft[c.id] || ""}
                    onChange={(e) => setCellDraft((p) => ({ ...p, [c.id]: e.target.value }))} />
                  <Btn variant="ghost" type="button" onClick={() => addCell(c)}>Add</Btn>
                </div>
              )}
              <button
                data-testid={`club-toggle-archives-${c.id}`}
                onClick={() => setExpanded(expanded === c.id ? null : c.id)}
                className="mt-4 text-xs font-semibold text-brand-deep hover:text-brand flex items-center gap-1"
              >
                <Books size={14} />
                {expanded === c.id ? "Hide archives" : "Event archive"}
                <ArrowUpRight size={12} />
              </button>
              {expanded === c.id && (
                <div className="mt-4 space-y-3">
                  {(c.archives || []).length === 0 && <div className="text-xs text-ink-3">No archive years recorded yet.</div>}
                  <div className="grid grid-cols-5 gap-2">
                    {(c.archives || []).map((y) => (
                      <div key={y.year} className="p-3 rounded-lg bg-paper-sidebar border border-edge-light text-center">
                        <div className="font-serif text-lg font-semibold text-brand-deep">{y.year}</div>
                        <div className="text-[10px] text-ink-3">{y.events} events</div>
                      </div>
                    ))}
                  </div>
                  {canManage && (
                    <div className="flex gap-2">
                      <input data-testid={`club-year-input-${c.id}`} type="number" className={inputCls} placeholder="Year" value={archDraft[c.id]?.year || ""}
                        onChange={(e) => setArchDraft((p) => ({ ...p, [c.id]: { ...p[c.id], year: e.target.value } }))} />
                      <input type="number" min="0" className={inputCls} placeholder="Events" value={archDraft[c.id]?.events || ""}
                        onChange={(e) => setArchDraft((p) => ({ ...p, [c.id]: { ...p[c.id], events: e.target.value } }))} />
                      <Btn variant="ghost" type="button" onClick={() => addYear(c)}>Save</Btn>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TactileCard>
        ))}
      </div>
    </div>
  );
}
