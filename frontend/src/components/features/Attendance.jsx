import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading, AttendanceRing } from "../CampusUI";
import { Plus } from "@phosphor-icons/react";

export function Attendance() {
  const [subs, setSubs] = useState([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");

  const load = () => axios.get(`${API}/attendance`).then((r) => setSubs(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!code || !name) return toast.error("Code and name required");
    try {
      await axios.post(`${API}/attendance`, { code, name });
      setCode(""); setName("");
      toast.success(`Added ${name}`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add");
    }
  };

  const mark = async (sub, kind) => {
    try {
      await axios.post(`${API}/attendance/${sub.id}/mark`, { present: kind === "present" });
      load();
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-8 animate-fade-up" data-testid="attendance-view">
      <SectionHeading
        eyebrow="Semester"
        title="Attendance tracker"
        description="Tap after each class. Your ring stays green above 75%."
      />

      <TactileCard className="!p-5">
        <form onSubmit={add} className="flex flex-wrap gap-3 items-center" data-testid="attendance-add-form">
          <input
            data-testid="attend-code-input"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="Code (CS301)"
            className="w-32 bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm font-mono"
          />
          <input
            data-testid="attend-name-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Subject name"
            className="flex-1 min-w-[180px] bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
          />
          <button
            data-testid="attend-add-btn"
            type="submit"
            className="px-4 py-2 rounded-lg bg-brand-deep text-paper text-sm font-semibold hover:bg-ink flex items-center gap-2 active:scale-[0.98]"
          >
            <Plus size={14} /> Add subject
          </button>
        </form>
      </TactileCard>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {subs.map((s) => {
          const pct = s.total ? Math.round((s.attended / s.total) * 100) : 0;
          return (
            <TactileCard key={s.id} className="!p-5" data-testid={`attend-card-${s.code}`}>
              <div className="flex items-center gap-4">
                <AttendanceRing percent={pct} />
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] font-mono text-brand font-semibold">{s.code}</div>
                  <div className="font-serif text-lg text-ink leading-tight truncate">{s.name}</div>
                  <div className="text-xs text-ink-3 mt-1">
                    {s.attended} / {s.total} classes
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button
                  data-testid={`attend-present-${s.code}`}
                  onClick={() => mark(s, "present")}
                  className="py-2 rounded-lg bg-brand-deep/10 hover:bg-brand-deep/20 text-brand-deep text-xs font-semibold"
                >
                  + Present
                </button>
                <button
                  data-testid={`attend-absent-${s.code}`}
                  onClick={() => mark(s, "absent")}
                  className="py-2 rounded-lg bg-brand/10 hover:bg-brand/20 text-brand text-xs font-semibold"
                >
                  + Absent
                </button>
              </div>
            </TactileCard>
          );
        })}
        {subs.length === 0 && (
          <div className="col-span-full text-ink-3 italic text-sm">
            No subjects yet — add your first above.
          </div>
        )}
      </div>
    </div>
  );
}
